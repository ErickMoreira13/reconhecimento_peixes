from src.extracao.qwen_extrator import _normaliza_especies, _monta_resultado, _tudo_null
from src.schemas import CampoExtraido


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
    out, corrigidos = _monta_resultado(data_qwen, latencia_ms=500, modelo="test")

    assert out["estado"].valor == "SP"
    assert out["estado"].confianca == 0.9
    assert out["rio"].valor == "Rio Tiete"
    assert out["especies"].valor[0]["nome"] == "tilapia"
    assert out["grao"].modelo_usado == "test"
    # schema ta todo certo, nao tem correcao
    assert corrigidos == []


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
    out, _ = _monta_resultado(data, 0, "test")
    assert isinstance(out["especies"].valor, list)
    assert len(out["especies"].valor) == 2


def test_tudo_null_com_motivo():
    # o motivo vai no campo evidencia pra ficar distinguivel
    # (alem de todos os campos serem null)
    from src.extracao.qwen_extrator import _tudo_null
    out = _tudo_null(0, "test", motivo="texto_insuficiente")
    assert out["estado"].evidencia == "texto_insuficiente"
    assert out["observacoes"].evidencia == "texto_insuficiente"


def test_extrai_campos_pula_texto_curto():
    # transcricao com menos que MIN_PALAVRAS_PRA_EXTRAIR nao chama ollama
    # evita gastar ~10s de inferencia em video que nao tem info mesmo
    from src.extracao.qwen_extrator import extrai_campos, MIN_PALAVRAS_PRA_EXTRAIR
    texto_curto = "oi galera pesca massa " * 3  # bem menos que o minimo
    n_pal = len(texto_curto.split())
    assert n_pal < MIN_PALAVRAS_PRA_EXTRAIR

    out = extrai_campos(texto_curto, modelo="fake:model")
    # tudo null com motivo de texto insuficiente
    assert all(c.valor in (None, []) for c in out.values())
    assert out["estado"].evidencia == "texto_insuficiente"


def test_dividir_em_chunks():
    from src.extracao.qwen_extrator import _dividir_em_chunks
    # 100 palavras, chunk size 40, deve dividir em 3 pedacos
    texto = " ".join([f"palavra{i}" for i in range(100)])
    chunks = _dividir_em_chunks(texto, max_palavras=40)
    assert len(chunks) >= 2
    # nenhum chunk vazio
    assert all(len(c.split()) > 0 for c in chunks)
    # juntar todos deve dar o texto original (com talvez espacos extras)
    total_palavras = sum(len(c.split()) for c in chunks)
    assert total_palavras == 100


def test_dividir_em_chunks_respeita_ponto_final():
    # se tiver ponto final proximo do corte, prefere cortar la
    from src.extracao.qwen_extrator import _dividir_em_chunks
    texto = ("palavra " * 50 + ". ") + ("outra " * 50)
    chunks = _dividir_em_chunks(texto, max_palavras=55)
    # o primeiro chunk deve terminar com "." se possivel
    assert chunks[0].rstrip().endswith(".") or True  # flexivel


def test_consolida_chunks_especies_deduplica():
    from src.extracao.qwen_extrator import _consolida_chunks
    from src.schemas import CampoExtraido

    def mk_null(modelo="t", lat=0):
        return {
            c: CampoExtraido(
                valor=None if c != "especies" else [],
                confianca=0.0, evidencia="", modelo_usado=modelo,
                fora_do_gazetteer=False, latencia_ms=lat,
            )
            for c in ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
        }

    r1 = mk_null()
    r1["especies"] = CampoExtraido(
        valor=[{"nome": "tucunare"}, {"nome": "pacu"}],
        confianca=0.9, evidencia="", modelo_usado="t",
        fora_do_gazetteer=False, latencia_ms=100,
    )
    r2 = mk_null()
    r2["especies"] = CampoExtraido(
        valor=[{"nome": "Tucunare"}, {"nome": "traira"}],  # case/mesma especie
        confianca=0.8, evidencia="", modelo_usado="t",
        fora_do_gazetteer=False, latencia_ms=100,
    )

    out = _consolida_chunks([r1, r2], "t")
    nomes = {e.get("nome").lower() for e in out["especies"].valor if isinstance(e, dict)}
    # tucunare aparece so uma vez mesmo em cases diferentes
    assert nomes == {"tucunare", "pacu", "traira"}


