from datetime import datetime, timezone


# helper pra timestamps. centraliza num lugar pra nao ficar escolhendo
# entre datetime.utcnow() (deprecated no 3.12) e datetime.now(tz=UTC) em
# cada arquivo. tambem padroniza o formato.


def agora_iso() -> str:
    # iso8601 com timezone, aware. substitui datetime.utcnow().isoformat()
    return datetime.now(timezone.utc).isoformat()


def agora_compact() -> str:
    # formato pra nomes de arquivo: 20260418_0333
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
