import os
import sys
from pathlib import Path

# garante que o src/ ta no path pros testes
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# seta envs fake pra nao precisar de .env real rodando os testes
os.environ.setdefault("YOUTUBE_API_KEYS", "fake_key_1,fake_key_2")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("WHISPER_DEVICE", "cpu")
