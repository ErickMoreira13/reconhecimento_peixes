#!/bin/bash
# farm noturno: loop infinito ate ctrl+c.
# missao: maximizar numero de videos TRANSCRITOS
#
# estrategia:
#   1. busca novos videos via harvester loop (rotaciona queries da yaml)
#   2. baixa audio em paralelo (8 workers)
#   3. transcreve com whisper (delete audio apos = economiza disco)
#   4. extrair e verificar fica pra depois (mais lento, usa ollama)
#
# para se:
#   - disco livre < 2GB (protecao)
#   - todas as queries saturadas (harvester sinaliza)
#
# log:
#   docs/noite-farm/run-YYYYMMDD.log
#   docs/noite-farm/progresso.jsonl (1 linha por ciclo)

set -u

ROOT="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$ROOT"

PY=".venv/bin/python"
LOG_DIR="docs/noite-farm"
mkdir -p "$LOG_DIR"

DATA=$(date +%Y%m%d)
LOG="$LOG_DIR/run-$DATA.log"
PROGRESSO="$LOG_DIR/progresso.jsonl"

log() {
    echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"
}

check_disco() {
    # retorna 0 se tem espaco, 1 se tiver menos que 2GB
    local livre_gb
    livre_gb=$(df -BG --output=avail /dados | tail -1 | tr -dc '0-9')
    if [ "$livre_gb" -lt 2 ]; then
        log "DISCO BAIXO: ${livre_gb}GB livres, parando"
        return 1
    fi
    return 0
}

cleanup_audios_orfaos() {
    # audios que ficaram em disco mas nao tem mais correspondencia no db
    # (ex: transcrever falhou, ou pipeline interrompido). deleta.
    $PY -c "
from src.storage import db
from pathlib import Path
with db.conectar() as conn:
    ativos = {r[0] for r in conn.execute('SELECT video_id FROM videos WHERE status=\"baixado\"').fetchall()}
d = Path('data/raw_audio')
n = 0
b = 0
for f in d.iterdir():
    if f.is_file() and f.stem not in ativos:
        b += f.stat().st_size
        f.unlink()
        n += 1
if n:
    print(f'cleanup: {n} audios orfaos ({b/1024/1024:.0f}MB)')
" 2>>"$LOG" || true
}

ciclo() {
    # um ciclo completo do pipeline. retorna 0 sempre (erros tratados internamente)
    local i=$1
    log "=== ciclo $i ==="

    if ! check_disco; then
        return 1
    fi

    # limpa audios que ficaram pra tras entre ciclos anteriores
    cleanup_audios_orfaos

    # 1) busca (rotacao automatica de queries saturada pela lib)
    log "busca: harvester-loop por 5 iteracoes"
    timeout 120 $PY -m src.harvester.loop --max-iter 5 --pausa 3 >>"$LOG" 2>&1 || log "  harvester timeout/falha (segue)"

    # 2) baixa
    # timeout 30min: com yt-dlp rate limitando apos muito uso, 10min nao basta
    # pra baixar 50 videos. se matar no meio, os audios ja baixados nao entram
    # no db (orfaos) e sao deletados no proximo ciclo -- desperdicio total
    log "baixar: limit 50 workers 8"
    timeout 1800 $PY -m src.main baixar --limit 50 --workers 8 >>"$LOG" 2>&1 || log "  baixar falhou"

    # 3) transcreve (delete audio apos)
    # timeout 1h: 50 audios com videos longos (algum de 1h40 no batch) nao cabe
    # em 30min, ai estoura o timeout e perde tudo. 1h geralmente basta
    log "transcrever: limit 50"
    timeout 3600 $PY -m src.main transcrever --limit 50 >>"$LOG" 2>&1 || log "  transcrever timeout"

    # snapshot de progresso
    local contagem
    contagem=$($PY -c "
from src.storage import db
with db.conectar() as conn:
    rows = conn.execute('SELECT status, COUNT(*) FROM videos GROUP BY status').fetchall()
    d = {s:c for s,c in rows}
    import json
    print(json.dumps(d))
" 2>/dev/null)

    echo "{\"ts\":\"$(date -Iseconds)\",\"ciclo\":$i,\"contagem\":$contagem}" >> "$PROGRESSO"
    log "progresso: $contagem"
}

log "############################################################"
log "# farm noturno iniciado ($(date))"
log "############################################################"

i=0
while true; do
    i=$((i + 1))
    ciclo "$i" || {
        log "ciclo $i abortou (disco baixo), saindo"
        break
    }
    log "sleep 30s..."
    sleep 30
done

log "farm noturno terminou depois de $i ciclos"
