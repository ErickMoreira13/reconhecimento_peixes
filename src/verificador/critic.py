import json
import time

import ollama

from src import config
from src.schemas import CampoExtraido, Veredito, TipoRejeicao


# camada 2 do verificador: llm critic
# uso llama 3.1 8b pq eh familia diferente do extrator (qwen)
# ter familia diferente reduz vies circular (generator e critic nao combinam as mesmas manias)
#
# roda so nos campos que passaram nas regras deterministicas


def _monta_prompt_critic(
    nome_campo: str,
    campo: CampoExtraido,
    transcricao: str,
    outros: dict[str, CampoExtraido],
) -> str:
    # resumo curto dos outros campos pra contexto
    contexto_outros = []
    for nome, c in outros.items():
        if nome == nome_campo or c.valor is None:
            continue
        v = c.valor if not isinstance(c.valor, list) else [x.get("nome") if isinstance(x, dict) else str(x) for x in c.valor]
        contexto_outros.append(f"  - {nome}: {v}")
    outros_block = "\n".join(contexto_outros) or "  (nada extraido nos outros)"

    return f"""Voce eh um auditor de extracoes. Sua tarefa: AVALIAR se uma extracao feita por outro
modelo esta CORRETA ou se deve ser rejeitada.

LEMBRETE CRITICO: o projeto tem VOCABULARIO ABERTO. Se o valor extraido nao esta em
nenhuma lista pre-existente, isso NAO eh motivo de rejeicao. So rejeita se:
- a evidencia NAO aparece no texto (alucinacao)
- o valor eh um nome proprio confundido com entidade (ex: "Joao" como peixe)
- o valor conflita geograficamente com outros campos (ex: UF=RS com bacia Amazonica)
- o contexto do texto eh irrelevante pra aquele campo
- a confianca reportada eh muito baixa

== DADOS ==
Campo avaliado: {nome_campo}
Valor extraido: {campo.valor!r}
Evidencia: {campo.evidencia!r}
Confianca reportada pelo extrator: {campo.confianca}
Fora do gazetteer: {campo.fora_do_gazetteer}

== OUTROS CAMPOS DESSE VIDEO ==
{outros_block}

== TRANSCRICAO ==
\"\"\"
{transcricao}
\"\"\"

== DECISAO ==
Responda APENAS em JSON:
{{
  "aceito": <true|false>,
  "razao": "<frase curta>",
  "sugestao_retry": "<dica concreta pro extrator retentar ou null>",
  "confianca_critica": <float 0-1>,
  "tipo_rejeicao": "<um de: evidencia_nao_alinha, conflito_cross_field, alucinacao_suspeita, confianca_baixa, nome_proprio_confundido, contexto_irrelevante, null>"
}}

Em duvida, aceita. Melhor aceitar que perder dado novo."""


def _parse_json_veredito(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        i = raw.find("{")
        j = raw.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(raw[i:j+1])
            except json.JSONDecodeError:
                return None
    return None


def avalia(
    nome_campo: str,
    campo: CampoExtraido,
    transcricao: str,
    outros: dict[str, CampoExtraido],
) -> Veredito:
    # se o valor eh null/vazio, nao gasta llm, aceita direto
    if campo.valor is None or campo.valor == [] or campo.valor == "":
        return Veredito(aceito=True, razao="valor null, nada a verificar", confianca_critica=1.0)

    prompt = _monta_prompt_critic(nome_campo, campo, transcricao, outros)
    cliente = ollama.Client(host=config.OLLAMA_HOST)

    try:
        resp = cliente.generate(
            model=config.MODEL_VERIFICADOR,
            prompt=prompt,
            format="json",
            options={
                "temperature": 0.0,
                "seed": 42,
                "num_ctx": 8192,
            },
        )
    except Exception as e:
        # se ollama quebrou, deixa passar pra nao travar o pipeline
        print(f"critic falhou (ollama): {e}")
        return Veredito(aceito=True, razao=f"critic indisponivel: {e}", confianca_critica=0.0)

    data = _parse_json_veredito(resp["response"])
    if data is None:
        print(f"critic cuspiu json quebrado: {resp['response'][:200]}")
        return Veredito(aceito=True, razao="json quebrado, aceita por default", confianca_critica=0.0)

    tipo = data.get("tipo_rejeicao")
    tipos_validos = {
        "evidencia_nao_alinha", "conflito_cross_field", "alucinacao_suspeita",
        "confianca_baixa", "nome_proprio_confundido", "contexto_irrelevante",
    }
    # se o critic inventou "valor_fora_gazetteer" ignora, nao eh motivo valido
    if tipo not in tipos_validos:
        tipo = None

    return Veredito(
        aceito=bool(data.get("aceito", True)),
        razao=str(data.get("razao", "")),
        sugestao_retry=data.get("sugestao_retry"),
        confianca_critica=float(data.get("confianca_critica", 0.5) or 0.5),
        tipo_rejeicao=tipo,
    )
