from src import ui_banners


def test_constantes_basicas():
    assert "><(((o>" in ui_banners.PEIXE
    assert "><(" in ui_banners.PEIXE_GRANDE
    # linha de igual nao pode ficar vazia
    assert len(ui_banners.LINHA) > 10
    assert len(ui_banners.LINHA_FINA) > 10


def test_banner_harvester_contem_peixe():
    s = ui_banners.banner_harvester()
    assert "><(((o>" in s
    assert "harvester loop" in s


def test_banner_gliner_labels_cita_labels():
    s = ui_banners.banner_gliner_labels()
    assert "2 labels" in s
    assert "4 labels" in s
    assert "rio" in s
    assert "municipio" in s


def test_banner_queries_tem_titulo():
    s = ui_banners.banner_queries()
    assert "queries" in s


def test_banner_fim_usa_titulo_passado():
    s = ui_banners.banner_fim("acabou tudo")
    assert "acabou tudo" in s


def test_caixa_renderiza_titulo_e_linhas():
    s = ui_banners.caixa("teste", ["linha1", "linha2"])
    assert "teste" in s
    assert "linha1" in s
    assert "linha2" in s
    # tem borda de mais e menos
    assert "+" in s
    assert "-" in s


def test_caixa_se_adapta_a_conteudo_longo():
    # se a linha for longa, caixa cresce. nao pode truncar
    linha_longa = "a" * 80
    s = ui_banners.caixa("t", [linha_longa])
    assert linha_longa in s


def test_caixa_vazia_nao_quebra():
    # caixa sem linhas funciona (so titulo e borda)
    s = ui_banners.caixa("so titulo", [])
    assert "so titulo" in s
    assert s.count("+") >= 2
