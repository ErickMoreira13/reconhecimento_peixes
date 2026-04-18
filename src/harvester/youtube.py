import time
import json
from pathlib import Path
from itertools import cycle
from datetime import datetime, timezone

from src.utils.tempo import agora_iso
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yt_dlp

from src import config
from src.storage import db as storage


# busca na api do youtube usando as keys rotativas
# cada key tem quota de ~10k/dia, entao rotar bastante
# se todas estouraram quota retorna o que ja pegou


def _search_page(query: str, key: str, page_token: str | None = None, published_after: str | None = None) -> dict | None:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": 50,
        "type": "video",
        "key": key,
    }
    if page_token:
        params["pageToken"] = page_token
    if published_after:
        params["publishedAfter"] = published_after

    try:
        r = requests.get(url, params=params, timeout=20)
    except Exception as e:
        print(f"erro na request youtube: {e}")
        return None

    if r.status_code == 200:
        return r.json()

    # 403 geralmente eh quota estourada
    if r.status_code == 403:
        print(f"key {key[:12]}... deve ter estourado quota ({r.status_code})")
        return None

    print(f"resposta estranha da api: {r.status_code} - {r.text[:200]}")
    return None


def busca_videos(query: str, max_videos: int = 50, ultimos_anos: int = 10) -> list[dict]:
    # usa rotacao simples, se uma key falha vai pra proxima
    if not config.YOUTUBE_API_KEYS:
        raise RuntimeError("sem keys configuradas, olha o .env")

    ano_lim = datetime.now(timezone.utc).year - ultimos_anos
    published_after = f"{ano_lim}-01-01T00:00:00Z"

    videos: list[dict] = []
    keys_cycle = cycle(config.YOUTUBE_API_KEYS)
    keys_queimadas: set[str] = set()
    page_token = None

    while len(videos) < max_videos:
        if len(keys_queimadas) == len(config.YOUTUBE_API_KEYS):
            print("todas as keys queimaram, para por aqui")
            break

        key = next(keys_cycle)
        if key in keys_queimadas:
            continue

        data = _search_page(query, key, page_token, published_after)
        if data is None:
            keys_queimadas.add(key)
            continue

        for it in data.get("items", []):
            sn = it["snippet"]
            videos.append({
                "video_id": it["id"]["videoId"],
                "url": f"https://www.youtube.com/watch?v={it['id']['videoId']}",
                "title": sn["title"],
                "channel": sn.get("channelTitle", ""),
                "published_at": sn["publishedAt"],
                "description": sn.get("description", ""),
                "query_origem": query,
            })
            if len(videos) >= max_videos:
                break

        page_token = data.get("nextPageToken")
        if not page_token:
            # acabou as paginas dessa query
            break

    return videos


# baixa so o audio em opus, menor tamanho que whisper aguenta
# outro formato bom eh m4a mas opus da arquivos muito menores


def baixa_audio(url: str, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
            "preferredquality": "32",
        }],
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        # as vezes da ruim em canais com drm ou idade
        print(f"falhou baixar {url}: {e}")
        return None

    vid = info.get("id")
    path = out_dir / f"{vid}.opus"

    if not path.exists():
        # as vezes o ytdlp baixa em outro formato mesmo pedindo opus ?????
        # procura pelo id em qualquer extensao
        achados = list(out_dir.glob(f"{vid}.*"))
        if achados:
            return achados[0]
        print(f"nao achei arquivo baixado pra {vid}")
        return None

    return path


# checkpoint em sqlite pra saber o que ja foi baixado
# reinicio seguro se cair no meio do processamento.
# toda parte de schema/conexao vive em src/storage/db.py, esse modulo so
# usa os helpers


def salva_metadata(videos: list[dict], db_path: Path):
    storage.upsert_videos(videos, db_path)


def pega_pendentes(db_path: Path, limit: int = 100) -> list[dict]:
    return storage.pega_por_status("pendente", limit, ["video_id", "url"], db_path)


def marca_baixado(video_id: str, audio_path: Path, db_path: Path):
    storage.atualiza(video_id, {
        "audio_path": str(audio_path),
        "status": "baixado",
        "baixado_em": agora_iso(),
    }, db_path)


def marca_falhou(video_id: str, db_path: Path):
    storage.atualiza(video_id, {"status": "falhou"}, db_path)


# download em paralelo pq eh i/o bound, ajuda bastante quando tem 500+ videos
# nao da pra compartilhar o mesmo objeto ytdlp entre threads, entao cada thread
# cria o seu proprio - como eh so inicializacao, overhead eh baixo


def baixa_audios_em_paralelo(
    videos: list[dict],
    out_dir: Path,
    workers: int = 4,
) -> list[tuple[dict, Path | None]]:
    # retorna lista de tuplas (video_meta, caminho_audio_ou_None)
    # a ordem NAO eh garantida de ser igual ao input pq usa as_completed
    if not videos:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    resultados: list[tuple[dict, Path | None]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(baixa_audio, v["url"], out_dir): v for v in videos}
        for fut in as_completed(futures):
            v = futures[fut]
            try:
                path = fut.result()
            except Exception as e:
                print(f"thread morreu em {v['video_id']}: {e}")
                path = None
            resultados.append((v, path))

    return resultados
