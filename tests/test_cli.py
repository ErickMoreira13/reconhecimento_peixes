import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# testes da cli do src/main.py sem subprocess
# chama as funcoes cmd_* direto, mockando io externo (ollama, whisper, yt-dlp)


@pytest.fixture
def args_ns():
    # helper pra criar um argparse.Namespace simples
    class NS:
        def __init__(self, **kw):
            self.__dict__.update(kw)
    return NS


def test_cmd_status_db_vazio(db_isolado, capsys):
    from src.main import cmd_status
    cmd_status(MagicMock())
    saida = capsys.readouterr().out
    assert "db vazio" in saida.lower()


def test_cmd_status_com_dados(db_isolado, videos_exemplo, capsys):
    from src.main import cmd_status
    from src.storage import db as storage
    storage.upsert_videos(videos_exemplo, db_isolado)

    cmd_status(MagicMock())
    saida = capsys.readouterr().out
    assert "pendente" in saida
    assert "2" in saida  # 2 videos exemplo


def test_cmd_reconciliar_db_consistente(db_isolado, videos_exemplo, capsys):
    from src.main import cmd_reconciliar
    from src.storage import db as storage
    storage.upsert_videos(videos_exemplo, db_isolado)

    cmd_reconciliar(MagicMock())
    saida = capsys.readouterr().out
    assert "nada pra reconciliar" in saida.lower() or "consistente" in saida.lower()


def test_cmd_reconciliar_promove_pra_extraido(db_isolado, videos_exemplo, tmp_path, monkeypatch, capsys):
    # cria um arquivo _extracao.json pra simular extracao rodada que nao foi marcada no db
    from src import config
    from src.main import cmd_reconciliar
    from src.storage import db as storage

    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    storage.upsert_videos(videos_exemplo, db_isolado)
    # fabrica arquivo de extracao pro "abc123"
    (tmp_path / "abc123_extracao.json").write_text('{"campos": {}}')

    # video em 'pendente' com arquivo extracao deveria virar extraido. mas
    # o reconcilia so mexe quem esta em transcrito/baixado. marca como transcrito:
    storage.atualiza("abc123", {"status": "transcrito"}, db_isolado)

    cmd_reconciliar(MagicMock())
    saida = capsys.readouterr().out
    assert "extraido" in saida.lower()

    # confirma no db
    with storage.conectar(db_isolado) as conn:
        st = conn.execute("SELECT status FROM videos WHERE video_id='abc123'").fetchone()[0]
    assert st == "extraido"


def test_cmd_exportar_sem_dados(db_isolado, tmp_path, monkeypatch, capsys):
    from src import config
    from src.main import cmd_exportar
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)

    cmd_exportar(MagicMock())
    saida = capsys.readouterr().out
    assert "nao tem nada" in saida.lower() or "encerra" in saida.lower() or "vazio" in saida.lower() or "aviso" in saida.lower() or "pra exportar" in saida.lower()


def test_main_cli_tem_todos_os_subcomandos(capsys):
    # roda main() com --help e parseia a saida pra confirmar que todos
    # os subcomandos estao registrados
    import src.main as main
    with patch.object(sys, "argv", ["src.main", "--help"]):
        try:
            main.main()
        except SystemExit:
            pass  # --help sai com exit normal
    saida = capsys.readouterr().out

    esperados = ["buscar", "baixar", "transcrever", "extrair", "verificar",
                 "exportar", "status", "reconciliar"]
    for cmd in esperados:
        assert cmd in saida, f"subcomando {cmd} nao aparece em --help"
