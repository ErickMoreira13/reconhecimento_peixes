from src.extracao.qwen_extrator import _normaliza_especies, _monta_resultado, _tudo_null


def test_normaliza_especies_none():
    assert _normaliza_especies(None) == []


def test_normaliza_especies_vazio_str():
    assert _normaliza_especies("") == []


def test_normaliza_especies_lista_dicts_passa_direto():
    inp = [{"nome": "tucunare", "evidencia": "peguei um tucunare", "fora_do_gazetteer": False}]
    out = _normaliza_especies(inp)
    assert len(out) == 1
    assert out[0]["nome"] == "tucunare"


def test_normaliza_especies_lista_strings_vira_dicts():
    out = _normaliza_especies(["tucunare", "pacu"])
    assert len(out) == 2
    assert out[0]["nome"] == "tucunare"
    assert out[0]["evidencia"] == ""
    assert out[1]["nome"] == "pacu"


def test_normaliza_especies_string_solta_separa_por_virgula():
    # bug real que aconteceu: qwen cuspiu string em vez de lista.
    # se deixar como string passa alucinacao "so filapossauro" pra frente
    out = _normaliza_especies("tucunare, pacu, traira")
    assert len(out) == 3
    assert {e["nome"] for e in out} == {"tucunare", "pacu", "traira"}


def test_normaliza_especies_string_com_ponto_virgula():
    out = _normaliza_especies("peixe1; peixe2; peixe3")
    assert len(out) == 3


def test_normaliza_especies_tira_vazios():
    # quando qwen cospe ", , peixe, ," com virgulas esparsas
    out = _normaliza_especies("tucunare,,,  , pacu")
    nomes = {e["nome"] for e in out}
    assert nomes == {"tucunare", "pacu"}


def test_normaliza_especies_entrada_malformada_nao_crasha():
    # qualquer coisa estranha retorna lista vazia, nao levanta excecao
    assert _normaliza_especies(42) == []
    assert _normaliza_especies({"foo": "bar"}) == []


def test_tudo_null_preenche_todos_os_campos():
    out = _tudo_null(latencia_ms=100, modelo="fake:model")
    esperados = {"estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"}
    assert set(out.keys()) == esperados
    for nome, c in out.items():
        assert c.confianca == 0.0
        assert c.modelo_usado == "fake:model"
        assert c.latencia_ms == 100
    # especies eh lista vazia, outros sao None
    assert out["especies"].valor == []
    assert out["estado"].valor is None


def test_monta_resultado_converte_dict_para_campo_extraido():
    data_qwen = {
        "estado": {"valor": "SP", "confianca": 0.9, "evidencia": "em são paulo", "fora_do_gazetteer": False},
        "municipio": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "rio": {"valor": "Rio Tiete", "confianca": 0.7, "evidencia": "rio tiete"},
        "bacia": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "tipo_ceva": {"valor": "garrafa_pet_perfurada", "confianca": 0.8, "evidencia": "garrafa pet"},
        "grao": {"valor": "milho", "confianca": 0.95, "evidencia": "milho"},
        "especies": {"valor": [{"nome": "tilapia", "evidencia": "tilapias"}], "confianca": 1.0},
        "observacoes": {"valor": "pesca de tarde", "confianca": 0.6, "evidencia": ""},
    }
    out = _monta_resultado(data_qwen, latencia_ms=500, modelo="test")

    assert out["estado"].valor == "SP"
    assert out["estado"].confianca == 0.9
    assert out["rio"].valor == "Rio Tiete"
    assert out["especies"].valor[0]["nome"] == "tilapia"
    assert out["grao"].modelo_usado == "test"


def test_monta_resultado_especies_string_eh_normalizada():
    # se o modelo cuspir especies como string, deve virar lista
    data = {
        "estado": {"valor": None},
        "municipio": {"valor": None},
        "rio": {"valor": None},
        "bacia": {"valor": None},
        "tipo_ceva": {"valor": None},
        "grao": {"valor": None},
        "especies": {"valor": "tilapia, pacu"},
        "observacoes": {"valor": None},
    }
    out = _monta_resultado(data, 0, "test")
    assert isinstance(out["especies"].valor, list)
    assert len(out["especies"].valor) == 2
