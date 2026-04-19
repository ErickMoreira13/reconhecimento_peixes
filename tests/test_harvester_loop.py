from pathlib import Path

import pytest

from src.harvester import loop as hloop
from src.harvester import youtube as yt
from src.storage import db as storage


@pytest.fixture
def yaml_tmp(tmp_path):
    # arquivo yaml minimo pra teste
    p = tmp_path / "queries.yaml"
    p.write_text("queries:\n  - a\n  - b\n  - c\n", encoding="utf-8")
    return p


def test_carrega_queries_yaml(yaml_tmp):
    qs = hloop.carrega_queries_yaml(yaml_tmp)
    assert qs == ["a", "b", "c"]


def test_ids_ja_vistos_vazio(db_isolado):
    assert hloop.ids_ja_vistos(db_isolado) == set()


def test_ids_ja_vistos_popula(db_isolado, videos_exemplo):
    yt.salva_metadata(videos_exemplo, db_isolado)
    ids = hloop.ids_ja_vistos(db_isolado)
    assert ids == {"abc123", "xyz789"}


def test_processa_query_todos_novos(db_isolado, monkeypatch):
    # mocka busca pra retornar 3 videos novos
    def fake_busca(q, max_videos=50, ultimos_anos=10):
        return [
            {"video_id": f"v{i}", "url": f"u{i}", "title": f"t{i}",
             "channel": "c", "published_at": "2025-01-01T00:00:00Z",
             "query_origem": q}
            for i in range(3)
        ]
    monkeypatch.setattr(hloop.yt, "busca_videos", fake_busca)
    storage.upsert_queries(["q1"], db_isolado)

    res = hloop.processa_query("q1", db_isolado)

    assert res["novos"] == 3
    assert res["dedup_rate"] == 0.0
    assert res["saturou"] is False


def test_processa_query_tudo_repetido_satura(db_isolado, monkeypatch, videos_exemplo):
    # popula db com 2 videos, mock retorna os mesmos 2
    yt.salva_metadata(videos_exemplo, db_isolado)
    storage.upsert_queries(["q1"], db_isolado)

    def fake_busca(q, max_videos=50, ultimos_anos=10):
        return videos_exemplo

    monkeypatch.setattr(hloop.yt, "busca_videos", fake_busca)

    res = hloop.processa_query("q1", db_isolado)

    assert res["dedup_rate"] == 1.0
    assert res["novos"] == 0
    assert res["saturou"] is True
    assert res["motivo"] == "dedup_alto"


def test_processa_query_erro_nao_quebra(db_isolado, monkeypatch):
    # se youtube falhar, retorna estrutura vazia sem crashar
    def fake_busca(*a, **k):
        raise RuntimeError("youtube fora do ar")

    monkeypatch.setattr(hloop.yt, "busca_videos", fake_busca)
    storage.upsert_queries(["q1"], db_isolado)

    res = hloop.processa_query("q1", db_isolado)

    assert res["novos"] == 0
    assert res["saturou"] is False


def test_roda_loop_para_quando_todas_saturam(db_isolado, yaml_tmp, monkeypatch):
    # mocka busca sempre retornando repetidos, forcando saturacao rapida
    call_count = {"n": 0}

    def fake_busca(q, max_videos=50, ultimos_anos=10):
        call_count["n"] += 1
        # retorna um video ja visto pra dar dedup alto
        # primeira vez salva o video, segunda em diante eh repetido
        return [{"video_id": f"video_{q}", "url": "u", "title": "t",
                 "channel": "c", "published_at": "2025-01-01T00:00:00Z",
                 "query_origem": q}]

    # popula db com os ids que a busca vai retornar pra forcar dedup=1.0
    yt.salva_metadata([
        {"video_id": "video_a", "url": "u", "title": "t",
         "channel": "c", "published_at": "2025-01-01T00:00:00Z",
         "query_origem": "a"},
        {"video_id": "video_b", "url": "u", "title": "t",
         "channel": "c", "published_at": "2025-01-01T00:00:00Z",
         "query_origem": "b"},
        {"video_id": "video_c", "url": "u", "title": "t",
         "channel": "c", "published_at": "2025-01-01T00:00:00Z",
         "query_origem": "c"},
    ], db_isolado)

    monkeypatch.setattr(hloop.yt, "busca_videos", fake_busca)
    # pausa zero pra nao atrasar teste
    hloop.roda_loop(yaml_tmp, pausa_s=0, db_path=db_isolado)

    # todas devem ter saturado
    satur = storage.lista_queries("saturada", db_isolado)
    assert len(satur) == 3


def test_roda_loop_respeita_max_iter(db_isolado, yaml_tmp, monkeypatch):
    def fake_busca(q, max_videos=50, ultimos_anos=10):
        # sempre traz novos, nunca satura
        import uuid
        return [{"video_id": uuid.uuid4().hex, "url": "u", "title": "t",
                 "channel": "c", "published_at": "2025-01-01T00:00:00Z",
                 "query_origem": q}]

    monkeypatch.setattr(hloop.yt, "busca_videos", fake_busca)
    hloop.roda_loop(yaml_tmp, max_iteracoes=2, pausa_s=0, db_path=db_isolado)

    # 2 iteracoes, 2 queries atualizadas com total_buscados > 0
    rows = storage.lista_queries(db_path=db_isolado)
    buscadas = [r for r in rows if r["total_buscados"] > 0]
    assert len(buscadas) == 2
