import os
import sys
from pathlib import Path

import pytest

# garante que o src/ ta no path pros testes
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# seta envs fake pra nao precisar de .env real rodando os testes
os.environ.setdefault("YOUTUBE_API_KEYS", "fake_key_1,fake_key_2")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("WHISPER_DEVICE", "cpu")


@pytest.fixture
def db_isolado(tmp_path, monkeypatch):
    # db sqlite isolado por teste. usa monkeypatch pra redirecionar
    # o DB_PATH do modulo storage e qualquer outro que use config.DATA_DIR
    db = tmp_path / "teste.db"
    from src.storage import db as storage
    monkeypatch.setattr(storage, "DB_PATH", db)
    return db


@pytest.fixture
def videos_exemplo():
    # uns videos fake pros testes que precisam de dado populado
    return [
        {"video_id": "abc123", "url": "https://youtu.be/abc123", "title": "pesca com ceva no rio madeira",
         "channel": "Canal Teste 1", "published_at": "2025-03-10T12:00:00Z", "query_origem": "pesca com ceva"},
        {"video_id": "xyz789", "url": "https://youtu.be/xyz789", "title": "tucunare gigante em rondonia",
         "channel": "Canal Teste 2", "published_at": "2025-05-20T15:30:00Z", "query_origem": "tucunare"},
    ]
