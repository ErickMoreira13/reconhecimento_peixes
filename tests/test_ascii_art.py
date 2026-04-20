from src import ascii_art


def test_banner_projeto_tem_nome():
    b = ascii_art.banner_projeto()
    assert "reconhecimento_peixes" in b
    assert "pescaria" in b


def test_banner_pipeline_contem_etapa():
    b = ascii_art.banner_pipeline("buscar videos")
    assert "buscar videos" in b


def test_marcas_tem_texto():
    assert "ok" in ascii_art.marca_ok("teste")
    assert "erro" in ascii_art.marca_erro("teste")
    assert "aviso" in ascii_art.marca_warn("teste")
    assert "info" in ascii_art.marca_info("teste")


def test_no_color_remove_ansi(monkeypatch):
    # com NO_COLOR setado, nao ha sequencias ANSI no output
    monkeypatch.setenv("NO_COLOR", "1")
    # recarrega o modulo pra pegar o env novo
    import importlib
    importlib.reload(ascii_art)
    b = ascii_art.banner_projeto()
    # nenhuma sequencia ANSI (comeca com \x1b[)
    assert "\x1b[" not in b
    # restaura
    monkeypatch.delenv("NO_COLOR")
    importlib.reload(ascii_art)


def test_colore_envolve_em_ansi():
    s = ascii_art.colore("oi", ascii_art.VERDE)
    # deve ter RESET no fim
    assert s.endswith(ascii_art.RESET) or s == "oi"


def test_progress_bar_completo():
    b = ascii_art.progress_bar(10, 10)
    assert "100%" in b
    assert "(10/10)" in b


def test_progress_bar_meio():
    b = ascii_art.progress_bar(5, 10, largura=10)
    assert "50%" in b
    # 5 hashes, 5 dashes
    assert "#####-----" in b


def test_progress_bar_zero():
    b = ascii_art.progress_bar(0, 10)
    assert "0%" in b


def test_progress_bar_total_zero_retorna_vazio():
    assert ascii_art.progress_bar(0, 0) == ""


def test_separador_repete_char():
    s = ascii_art.separador("-", 5, cor="")
    # 5 traços (cor='' desliga ansi)
    assert "-----" in s


def test_titulo_grande_contem_texto():
    t = ascii_art.titulo_grande("teste titulo")
    assert "teste titulo" in t
    assert "====" in t


def test_tag_fica_maiuscula():
    t = ascii_art.tag("warn")
    assert "WARN" in t
    assert "[" in t and "]" in t


def test_progress_bar_colorido_tem_porcentagem():
    b = ascii_art.progress_bar_colorido(3, 10)
    assert "30%" in b
    assert "(3/10)" in b
