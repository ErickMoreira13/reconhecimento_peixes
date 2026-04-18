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
    # nova versao: aplica regras 1x por campo, depois 1 chamada batch no critic
    # com vereditos de todos os 8 campos, depois faz retry so nos rejeitados.
    # tres a quatro chamadas ollama no pior caso, em vez de 8+ no velho
    out: dict[str, dict] = {}

    # 1. aplica regras em todos primeiro (cheap gate)
    vereditos_regras: dict[str, Veredito] = {}
    for nome, c in campos.items():
        # passa os outros ja avaliados como contexto (pra cross-field)
        outros_ja = {n: out_nome["campo"] for n, out_nome in out.items()}
        v = regras.aplica_regras(nome, c, transcricao, outros_ja)
        vereditos_regras[nome] = v
        out[nome] = {"campo": c, "veredito": v, "tentativas": 0}

    # 2. critic batch nos que passaram nas regras (1 chamada ollama so)
    passaram = {nome: out[nome]["campo"] for nome, v in vereditos_regras.items() if v.aceito}
    if passaram:
        vereditos_critic = critic.avalia_batch(passaram, transcricao)
        for nome, v_crit in vereditos_critic.items():
            if not v_crit.aceito:
                out[nome]["veredito"] = v_crit

    # 3. retry nos rejeitados (regras OU critic)
    for nome in list(out.keys()):
        v = out[nome]["veredito"]
        if v.aceito:
            continue

        # tenta re-extrair ate esgotar o budget
        for tentativa in range(1, BUDGET_RETRIES + 1):
            novo = _reextrai_campo(transcricao, spans_gliner, nome, v, tentativa)
            if novo is None:
                break

            # checa regras de novo
            outros_ja = {n: out[n]["campo"] for n in out if n != nome}
            v_reg = regras.aplica_regras(nome, novo, transcricao, outros_ja)
            if not v_reg.aceito:
                v = v_reg
                out[nome].update({"campo": novo, "veredito": v_reg, "tentativas": tentativa})
                continue

            # passou nas regras, critic so nesse campo
            v_crit = critic.avalia(nome, novo, transcricao, outros_ja)
            if v_crit.aceito:
                out[nome].update({"campo": novo, "veredito": v_crit, "tentativas": tentativa})
                break
            v = v_crit
            out[nome].update({"campo": novo, "veredito": v_crit, "tentativas": tentativa})

        # se ainda rejeitado apos retries, anula o valor
        if not out[nome]["veredito"].aceito:
            c_final = out[nome]["campo"]
            c_final.evidencia = f"[rejeitado_{out[nome]['tentativas']}x] {c_final.evidencia}"
            if isinstance(c_final.valor, list):
                c_final.valor = []
            else:
                c_final.valor = None

    return out
