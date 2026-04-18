import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from src.storage import db as storage
from src.utils.tempo import agora_iso


# dashboard simples pra ver o pipeline rodando em tempo real
# nao tem websocket nem nada sofisticado, so polling via fetch no cliente
# uma pagina html, 1 endpoint de json, 1 endpoint de ultimos resultados


app = FastAPI(title="reconhecimento_peixes dashboard", docs_url=None, redoc_url=None)


DB_PATH = storage.DB_PATH
TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=HTMLResponse)
def index():
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


def _ultimos_por_etapa(conn, coluna_quando: str, limit: int = 5) -> list[dict]:
    # helper pra nao repetir a mesma query 3 vezes com coluna diferente
    rows = conn.execute(
        f"SELECT video_id, title, {coluna_quando} FROM videos "
        f"WHERE {coluna_quando} IS NOT NULL ORDER BY {coluna_quando} DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"video_id": r[0], "title": r[1], "quando": r[2]} for r in rows]


@app.get("/api/status")
def api_status():
    if not DB_PATH.exists():
        return JSONResponse({"erro": "db ainda nao existe, rode buscar primeiro"}, status_code=404)

    with storage.conectar() as conn:
        por_status = {r[0]: r[1] for r in conn.execute("SELECT status, COUNT(*) FROM videos GROUP BY status")}
        ultimos_baixados = _ultimos_por_etapa(conn, "baixado_em")
        ultimos_transcritos = _ultimos_por_etapa(conn, "transcrito_em")
        ultimos_extraidos = _ultimos_por_etapa(conn, "extraido_em")

    return {
        "por_status": por_status,
        "total": sum(por_status.values()),
        "ultimos_baixados": ultimos_baixados,
        "ultimos_transcritos": ultimos_transcritos,
        "ultimos_extraidos": ultimos_extraidos,
        "atualizado_em": agora_iso(),
    }


@app.get("/api/resultado/{video_id}")
def api_resultado(video_id: str):
    # pega o json completo da extracao pra um video
    with storage.conectar() as conn:
        row = conn.execute("SELECT resultado_path FROM videos WHERE video_id = ?", (video_id,)).fetchone()

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
    with storage.conectar() as conn:
        rows = conn.execute(
            "SELECT video_id, resultado_path FROM videos WHERE resultado_path IS NOT NULL"
        ).fetchall()

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
