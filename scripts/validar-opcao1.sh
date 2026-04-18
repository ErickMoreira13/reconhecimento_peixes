#!/usr/bin/env bash
# valida a config invertida (llama extrator + qwen verificador) no pipeline
# completo contra os 52 videos ja transcritos.
#
# nao precisa re-buscar nem re-transcrever. so extrair -> verificar -> exportar.
# depois roda a analise e salva tudo em docs/ pra comparar com o baseline.
#
# tempo esperado: ~1h (extracao ~20min + verificar ~40min + analise).
# pode rodar tranquilo a noite, usa a gpu mas nao trava maquina.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
cd "$ROOT_DIR"

# shellcheck disable=SC1091
source .venv/bin/activate

DATA=$(date +%Y-%m-%d_%H%M)
OUT_DIR="docs/validacao-opcao1-$DATA"
mkdir -p "$OUT_DIR"

echo "=== validacao opcao 1: llama-extrator + qwen-verificador ==="
echo "saida: $OUT_DIR"
echo

# confere o .env ta com a config certa
if ! grep -q "^MODEL_EXTRATOR=llama3.1:8b" .env; then
    echo "ERRO: .env nao ta com llama como extrator"
    echo "rode: sed -i 's/^MODEL_EXTRATOR=.*/MODEL_EXTRATOR=llama3.1:8b/' .env"
    exit 1
fi
if ! grep -q "^MODEL_VERIFICADOR=qwen2.5:7b" .env; then
    echo "ERRO: .env nao ta com qwen como verificador"
    echo "rode: sed -i 's/^MODEL_VERIFICADOR=.*/MODEL_VERIFICADOR=qwen2.5:7b/' .env"
    exit 1
fi

echo "[1/5] resetando status dos videos no db (marca todos como 'transcrito')"
python -c "
import sqlite3
conn = sqlite3.connect('data/videos.db')
# volta tudo pra transcrito pra re-rodar extrair/verificar com a config nova
for col in ['resultado_path', 'extraido_em', 'verificado_em']:
    try: conn.execute(f'UPDATE videos SET {col} = NULL')
    except sqlite3.OperationalError: pass
conn.execute(\"UPDATE videos SET status = 'transcrito' WHERE status IN ('extraido', 'verificado')\")
conn.commit()
n = conn.execute(\"SELECT COUNT(*) FROM videos WHERE status='transcrito'\").fetchone()[0]
print(f'  {n} videos prontos pra reextrair')
conn.close()
"

echo
echo "[2/5] limpando extracoes antigas (mantem os *_extracao_qwen2.5_7b.json etc do benchmark)"
# so apaga os _extracao.json sem suffix (que eh o default que vai ser regerado)
find data/results -name "*_extracao.json" -delete 2>/dev/null || true

echo
echo "[3/5] extraindo com llama 3.1 8b (default agora)..."
time python -m src.main extrair --limit 60 2>&1 | tail -5

echo
echo "[4/5] verificando com qwen 2.5 7b (default agora)..."
time python -m src.main verificar --limit 60 2>&1 | tail -5

echo
echo "[5/5] exportando csv e rodando analise..."
python -m src.main exportar 2>&1 | tail -2

# copia o csv pra docs/ pra guardar junto do relatorio
CSV_GERADO=$(ls -t data/results/planilha_*.csv 2>/dev/null | head -1)
if [ -n "$CSV_GERADO" ]; then
    cp "$CSV_GERADO" "$OUT_DIR/planilha.csv"
    echo "  planilha copiada pra $OUT_DIR/planilha.csv"
fi

# gera resumo da opcao 1 (metricas do verificador: quantos rejeitados, etc)
python -c "
import json
from pathlib import Path

results = Path('data/results')
stats = {
    'total_extraidos': 0,
    'total_verificados': 0,
    'rejeitados_por_campo': {},
    'tipos_rejeicao': {},
    'campos_preenchidos': {},
    'termos_fora_gazetteer': {},
}

# pega os _extracao.json sem suffix (resultado da nova config)
for p in results.glob('*_extracao.json'):
    stats['total_extraidos'] += 1
    d = json.loads(p.read_text(encoding='utf-8'))
    if d.get('verificado'):
        stats['total_verificados'] += 1
    for nome, c in d.get('campos', {}).items():
        if c.get('valor') not in (None, '', []):
            stats['campos_preenchidos'][nome] = stats['campos_preenchidos'].get(nome, 0) + 1
        if c.get('fora_do_gazetteer'):
            stats['termos_fora_gazetteer'][nome] = stats['termos_fora_gazetteer'].get(nome, 0) + 1
    for nome, v in d.get('vereditos', {}).items():
        if not v.get('aceito'):
            stats['rejeitados_por_campo'][nome] = stats['rejeitados_por_campo'].get(nome, 0) + 1
            tp = v.get('tipo_rejeicao') or 'outro'
            stats['tipos_rejeicao'][tp] = stats['tipos_rejeicao'].get(tp, 0) + 1

import json as _json
out = Path('$OUT_DIR') / 'stats.json'
out.write_text(_json.dumps(stats, ensure_ascii=False, indent=2))
print(f'  stats em $OUT_DIR/stats.json')
print(f'  total extraidos: {stats[\"total_extraidos\"]}')
print(f'  total verificados: {stats[\"total_verificados\"]}')
print(f'  rejeitados por campo: {stats[\"rejeitados_por_campo\"]}')
"

echo
echo "=== validacao terminou ==="
echo
echo "arquivos em $OUT_DIR:"
ls -la "$OUT_DIR"
echo
echo "compara com o baseline em docs/benchmark-modelos-2026-04-18.csv"
