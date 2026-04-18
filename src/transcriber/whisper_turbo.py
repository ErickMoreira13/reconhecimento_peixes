import json
from pathlib import Path
from datetime import datetime

# importa antes do faster-whisper pra garantir que as libs cuda estao visiveis
from src.transcriber.cuda_libs import pre_carrega_libs_cuda
pre_carrega_libs_cuda()

from faster_whisper import WhisperModel

from src import config
from src.storage import db as storage


# carrega o whisper uma vez so e reusa pra todos os videos
# large-v3-turbo eh ~2x mais rapido que large-v3 com wer parecida
_modelo: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _modelo
    if _modelo is None:
        print(f"carregando whisper {config.WHISPER_MODEL} em {config.WHISPER_DEVICE}...")
        _modelo = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type="float16" if config.WHISPER_DEVICE == "cuda" else "int8",
        )
    return _modelo


def transcreve(audio_path: Path) -> dict:
    # language=pt forca pt, se deixar auto as vezes detecta es em sotaque ribeirinho
    # vad_filter corta silencio, ajuda bastante em video longo com pausas
    m = _get_model()

    segs_iter, info = m.transcribe(
        str(audio_path),
        language="pt",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=False,  # nao precisa por enquanto, economiza tempo
    )

    segmentos = []
    texto_completo = []
    for s in segs_iter:
        segmentos.append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
        })
        texto_completo.append(s.text.strip())

    return {
        "texto": " ".join(texto_completo),
        "segmentos": segmentos,
        "duracao_seg": round(info.duration, 2),
        "idioma_detectado": info.language,
    }


def salva_transcricao(video_id: str, resultado: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{video_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    return path


# atualiza o status do video no banco depois que transcreveu
# mesmo banco do harvester. schema mora em src/storage/db.py


def marca_transcrito(video_id: str, transcricao_path: Path, db_path: Path):
    storage.atualiza(video_id, {
        "transcricao_path": str(transcricao_path),
        "status": "transcrito",
        "transcrito_em": datetime.utcnow().isoformat(),
    }, db_path)


def pega_pra_transcrever(db_path: Path, limit: int = 100) -> list[dict]:
    return storage.pega_por_status("baixado", limit, ["video_id", "audio_path"], db_path)
