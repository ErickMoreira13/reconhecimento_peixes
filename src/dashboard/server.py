import json
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src import config


# dashboard simples pra ver o pipeline rodando em tempo real
# nao tem websocket nem nada sofisticado, so polling via fetch no cliente
# uma pagina html, 1 endpoint de json, 1 endpoint de ultimos resultados


app = FastAPI(title="reconhecimento_peixes dashboard", docs_url=None, redoc_url=None)


DB_PATH = config.DATA_DIR / "videos.db"

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=HTMLResponse)
def index():
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/status")
def api_status():
    # contagem por status + totais + tempos
    if not DB_PATH.exists():
        return JSONResponse({"erro": "db ainda nao existe, rode buscar primeiro"}, status_code=404)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # contagem por status
    cur.execute("SELECT status, COUNT(*) FROM videos GROUP BY status")
    por_status = {r[0]: r[1] for r in cur.fetchall()}

    # ultimos baixados/transcritos/extraidos
    cur.execute("SELECT video_id, title, baixado_em FROM videos WHERE baixado_em IS NOT NULL ORDER BY baixado_em DESC LIMIT 5")
    ultimos_baixados = [{"video_id": r[0], "title": r[1], "quando": r[2]} for r in cur.fetchall()]

    cur.execute("SELECT video_id, title, transcrito_em FROM videos WHERE transcrito_em IS NOT NULL ORDER BY transcrito_em DESC LIMIT 5")
    ultimos_transcritos = [{"video_id": r[0], "title": r[1], "quando": r[2]} for r in cur.fetchall()]

    cur.execute("SELECT video_id, title, extraido_em FROM videos WHERE extraido_em IS NOT NULL ORDER BY extraido_em DESC LIMIT 5")
    ultimos_extraidos = [{"video_id": r[0], "title": r[1], "quando": r[2]} for r in cur.fetchall()]

    total = sum(por_status.values())

    conn.close()

    return {
        "por_status": por_status,
        "total": total,
        "ultimos_baixados": ultimos_baixados,
        "ultimos_transcritos": ultimos_transcritos,
        "ultimos_extraidos": ultimos_extraidos,
        "atualizado_em": datetime.utcnow().isoformat(),
    }


@app.get("/api/resultado/{video_id}")
def api_resultado(video_id: str):
    # pega o json completo da extracao pra um video
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT resultado_path FROM videos WHERE video_id = ?", (video_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return JSONResponse({"erro": "nao tem resultado pra esse video ainda"}, status_code=404)

    p = Path(row[0])
    if not p.exists():
        return JSONResponse({"erro": "arquivo sumiu"}, status_code=404)

    with open(p, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/flags")
def api_flags_fora_do_gazetteer():
    # util pra ver quais termos novos apareceram
    # retorna valores extraidos que nao bateram com o dict
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT video_id, resultado_path FROM videos
        WHERE resultado_path IS NOT NULL
    """)
    rows = cur.fetchall()
    conn.close()

    termos_novos: dict[str, list[dict]] = {}
    for video_id, rp in rows:
        if not rp:
            continue
        p = Path(rp)
        if not p.exists():
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue

        for campo_nome, campo in d.get("campos", {}).items():
            if not campo.get("fora_do_gazetteer"):
                continue
            valor = campo.get("valor")
            if not valor:
                continue
            termos_novos.setdefault(campo_nome, []).append({
                "video_id": video_id,
                "valor": valor,
                "evidencia": campo.get("evidencia", ""),
            })

    return termos_novos
