from src.extracao.utils import parse_json_safe


# mais edge cases alem do test_parse_json.py original


def test_parse_json_com_null():
    d = parse_json_safe('{"valor": null}')
    assert d == {"valor": None}


def test_parse_json_com_array():
    d = parse_json_safe('{"lista": [1, 2, 3]}')
    assert d["lista"] == [1, 2, 3]


def test_parse_json_com_string_com_aspas_escapadas():
    d = parse_json_safe('{"texto": "ele disse \\"oi\\""}')
    assert d is not None
    assert d["texto"] == 'ele disse "oi"'


def test_parse_json_com_chaves_em_portugues_com_acento():
    d = parse_json_safe('{"acao": "correr", "coracao": "batendo"}')
    assert d is not None


def test_parse_json_recupera_de_pergunta_final():
    # llm as vezes cospe "Aqui esta: {...}. Posso ajudar mais?"
    raw = 'Aqui esta: {"campo": "valor"}. Posso ajudar mais?'
    d = parse_json_safe(raw)
    assert d == {"campo": "valor"}


def test_parse_json_com_fence_json():
    d = parse_json_safe('```json\n{"a": 1}\n```')
    assert d == {"a": 1}


def test_parse_json_so_com_fence_vazio():
    d = parse_json_safe('```json\n\n```')
    assert d is None


def test_parse_json_whitespace_apenas():
    assert parse_json_safe("   \n\t   ") is None


def test_parse_json_nao_eh_dict():
    # so esperamos dict no nivel top. se for array ou string, nao serve
    # (mas pelo contrato da funcao, qualquer json valido eh aceito)
    # na pratica so vem dict do llm entao nao ha problema
    result = parse_json_safe('[1, 2, 3]')
    # a funcao atual retorna o que json.loads der
    assert result == [1, 2, 3]


def test_parse_json_profundamente_aninhado():
    raw = '{"a": {"b": {"c": {"d": {"e": "deep"}}}}}'
    d = parse_json_safe(raw)
    assert d["a"]["b"]["c"]["d"]["e"] == "deep"
