from src.extracao.qwen_extrator import _parse_json_safe


def test_json_limpo():
    raw = '{"a": 1, "b": 2}'
    d = _parse_json_safe(raw)
    assert d == {"a": 1, "b": 2}


def test_json_com_markdown_fence():
    # ollama as vezes cospe com ```json ... ```
    raw = '```json\n{"campo": "valor"}\n```'
    d = _parse_json_safe(raw)
    assert d == {"campo": "valor"}


def test_json_com_texto_antes_e_depois():
    # algumas respostas tem "Aqui esta o JSON: {...} - espero que ajude!"
    raw = 'aqui esta o json: {"campo": "valor"} fim'
    d = _parse_json_safe(raw)
    assert d == {"campo": "valor"}


def test_json_completamente_quebrado():
    d = _parse_json_safe("isso nao eh json nenhum")
    assert d is None


def test_json_com_quebras_de_linha():
    raw = """
    {
      "estado": "RO",
      "confianca": 0.9
    }
    """
    d = _parse_json_safe(raw)
    assert d is not None
    assert d["estado"] == "RO"


def test_json_vazio():
    assert _parse_json_safe("") is None


def test_json_aninhado():
    raw = '{"outer": {"inner": {"valor": 42}}}'
    d = _parse_json_safe(raw)
    assert d["outer"]["inner"]["valor"] == 42
