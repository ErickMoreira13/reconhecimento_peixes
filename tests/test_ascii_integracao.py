# integracao: banners do ascii_art + ui_banners combinando
# (scripts do projeto usam os dois, quero garantir que nao brigam)

from src import ascii_art, ui_banners


def test_banner_projeto_concatena_com_banner_pipeline():
    # caso de uso: scripts/testar-retry-schema chama ambos em sequencia
    a = ascii_art.banner_projeto()
    b = ascii_art.banner_pipeline("teste")
    combinado = a + b
    assert "reconhecimento_peixes" in combinado
    assert "teste" in combinado
    # nao deve ter texto colado sem espaco/newline no meio
    assert "reconhecimento_peixesteste" not in combinado


def test_banner_pipeline_com_caixa_do_ui_banners():
    # caso de uso: script mostra banner + caixa de params
    b = ascii_art.banner_pipeline("etapa")
    c = ui_banners.caixa("params", ["modelo=llama", "limit=10"])
    combinado = b + c
    assert "etapa" in combinado
    assert "modelo=llama" in combinado
    assert "limit=10" in combinado


def test_progress_bar_em_loop_simulado():
    # simula iteracao de 10 elementos
    saidas = []
    for i in range(1, 11):
        saidas.append(ascii_art.progress_bar(i, 10, largura=10))
    # primeira tem 10%, ultima tem 100%
    assert "10%" in saidas[0]
    assert "100%" in saidas[-1]
    # todas tem o formato (i/10)
    for i, s in enumerate(saidas, 1):
        assert f"({i}/10)" in s


def test_marcas_concatenam_texto_legivel():
    # usuario ve multiplas marcas em sequencia, devem ficar distinguiveis
    o = ascii_art.marca_ok("baixou 10 videos")
    w = ascii_art.marca_warn("3 falharam")
    e = ascii_art.marca_erro("ollama fora do ar")
    todas = "\n".join([o, w, e])
    # palavras chave aparecem
    assert "baixou" in todas
    assert "ok" in todas
    assert "aviso" in todas
    assert "erro" in todas