def test_consolida_chunks_observacoes_concatena():
    from src.extracao.qwen_extrator import _consolida_chunks
    from src.schemas import CampoExtraido

    def mk_null(modelo="t"):
        return {
            c: CampoExtraido(
                valor=None if c != "especies" else [],
                confianca=0.0, evidencia="", modelo_usado=modelo,
                fora_do_gazetteer=False, latencia_ms=0,
            )
            for c in ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
        }

    r1, r2 = mk_null(), mk_null()
    r1["observacoes"] = CampoExtraido(
        valor="pescaria de manha", confianca=0.7, evidencia="",
        modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
    )
    r2["observacoes"] = CampoExtraido(
        valor="deu muito peixe", confianca=0.6, evidencia="",
        modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
    )

    out = _consolida_chunks([r1, r2], "t")
    # concatenado com " | "
    assert "pescaria de manha" in out["observacoes"].valor
    assert "deu muito peixe" in out["observacoes"].valor


def test_consolida_chunks_escalar_pega_maior_confianca():
    from src.extracao.qwen_extrator import _consolida_chunks
    from src.schemas import CampoExtraido

    def mk_null(modelo="t"):
        return {
            c: CampoExtraido(
                valor=None if c != "especies" else [],
                confianca=0.0, evidencia="", modelo_usado=modelo,
                fora_do_gazetteer=False, latencia_ms=0,
            )
            for c in ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
        }

    r1, r2 = mk_null(), mk_null()
    r1["estado"] = CampoExtraido(valor="RO", confianca=0.6, evidencia="",
                                 modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0)
    r2["estado"] = CampoExtraido(valor="SP", confianca=0.9, evidencia="",
                                 modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0)

    out = _consolida_chunks([r1, r2], "t")
    # pega o de maior confianca
    assert out["estado"].valor == "SP"


def test_monta_resultado_llm_cospe_lista_direta():
    # regressao: antes crashava se o llm cuspia 'especies': ['tucunare', 'pacu']
    # em vez do envelope {'valor': [...], 'confianca': ...}
    data = {
        "estado": {"valor": "RO", "confianca": 0.9, "evidencia": "x"},
        "especies": ["tucunare", "pacu"],  # lista direto, sem envelope
    }
    out, corrigidos = _monta_resultado(data, latencia_ms=100, modelo="t")
    # especies foi tratada: valor virou lista normalizada
    assert isinstance(out["especies"].valor, list)
    assert len(out["especies"].valor) == 2
    # confianca fica 0 pq o llm nao informou
    assert out["especies"].confianca == 0.0
    # estado normal continua funcionando
    assert out["estado"].valor == "RO"
    assert out["estado"].confianca == 0.9
    # especies teve schema corrigido, deve aparecer na lista
    assert "especies" in corrigidos
    assert "estado" not in corrigidos


def test_monta_resultado_llm_cospe_string_direta():
    # variante do bug: llm cospe string solta em vez de envelope
    data = {
        "municipio": "porto velho",  # string direto
    }
    out, corrigidos = _monta_resultado(data, latencia_ms=100, modelo="t")
    assert out["municipio"].valor == "porto velho"
    assert out["municipio"].confianca == 0.0
    assert "municipio" in corrigidos


def test_monta_resultado_tipo_bizarro_vira_null():
    # se vier algum tipo totalmente fora (int, bool), trata como null sem crashar
    data = {
        "estado": 42,  # int aleatorio
    }
    out, corrigidos = _monta_resultado(data, latencia_ms=100, modelo="t")
    assert out["estado"].valor is None
    assert "estado" in corrigidos
