import json
import time

import ollama

from src import config
from src.schemas import CampoExtraido, Veredito, TipoRejeicao
from src.extracao.utils import parse_json_safe


# camada 2 do verificador: llm critic
# uso llama 3.1 8b pq eh familia diferente do extrator (qwen) - reduz vies circular
#
# importante: avalia TODOS os 8 campos de uma vez em uma unica chamada ao llama.
# fazer 8 chamadas separadas gastava 50s+ por video. batchando fica ~8-12s.
# se algum campo falha, a gente sabe qual eh pelo nome no json de resposta.


TIPOS_VALIDOS = {
    "evidencia_nao_alinha",
    "conflito_cross_field",
    "alucinacao_suspeita",
    "confianca_baixa",
    "nome_proprio_confundido",
    "contexto_irrelevante",
}


def _resumo_outros(nome_campo: str, campos: dict[str, CampoExtraido]) -> str:
    # gera um resumo curto dos outros campos pra dar contexto cruzado
    linhas = []
    for nome, c in campos.items():
        if nome == nome_campo or c.valor is None or c.valor == [] or c.valor == "":
            continue
        v = c.valor
        if isinstance(v, list):
            v = [(x.get("nome") if isinstance(x, dict) else str(x)) for x in v]
        linhas.append(f"  - {nome}: {v}")
    return "\n".join(linhas) or "  (nada extraido nos outros)"


def _monta_prompt_batch(
    campos: dict[str, CampoExtraido],
    transcricao: str,
) -> str:
    # monta um prompt unico pro llama avaliar todos os campos de uma vez
    blocos = []
    for nome, c in campos.items():
        # especies tem estrutura de lista com evidencia por item, passar junto
        if nome == "especies":
            if not c.valor:
                valor_str = "[]"
                ev_str = json.dumps(c.evidencia, ensure_ascii=False)
            else:
                itens = []
                evidencias_items = []
                for e in c.valor:
                    if isinstance(e, dict):
                        itens.append(e.get("nome", ""))
                        ev = e.get("evidencia", "")
                        if ev:
                            evidencias_items.append(f'"{e.get("nome","")}" -> "{ev}"')
                    else:
                        itens.append(str(e))
                valor_str = json.dumps(itens, ensure_ascii=False)
                ev_str = " | ".join(evidencias_items) if evidencias_items else json.dumps(c.evidencia, ensure_ascii=False)
        else:
            valor_str = json.dumps(c.valor, ensure_ascii=False) if c.valor is not None else "null"
            ev_str = json.dumps(c.evidencia, ensure_ascii=False)

        blocos.append(
            f"- {nome}:\n"
            f"    valor: {valor_str}\n"
            f"    evidencia: {ev_str}\n"
            f"    confianca: {c.confianca:.2f}\n"
            f"    fora_do_gazetteer: {c.fora_do_gazetteer}"
        )
    blocos_str = "\n".join(blocos)

    return f"""Voce eh um auditor de extracoes de dados de pesca brasileira.
Avalie se cada campo foi extraido CORRETAMENTE a partir da transcricao.

REGRA CENTRAL (vocabulario aberto):
- se o valor nao esta em nenhum dicionario pre-definido, isso NAO eh motivo de rejeicao
- NOMES DE PEIXES BR sao MUITOS (tilapia, traira, pacu, piau, tucunare, pirarucu, tambaqui,
  chimbore, pacu manteiga, pacu peva, piau flamengo, piraputanga etc etc). ACEITA os nomes
  se eles aparecerem como palavra/trecho na transcricao
- so rejeite se TIVER CERTEZA que:
  a) a evidencia NAO aparece literalmente no texto (alucinacao comprovada)
  b) o valor eh uma palavra claramente inventada/nonsense (ex: "filapossauro", "trabozucador")
     que nao eh nome real de peixe nem sabe o que eh
  c) o valor eh nome proprio humano confundido com entidade (ex: "Joao" como peixe)
  d) os campos conflitam geograficamente (ex: UF=RS com bacia Amazonica, impossivel)
- em DUVIDA, aceite. Prefiro dado com flag do que perder informacao real.

CAMPOS EXTRAIDOS:
{blocos_str}

TRANSCRICAO:
\"\"\"
{transcricao[:3000]}
\"\"\"

Retorne JSON com veredito POR CAMPO. Em duvida, aceita (melhor dado com flag do que perder):
{{
  "estado": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "municipio": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "rio": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "bacia": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "tipo_ceva": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "grao": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "especies": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}},
  "observacoes": {{"aceito": <bool>, "razao": "<curta>", "tipo_rejeicao": "<tipo|null>"}}
}}

tipos de rejeicao validos: evidencia_nao_alinha, conflito_cross_field, alucinacao_suspeita, confianca_baixa, nome_proprio_confundido, contexto_irrelevante

Responda APENAS o JSON."""


def avalia_batch(
    campos: dict[str, CampoExtraido],
    transcricao: str,
) -> dict[str, Veredito]:
    # roda o critic em batch, retorna dict nome_campo -> Veredito
    prompt = _monta_prompt_batch(campos, transcricao)
    cliente = ollama.Client(host=config.OLLAMA_HOST)

    try:
        resp = cliente.generate(
            model=config.MODEL_VERIFICADOR,
            prompt=prompt,
            format="json",
            options={"temperature": 0.0, "seed": 42, "num_ctx": 8192},
        )
    except Exception as e:
        # se ollama caiu, aceita tudo pra nao travar
        print(f"critic falhou (ollama): {e}")
        return {nome: Veredito(aceito=True, razao="critic indisponivel", confianca_critica=0.0) for nome in campos}

    data = parse_json_safe(resp["response"])
    if data is None:
        print(f"critic cuspiu json invalido: {resp['response'][:200]}")
        return {nome: Veredito(aceito=True, razao="json do critic quebrado", confianca_critica=0.0) for nome in campos}

    out: dict[str, Veredito] = {}
    for nome in campos:
        d = data.get(nome, {}) or {}
        tipo = d.get("tipo_rejeicao")
        if tipo not in TIPOS_VALIDOS:
            tipo = None
        out[nome] = Veredito(
            aceito=bool(d.get("aceito", True)),
            razao=str(d.get("razao", "")),
            sugestao_retry=d.get("sugestao_retry"),
            confianca_critica=0.9,
            tipo_rejeicao=tipo,
        )
    return out


# compat: mantem avalia() antigo pra nao quebrar codigo que importa
def avalia(
    nome_campo: str,
    campo: CampoExtraido,
    transcricao: str,
    outros: dict[str, CampoExtraido],
) -> Veredito:
    # versao antiga, chamada 1-a-1. redireciona pro batch com 1 campo so.
    if campo.valor is None or campo.valor == [] or campo.valor == "":
        return Veredito(aceito=True, razao="valor null, nada a verificar", confianca_critica=1.0)

    todos = {**outros, nome_campo: campo}
    resultado = avalia_batch(todos, transcricao)
    return resultado.get(nome_campo, Veredito(aceito=True, razao="fallback aceita"))
