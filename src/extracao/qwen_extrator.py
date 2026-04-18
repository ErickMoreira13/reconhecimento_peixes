import json
import time

import ollama

from src import config
from src.schemas import CampoExtraido
from src.extracao.prompts import monta_prompt_extrator
from src.extracao import gliner_client
from src.extracao.utils import parse_json_safe as _parse_json_safe


# extrator principal: ollama/qwen single-prompt pra sair os 8 campos
# filosofia de vocabulario aberto ja ta no prompt
#
# 1 chamada por video eh mt mais rapido que 8 agentes separados (5s vs 13s no 4060)
# se o json vier quebrado, tenta retry com temp maior


# se texto tem menos que isso nao vale nem chamar o llm, retorna null direto.
# alguns videos sao shorts de 15s ou audios com falha de transcricao —
# whisper as vezes retorna 0 palavras em cortes publicitarios
MIN_PALAVRAS_PRA_EXTRAIR = 30


def _chama_ollama(prompt: str, modelo: str, temperature: float = 0.0, seed: int = 42) -> tuple[str, int]:
    # retorna (resposta, latencia_ms)
    cliente = ollama.Client(host=config.OLLAMA_HOST)

    t0 = time.monotonic()
    resp = cliente.generate(
        model=modelo,
        prompt=prompt,
        format="json",
        options={
            "temperature": temperature,
            "seed": seed,
            "num_ctx": 8192,
        },
    )
    latencia_ms = int((time.monotonic() - t0) * 1000)
    return resp["response"], latencia_ms


def extrai_campos(
    transcricao: str,
    gliner_checkpoint: str | None = None,
    modelo: str | None = None,
) -> dict[str, CampoExtraido]:
    # se nao passar modelo usa o do .env
    modelo = modelo or config.MODEL_EXTRATOR

    # 0. pula cedo se texto muito curto. whisper as vezes cuspe ""
    # em cortes publicitarios ou audios com so musica, nao vale rodar llm.
    n_palavras = len(transcricao.split())
    if n_palavras < MIN_PALAVRAS_PRA_EXTRAIR:
        print(f"transcricao muito curta ({n_palavras} palavras), pulando llm")
        return _tudo_null(0, modelo, motivo="texto_insuficiente")

    # 1. roda gliner pra pegar spans de peixe e bacia (contexto pro prompt)
    spans = gliner_client.extrai_por_label(transcricao, checkpoint_path=gliner_checkpoint)

    # 2. monta prompt com esses spans + hints dos dicts
    prompt = monta_prompt_extrator(transcricao, spans)

    # 3. chama o llm
    raw, lat_ms = _chama_ollama(prompt, modelo, temperature=0.0)
    data = _parse_json_safe(raw)

    if data is None:
        # retry com temp 0.2, as vezes funciona
        print("json quebrado no primeiro try, tentando com temp maior")
        raw, lat_ms2 = _chama_ollama(prompt, modelo, temperature=0.2, seed=99)
        lat_ms += lat_ms2
        data = _parse_json_safe(raw)

    if data is None:
        # ja era, retorna tudo null pra nao travar o pipeline
        print(f"{modelo} nao gerou json valido, resposta: {raw[:300]}")
        return _tudo_null(lat_ms, modelo, motivo="llm_json_invalido")

    return _monta_resultado(data, lat_ms, modelo)


def _tudo_null(latencia_ms: int, modelo: str, motivo: str = "") -> dict[str, CampoExtraido]:
    # fallback quando o llm nao respondeu nada util
    # motivo ajuda a distinguir no csv final se foi culpa do llm ou texto insuficiente
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}
    for c in campos:
        out[c] = CampoExtraido(
            valor=None if c != "especies" else [],
            confianca=0.0,
            evidencia=motivo,
            modelo_usado=modelo,
            fora_do_gazetteer=False,
            latencia_ms=latencia_ms,
        )
    return out


def _normaliza_especies(valor) -> list[dict]:
    # forca especies a ser sempre lista de dicts, pra nao aceitar string solta
    # (qwen as vezes cospe "especies": "peixe_x" em vez de lista — se deixar passar,
    # uma alucinacao tipo "só filapossauro" entra como string e ninguem pega)
    if valor is None or valor == "":
        return []
    if isinstance(valor, list):
        normalizada = []
        for item in valor:
            if isinstance(item, dict):
                normalizada.append({
                    "nome": str(item.get("nome", "")).strip(),
                    "evidencia": str(item.get("evidencia", "")).strip(),
                    "fora_do_gazetteer": bool(item.get("fora_do_gazetteer", False)),
                })
            elif isinstance(item, str):
                normalizada.append({"nome": item.strip(), "evidencia": "", "fora_do_gazetteer": False})
        # tira entradas vazias
        return [e for e in normalizada if e.get("nome")]
    if isinstance(valor, str):
        # qwen cuspiu string solta, tenta separar por virgula/ponto-e-virgula
        # se for algo muito estranho, a camada seguinte (critic) deve pegar
        partes = [p.strip() for p in valor.replace(";", ",").split(",") if p.strip()]
        return [{"nome": p, "evidencia": "", "fora_do_gazetteer": False} for p in partes]
    return []


def _monta_resultado(data: dict, latencia_ms: int, modelo: str) -> dict[str, CampoExtraido]:
    # converte o dict cru do llm em CampoExtraido pra cada um
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}

    for c in campos:
        item = data.get(c, {}) or {}

        if c == "especies":
            valor = _normaliza_especies(item.get("valor"))
        else:
            valor = item.get("valor")

        out[c] = CampoExtraido(
            valor=valor,
            confianca=float(item.get("confianca", 0.0) or 0.0),
            evidencia=str(item.get("evidencia", "") or ""),
            modelo_usado=modelo,
            fora_do_gazetteer=bool(item.get("fora_do_gazetteer", False)),
            latencia_ms=latencia_ms,
        )

    return out
