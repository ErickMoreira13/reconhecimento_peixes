import json


# utilitarios puros, sem dep do ollama
# fica separado pros testes rodarem sem precisar instalar o client do llm


def parse_json_safe(raw: str) -> dict | None:
    # ollama as vezes cospe texto fora do json ou com cerca de markdown
    # essa funcao tenta varias estrategias pra recuperar o dict
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if "```" in raw[3:] else raw[3:]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # ultima tentativa: pega do primeiro { ate o ultimo }
    i = raw.find("{")
    j = raw.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(raw[i:j+1])
        except json.JSONDecodeError:
            return None

    return None
