import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src import config


# ponto unico que mexe com o schema do sqlite
# em vez de ficar espalhando ALTER TABLE nos modulos (que era o que tava fazendo
# antes), centraliza tudo aqui. schema declarado no topo, cria idempotente.


DB_PATH = config.DATA_DIR / "videos.db"


SCHEMA_INICIAL = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    channel TEXT,
    published_at TEXT,
    query_origem TEXT,
    audio_path TEXT,
    transcricao_path TEXT,
    resultado_path TEXT,
    status TEXT DEFAULT 'pendente',
    baixado_em TEXT,
    transcrito_em TEXT,
    extraido_em TEXT,
    verificado_em TEXT
);

CREATE TABLE IF NOT EXISTS queries (
    texto TEXT PRIMARY KEY,
    status TEXT DEFAULT 'ativa',
    total_buscados INTEGER DEFAULT 0,
    total_novos INTEGER DEFAULT 0,
    dedup_rate_ultima REAL DEFAULT 0.0,
    rejeicao_rate_ultima REAL DEFAULT 0.0,
    criado_em TEXT,
    atualizado_em TEXT,
    motivo_saturacao TEXT
);
"""


# colunas que podem precisar ser adicionadas em db antigo (pre-schema unificado)
# lista todas pra facilitar upgrade sem perder dado
COLUNAS_OPCIONAIS = [
    ("transcricao_path", "TEXT"),
    ("resultado_path", "TEXT"),
    ("transcrito_em", "TEXT"),
    ("extraido_em", "TEXT"),
    ("verificado_em", "TEXT"),
    ("baixado_em", "TEXT"),
    ("query_origem", "TEXT"),
]


def _ensure_schema(conn: sqlite3.Connection):
    # executescript pra rodar os 2 CREATE TABLE de uma vez
    conn.executescript(SCHEMA_INICIAL)
    # garante que db antigo tenha todas as colunas
    for nome, tipo in COLUNAS_OPCIONAIS:
        try:
            conn.execute(f"ALTER TABLE videos ADD COLUMN {nome} {tipo}")
        except sqlite3.OperationalError:
            # ja existe, tranquilo
            pass
    conn.commit()


@contextmanager
def conectar(db_path: Path | None = None):
    # context manager padrao pra usar no resto do codigo
    # garante commit/close + schema ok
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        _ensure_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def contagem_por_status(db_path: Path | None = None) -> list[tuple[str, int]]:
    # util usado pelo comando status e pelo dashboard
    with conectar(db_path) as conn:
        rows = conn.execute("SELECT status, COUNT(*) FROM videos GROUP BY status").fetchall()
    return rows


def upsert_videos(videos: list[dict], db_path: Path | None = None):
    # insere videos novos (ignora duplicatas por video_id)
    with conectar(db_path) as conn:
        for v in videos:
            conn.execute("""
                INSERT OR IGNORE INTO videos (video_id, url, title, channel, published_at, query_origem)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                v["video_id"], v["url"], v["title"], v["channel"],
                v["published_at"], v.get("query_origem", ""),
            ))


def pega_por_status(status: str, limit: int, colunas: list[str], db_path: Path | None = None) -> list[dict]:
    # select flexivel. evita replicar query simples em todo lugar
    cols = ", ".join(colunas)
    with conectar(db_path) as conn:
        rows = conn.execute(
            f"SELECT {cols} FROM videos WHERE status = ? LIMIT ?",
            (status, limit),
        ).fetchall()
    return [dict(zip(colunas, r)) for r in rows]


def atualiza(video_id: str, campos: dict, db_path: Path | None = None):
    # update flexivel. ex: atualiza('abc', {'status': 'baixado', 'audio_path': '...'})
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [video_id]
    with conectar(db_path) as conn:
        conn.execute(f"UPDATE videos SET {sets} WHERE video_id = ?", vals)


def reconcilia_status(results_dir: Path, db_path: Path | None = None) -> dict:
    # fix pra videos orfaos: a gente pode ter um video em status='transcrito'
    # mas com arquivo <vid>_extracao.json existente (extracao rodou mas nao
    # marcou o db direito). ou vice-versa: status='extraido' mas sem arquivo.
    #
    # roda esse metodo antes de comecar uma nova etapa pra limpar inconsistencias
    mudancas = {"marcados_extraido": 0, "voltados_transcrito": 0}

    with conectar(db_path) as conn:
        # caso 1: arquivo de extracao existe mas status != extraido/verificado
        rows = conn.execute("""
            SELECT video_id, status FROM videos
            WHERE status IN ('transcrito', 'baixado')
        """).fetchall()
        for vid, st in rows:
            p = results_dir / f"{vid}_extracao.json"
            if p.exists():
                conn.execute(
                    "UPDATE videos SET status='extraido', resultado_path=? WHERE video_id=?",
                    (str(p), vid),
                )
                mudancas["marcados_extraido"] += 1

        # caso 2: status extraido/verificado mas arquivo sumiu
        rows = conn.execute("""
            SELECT video_id, resultado_path FROM videos
            WHERE status IN ('extraido', 'verificado')
        """).fetchall()
        for vid, rp in rows:
            if not rp or not Path(rp).exists():
                conn.execute(
                    "UPDATE videos SET status='transcrito', resultado_path=NULL WHERE video_id=?",
                    (vid,),
                )
                mudancas["voltados_transcrito"] += 1

    return mudancas
