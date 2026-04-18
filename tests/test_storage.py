import sqlite3
from pathlib import Path

import pytest

from src.storage import db as storage


@pytest.fixture
def db_temp(tmp_path):
    # sqlite temporario pra cada teste nao contaminar outros
    # (fixture local aqui porque muitos testes abaixo usam o path direto em vez
    # do DB_PATH global que o db_isolado substitui)
    return tmp_path / "teste.db"


def test_schema_cria_tabela_videos(db_temp):
    with storage.conectar(db_temp) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(videos)").fetchall()]
    # colunas essenciais
    for esperada in ["video_id", "url", "status", "audio_path", "transcricao_path"]:
        assert esperada in cols


def test_upsert_insere_videos(db_temp):
    videos = [
        {"video_id": "abc", "url": "http://x", "title": "t1", "channel": "c1", "published_at": "2025-01-01", "query_origem": "q"},
        {"video_id": "xyz", "url": "http://y", "title": "t2", "channel": "c2", "published_at": "2025-02-01", "query_origem": "q"},
    ]
    storage.upsert_videos(videos, db_temp)

    with storage.conectar(db_temp) as conn:
        n = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    assert n == 2


def test_upsert_ignora_duplicado(db_temp):
    v = {"video_id": "abc", "url": "http://x", "title": "t1", "channel": "c1", "published_at": "2025-01-01"}
    storage.upsert_videos([v], db_temp)
    storage.upsert_videos([v], db_temp)  # segundo insert deve ser ignorado
    storage.upsert_videos([v], db_temp)

    with storage.conectar(db_temp) as conn:
        n = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    assert n == 1


def test_atualiza_muda_status(db_temp):
    storage.upsert_videos([
        {"video_id": "abc", "url": "http://x", "title": "t", "channel": "c", "published_at": "2025-01-01"}
    ], db_temp)

    storage.atualiza("abc", {"status": "baixado", "audio_path": "/tmp/x.opus"}, db_temp)

    with storage.conectar(db_temp) as conn:
        row = conn.execute("SELECT status, audio_path FROM videos WHERE video_id = 'abc'").fetchone()
    assert row == ("baixado", "/tmp/x.opus")


def test_pega_por_status_filtra(db_temp):
    storage.upsert_videos([
        {"video_id": "a", "url": "u1", "title": "t1", "channel": "c", "published_at": "2025-01-01"},
        {"video_id": "b", "url": "u2", "title": "t2", "channel": "c", "published_at": "2025-01-01"},
        {"video_id": "c", "url": "u3", "title": "t3", "channel": "c", "published_at": "2025-01-01"},
    ], db_temp)
    storage.atualiza("a", {"status": "baixado"}, db_temp)
    storage.atualiza("b", {"status": "baixado"}, db_temp)
    # c fica como pendente

    baixados = storage.pega_por_status("baixado", 10, ["video_id", "url"], db_temp)
    pendentes = storage.pega_por_status("pendente", 10, ["video_id"], db_temp)

    assert len(baixados) == 2
    assert len(pendentes) == 1
    assert pendentes[0]["video_id"] == "c"


def test_pega_por_status_respeita_limit(db_temp):
    videos = [
        {"video_id": f"id{i}", "url": "u", "title": "t", "channel": "c", "published_at": "2025-01-01"}
        for i in range(10)
    ]
    storage.upsert_videos(videos, db_temp)

    result = storage.pega_por_status("pendente", 3, ["video_id"], db_temp)
    assert len(result) == 3


def test_contagem_por_status(db_temp):
    storage.upsert_videos([
        {"video_id": "a", "url": "u", "title": "t", "channel": "c", "published_at": "2025-01-01"},
        {"video_id": "b", "url": "u", "title": "t", "channel": "c", "published_at": "2025-01-01"},
    ], db_temp)
    storage.atualiza("a", {"status": "baixado"}, db_temp)

    rows = dict(storage.contagem_por_status(db_temp))
    assert rows.get("baixado") == 1
    assert rows.get("pendente") == 1


def test_schema_idempotente(db_temp):
    # rodar conectar varias vezes nao deve quebrar nem duplicar
    with storage.conectar(db_temp):
        pass
    with storage.conectar(db_temp):
        pass
    with storage.conectar(db_temp):
        pass
    # se passou sem exception, ok


def test_schema_upgrade_em_db_antigo(db_temp, tmp_path):
    # simula um db antigo sem a coluna transcricao_path e ve se adiciona
    conn = sqlite3.connect(db_temp)
    conn.execute("""
        CREATE TABLE videos (
            video_id TEXT PRIMARY KEY,
            url TEXT,
            status TEXT DEFAULT 'pendente'
        )
    """)
    conn.commit()
    conn.close()

    # agora chama conectar(), deve adicionar as colunas faltantes
    with storage.conectar(db_temp) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(videos)").fetchall()]

    assert "transcricao_path" in cols
    assert "extraido_em" in cols
