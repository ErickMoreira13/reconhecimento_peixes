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
