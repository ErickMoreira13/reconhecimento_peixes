import time

import ollama

from src import config
from src.schemas import CampoExtraido, Veredito
from src.verificador import regras, critic
from src.extracao.prompts import monta_prompt_extrator
from src.extracao.qwen_extrator import _parse_json_safe, _chama_ollama


# loop do verificador com retry budget
# filosofia: regras primeiro (baratas), depois critic (caro), depois re-extrair se rejeitou
#
# budget padrao: 2 retries.
# tentativa 1: temp 0.0
# tentativa 2: temp 0.2 + feedback injection (passa razao da rejeicao)
# tentativa 3: temp 0.4 + fallback pra gemma 3 4b (vies diferente)


BUDGET_RETRIES = 2
TEMPS_ESCALACAO = [0.0, 0.2, 0.4]
MODEL_FALLBACK = "gemma3:4b"


def _reextrai_campo(
    transcricao: str,
    spans_gliner: dict,
    campo_nome: str,
    veredito_anterior: Veredito,
    tentativa: int,
) -> CampoExtraido | None:
    # reextrai SO o campo rejeitado, nao o json inteiro
    # passa a razao da rejeicao como feedback pro modelo nao repetir o erro
    temp = TEMPS_ESCALACAO[min(tentativa, len(TEMPS_ESCALACAO) - 1)]
    usar_fallback = tentativa >= 2

    # monta prompt focado so no campo que falhou, mais curto
    feedback = ""
    if veredito_anterior:
        feedback = f"""
ATENCAO: tentativa anterior foi REJEITADA pelo auditor.
Razao: {veredito_anterior.razao}
Sugestao: {veredito_anterior.sugestao_retry or "reveja a evidencia"}
Reavalie com mais cuidado. Nao invente. Em duvida, retorne null.
"""

    prompt = f"""Voce eh um extrator especialista em pesca brasileira.
Extraia APENAS o campo "{campo_nome}" da transcricao.

{feedback}

REGRAS:
- vocabulario aberto — se nao casa com lista conhecida, retorne o valor bruto do texto
- evidencia tem que ser trecho LITERAL da transcricao
- se nao foi mencionado, retorne null
- marque fora_do_gazetteer=true quando o valor nao bate com lista conhecida

Retorne JSON:
{{
  "valor": <str, lista ou null>,
  "confianca": <float 0-1>,
  "evidencia": "<trecho literal>",
  "fora_do_gazetteer": <bool>
}}

TRANSCRICAO:
\"\"\"
{transcricao}
\"\"\"
"""
    modelo = MODEL_FALLBACK if usar_fallback else config.MODEL_EXTRATOR
    cliente = ollama.Client(host=config.OLLAMA_HOST)

    t0 = time.monotonic()
    try:
        resp = cliente.generate(
            model=modelo,
            prompt=prompt,
            format="json",
            options={"temperature": temp, "num_ctx": 8192},
        )
    except Exception as e:
        print(f"retry falhou: {e}")
        return None
    lat_ms = int((time.monotonic() - t0) * 1000)

    data = _parse_json_safe(resp["response"])
    if data is None:
        return None

    return CampoExtraido(
        valor=data.get("valor"),
        confianca=float(data.get("confianca", 0.0) or 0.0),
        evidencia=str(data.get("evidencia", "") or ""),
        modelo_usado=modelo,
        fora_do_gazetteer=bool(data.get("fora_do_gazetteer", False)),
        latencia_ms=lat_ms,
    )


def verifica_campo_com_retry(
    nome_campo: str,
    campo: CampoExtraido,
    transcricao: str,
    outros: dict[str, CampoExtraido],
    spans_gliner: dict,
    budget: int = BUDGET_RETRIES,
) -> tuple[CampoExtraido, Veredito, int]:
    # retorna o campo final (pode ter sido reextraido), o veredito final, e quantos retries gastou
    veredito: Veredito | None = None
    tentativas = 0

    campo_atual = campo

    while tentativas <= budget:
        # camada 1: regras
        v_reg = regras.aplica_regras(nome_campo, campo_atual, transcricao, outros)
        if not v_reg.aceito:
            veredito = v_reg
            tentativas += 1
            if tentativas > budget:
                # acabou retries, flag no campo
                campo_atual.evidencia = f"[rejeitado_{budget}x] {campo_atual.evidencia}"
                campo_atual.valor = None if not isinstance(campo_atual.valor, list) else []
                return campo_atual, veredito, tentativas

            novo = _reextrai_campo(transcricao, spans_gliner, nome_campo, veredito, tentativas)
            if novo is None:
                # reextrair falhou, aceita o que tinha com flag
                return campo_atual, veredito, tentativas
            campo_atual = novo
            continue

        # camada 2: critic
        v_cri = critic.avalia(nome_campo, campo_atual, transcricao, outros)
        if not v_cri.aceito:
            veredito = v_cri
            tentativas += 1
            if tentativas > budget:
                campo_atual.evidencia = f"[rejeitado_{budget}x] {campo_atual.evidencia}"
                campo_atual.valor = None if not isinstance(campo_atual.valor, list) else []
                return campo_atual, veredito, tentativas

            novo = _reextrai_campo(transcricao, spans_gliner, nome_campo, veredito, tentativas)
            if novo is None:
                return campo_atual, veredito, tentativas
            campo_atual = novo
            continue

        # passou nas duas camadas
        return campo_atual, v_cri, tentativas

    # saida do loop sem retornar (nao deveria chegar aqui)
    return campo_atual, veredito or Veredito(aceito=True, razao="sem verificacao"), tentativas


def verifica_todos_os_campos(
    campos: dict[str, CampoExtraido],
    transcricao: str,
    spans_gliner: dict,
) -> dict[str, dict]:
    # aplica verificacao em todos os 8 campos
    # retorna dict com campo final + veredito + tentativas pra cada um
    out: dict[str, dict] = {}
    for nome, c in campos.items():
        # passa os outros campos ja verificados como contexto (cross-field)
        outros = {n: o["campo"] for n, o in out.items()}
        novo_campo, veredito, tents = verifica_campo_com_retry(
            nome, c, transcricao, outros, spans_gliner
        )
        out[nome] = {
            "campo": novo_campo,
            "veredito": veredito,
            "tentativas": tents,
        }
    return out
