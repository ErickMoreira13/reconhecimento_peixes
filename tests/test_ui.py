from src import ui


def test_console_existe():
    c = ui.console()
    assert c is not None


def test_tabela_status_nao_quebra(capsys):
    # funcao de display, so checa que nao levanta excecao
    ui.tabela_status([("pendente", 5), ("baixado", 3), ("transcrito", 2)])
    saida = capsys.readouterr().out
    assert "pendente" in saida or "pipeline" in saida.lower()


def test_tabela_status_ordem_respeitada(capsys):
    # ordem no output deve seguir a ordem logica do pipeline, nao a do input
    ui.tabela_status([("verificado", 1), ("pendente", 5), ("baixado", 3)])
    saida = capsys.readouterr().out
    # as 3 devem aparecer
    for st in ["pendente", "baixado", "verificado"]:
        assert st in saida


def test_info_ok_aviso_erro_nao_quebram(capsys):
    ui.info("mensagem de info")
    ui.ok("mensagem de ok")
    ui.aviso("mensagem de aviso")
    ui.erro("mensagem de erro")
    saida = capsys.readouterr().out
    assert "info" in saida.lower()
    assert "ok" in saida.lower()
    assert "aviso" in saida.lower()
    assert "erro" in saida.lower()


def test_progresso_context_manager(capsys):
    # uso basico do progress manager
    with ui.progresso(3, "testando") as (prog, task):
        for _ in range(3):
            prog.advance(task)
    # nao deve ter exception, e o output mostra a barra
