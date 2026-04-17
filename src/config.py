import os
from pathlib import Path
from dotenv import load_dotenv

# carrega .env da raiz do projeto
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")


# youtube
YOUTUBE_API_KEYS = [k.strip() for k in os.getenv("YOUTUBE_API_KEYS", "").split(",") if k.strip()]

# ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_EXTRATOR = os.getenv("MODEL_EXTRATOR", "qwen2.5:7b")
MODEL_VERIFICADOR = os.getenv("MODEL_VERIFICADOR", "llama3.1:8b")

# whisper
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
_device_pref = os.getenv("WHISPER_DEVICE", "auto")


def _detecta_device():
    # se o user forcar, respeita
    if _device_pref in ("cuda", "cpu"):
        return _device_pref
    # auto: tenta descobrir se tem gpu disponivel
    # evito importar torch so pra isso, uso nvidia-smi se existir
    import shutil
    import subprocess
    if shutil.which("nvidia-smi"):
        try:
            r = subprocess.run(["nvidia-smi"], capture_output=True, timeout=3)
            if r.returncode == 0:
                return "cuda"
        except Exception:
            pass
    return "cpu"


WHISPER_DEVICE = _detecta_device()

# paths
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
RAW_AUDIO_DIR = DATA_DIR / "raw_audio"
TRANSCR_DIR = DATA_DIR / "transcriptions"
RESULTS_DIR = DATA_DIR / "results"

# cria as pastas se nao existirem
for d in [DATA_DIR, RAW_AUDIO_DIR, TRANSCR_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def checa_keys():
    # util pra debug rapido se as keys tao carregando
    if not YOUTUBE_API_KEYS:
        raise RuntimeError("cade as YOUTUBE_API_KEYS no .env ?????")
    print(f"carregou {len(YOUTUBE_API_KEYS)} keys do youtube")
