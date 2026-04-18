import json

import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi nao instalado, pulando testes do dashboard", allow_module_level=True)

from src.dashboard.server import app
from src.storage import db as storage


@pytest.fixture
def client(db_isolado, videos_exemplo):
    # popula o db e devolve um test client
    storage.upsert_videos(videos_exemplo, db_isolado)
    return TestClient(app)


def test_index_retorna_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "pipeline" in r.text.lower()


def test_api_status_tem_contagem(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "por_status" in data
    assert "total" in data
    assert data["total"] >= 2
    assert data["por_status"]["pendente"] == 2


def test_api_status_sem_db_retorna_404(tmp_path, monkeypatch):
    # sem db, deve dar 404 com mensagem amigavel
    from src.dashboard import server as dash
    monkeypatch.setattr(dash, "DB_PATH", tmp_path / "naoexiste.db")
    from src.storage import db as st
    monkeypatch.setattr(st, "DB_PATH", tmp_path / "naoexiste.db")
    c = TestClient(app)
    r = c.get("/api/status")
    assert r.status_code == 404


def test_api_resultado_inexistente(client):
    r = client.get("/api/resultado/video_que_nao_existe")
    assert r.status_code == 404


def test_api_flags_retorna_dict(client):
    r = client.get("/api/flags")
    assert r.status_code == 200
    data = r.json()
    # sem resultados ainda extraidos, retorna dict vazio
    assert isinstance(data, dict)


def test_api_status_estrutura_campos(client):
    r = client.get("/api/status")
    data = r.json()
    # campos esperados pela view html
    for k in ["por_status", "total", "ultimos_baixados", "ultimos_transcritos", "ultimos_extraidos", "atualizado_em"]:
        assert k in data
