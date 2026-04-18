from unittest.mock import patch, MagicMock

import pytest

from src.harvester import youtube as yt


# testes sem hitar rede nem yt-dlp. mocka os internals


class FakeResp:
    def __init__(self, status_code: int, data: dict | None = None):
        self.status_code = status_code
        self._data = data or {}
        self.text = str(self._data)

    def json(self):
        return self._data


def _api_resp_ok(n_videos: int = 3, page_token: str | None = None) -> dict:
    items = [
        {
            "id": {"videoId": f"vid_{i}"},
            "snippet": {
                "title": f"titulo {i}",
                "publishedAt": "2025-01-01T00:00:00Z",
                "channelTitle": f"canal_{i}",
                "description": "descricao",
            },
        }
        for i in range(n_videos)
    ]
    out = {"items": items}
    if page_token:
        out["nextPageToken"] = page_token
    return out


def test_busca_videos_retorna_lista(monkeypatch):
    from src import config
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", ["fake_key_1"])

    def mock_get(url, params=None, timeout=None):
        return FakeResp(200, _api_resp_ok(3))

    monkeypatch.setattr("requests.get", mock_get)

    videos = yt.busca_videos("pesca", max_videos=3)
    assert len(videos) == 3
    assert all("video_id" in v for v in videos)
    assert all("url" in v for v in videos)


def test_busca_videos_respeita_max(monkeypatch):
    from src import config
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", ["k1"])
    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResp(200, _api_resp_ok(50)))

    videos = yt.busca_videos("pesca", max_videos=5)
    # quando mocko API com 50 videos/pagina, mas max=5 so retorna 5
    assert len(videos) == 5


def test_busca_videos_sem_keys_levanta(monkeypatch):
    from src import config
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", [])
    with pytest.raises(RuntimeError, match="sem keys"):
        yt.busca_videos("pesca", max_videos=5)


def test_busca_videos_api_403_tenta_proxima_key(monkeypatch):
    # quando uma key retorna 403 (quota), deve tentar a proxima
    from src import config
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", ["k1", "k2"])

    chamadas = {"n": 0}
    def mock_get(url, params=None, timeout=None):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return FakeResp(403, {"error": "quota"})
        return FakeResp(200, _api_resp_ok(2))

    monkeypatch.setattr("requests.get", mock_get)

    videos = yt.busca_videos("pesca", max_videos=2)
    assert len(videos) == 2
    assert chamadas["n"] >= 2


def test_busca_videos_todas_keys_queimadas(monkeypatch):
    from src import config
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", ["k1", "k2"])
    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResp(403))

    videos = yt.busca_videos("pesca", max_videos=10)
    assert videos == []


def test_video_tem_campos_essenciais(monkeypatch):
    from src import config
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", ["k1"])
    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResp(200, _api_resp_ok(1)))

    videos = yt.busca_videos("pesca", max_videos=1)
    v = videos[0]
    for campo in ["video_id", "url", "title", "channel", "published_at", "query_origem"]:
        assert campo in v
    assert v["url"].startswith("https://www.youtube.com/watch?v=")


def test_salva_metadata_persiste_no_db(db_isolado, videos_exemplo):
    yt.salva_metadata(videos_exemplo, db_isolado)
    pendentes = yt.pega_pendentes(db_isolado, limit=10)
    assert len(pendentes) == 2


def test_marca_baixado_muda_status(db_isolado, videos_exemplo, tmp_path):
    yt.salva_metadata(videos_exemplo, db_isolado)
    audio_path = tmp_path / "abc123.opus"
    audio_path.write_text("fake audio")

    yt.marca_baixado("abc123", audio_path, db_isolado)

    pendentes = yt.pega_pendentes(db_isolado, limit=10)
    # so xyz789 continua pendente
    assert len(pendentes) == 1
    assert pendentes[0]["video_id"] == "xyz789"


def test_marca_falhou_tira_dos_pendentes(db_isolado, videos_exemplo):
    yt.salva_metadata(videos_exemplo, db_isolado)
    yt.marca_falhou("abc123", db_isolado)

    pendentes = yt.pega_pendentes(db_isolado, limit=10)
    assert all(p["video_id"] != "abc123" for p in pendentes)
