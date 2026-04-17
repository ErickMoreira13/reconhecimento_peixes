import json
import time

import ollama

from src import config
from src.schemas import CampoExtraido
from src.extracao.prompts import monta_prompt_extrator
from src.extracao import gliner_client


# extrator principal: ollama/qwen single-prompt pra sair os 8 campos
# filosofia de vocabulario aberto ja ta no prompt
#
# 1 chamada por video eh mt mais rapido que 8 agentes separados (5s vs 13s no 4060)
# se o json vier quebrado, tenta retry com temp maior


def _parse_json_safe(raw: str) -> dict | None:
    # ollama as vezes cospe texto antes/depois do json, tenta achar o objeto
    raw = raw.strip()
    if raw.startswith("```"):
        # remove cercas de markdown se tiver
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # ultima tentativa: pega do primeiro { ate o ultimo }
        i = raw.find("{")
        j = raw.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(raw[i:j+1])
            except json.JSONDecodeError:
                return None
        return None


def _chama_ollama(prompt: str, temperature: float = 0.0, seed: int = 42) -> tuple[str, int]:
    # retorna (resposta, latencia_ms)
    cliente = ollama.Client(host=config.OLLAMA_HOST)

    t0 = time.monotonic()
    resp = cliente.generate(
        model=config.MODEL_EXTRATOR,
        prompt=prompt,
        format="json",  # forca json strict, qwen suporta bem
        options={
            "temperature": temperature,
            "seed": seed,
            "num_ctx": 8192,
        },
    )
    latencia_ms = int((time.monotonic() - t0) * 1000)
    return resp["response"], latencia_ms


def extrai_campos(transcricao: str, gliner_checkpoint: str | None = None) -> dict[str, CampoExtraido]:
    # 1. roda gliner pra pegar spans de peixe e bacia (contexto pro prompt)
    spans = gliner_client.extrai_por_label(transcricao, checkpoint_path=gliner_checkpoint)

    # 2. monta prompt com esses spans + hints dos dicts
    prompt = monta_prompt_extrator(transcricao, spans)

    # 3. chama qwen
    raw, lat_ms = _chama_ollama(prompt, temperature=0.0)
    data = _parse_json_safe(raw)

    if data is None:
        # retry com temp 0.2, as vezes funciona
        print("json quebrado no primeiro try, tentando com temp maior")
        raw, lat_ms2 = _chama_ollama(prompt, temperature=0.2, seed=99)
        lat_ms += lat_ms2
        data = _parse_json_safe(raw)

    if data is None:
        # ja era, retorna tudo null pra nao travar o pipeline
        print(f"qwen nao gerou json valido, resposta: {raw[:300]}")
        return _tudo_null(lat_ms)

    return _monta_resultado(data, lat_ms)


def _tudo_null(latencia_ms: int) -> dict[str, CampoExtraido]:
    # fallback quando o qwen nao respondeu nada util
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}
    for c in campos:
        out[c] = CampoExtraido(
            valor=None if c != "especies" else [],
            confianca=0.0,
            evidencia="",
            modelo_usado=config.MODEL_EXTRATOR,
            fora_do_gazetteer=False,
            latencia_ms=latencia_ms,
        )
    return out


def _monta_resultado(data: dict, latencia_ms: int) -> dict[str, CampoExtraido]:
    # converte o dict cru do qwen em CampoExtraido pra cada um
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}

    for c in campos:
        item = data.get(c, {}) or {}
        valor = item.get("valor") if c != "especies" else item.get("valor", [])

        out[c] = CampoExtraido(
            valor=valor,
            confianca=float(item.get("confianca", 0.0) or 0.0),
            evidencia=str(item.get("evidencia", "") or ""),
            modelo_usado=config.MODEL_EXTRATOR,
            fora_do_gazetteer=bool(item.get("fora_do_gazetteer", False)),
            latencia_ms=latencia_ms,
        )

    return out
