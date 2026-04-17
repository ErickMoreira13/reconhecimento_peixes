#!/usr/bin/env bash
# bootstrap do projeto - cria venv, instala deps, configura .env
# idempotente: pode re-rodar tranquilo

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== setup do reconhecimento_peixes ==="
echo

# 1. check de pre-requisitos
echo "1. checando pre-requisitos..."
bash scripts/check-env.sh || {
    echo
    echo "falta coisa, veja acima. se faltou ollama: https://ollama.com/download"
    echo "se faltou ffmpeg: sudo apt install ffmpeg (ubuntu) ou equivalente"
    exit 1
}

# 2. cria venv se nao tem
echo
echo "2. criando venv..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  venv criado em .venv/"
else
    echo "  ja existe, ok"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# 3. upgrade pip
echo
echo "3. atualizando pip..."
pip install -q --upgrade pip

# 4. instala requirements base
echo
echo "4. instalando deps base..."
pip install -q -r requirements.txt

# 5. se tem gpu, instala extras
echo
echo "5. checando gpu pra deps extras..."
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    echo "  gpu detectada, instalando onnxruntime-gpu..."
    pip install -q -r requirements-gpu.txt
else
    echo "  sem gpu, pulando deps gpu (tudo bem, roda em cpu)"
fi

# 6. cria .env se nao tem
echo
echo "6. configurando .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  criado .env a partir do exemplo"
    echo "  IMPORTANTE: edita o .env e poe suas keys do youtube antes de rodar 'buscar'"
else
    echo "  ja existe, ok"
fi

# 7. cria pastas de dados
echo
echo "7. criando pastas de dados..."
mkdir -p data/raw_audio data/transcriptions data/results

# 8. baixa modelos ollama (pode demorar)
echo
echo "8. baixar modelos ollama? (precisa de ~12gb de disco)"
read -rp "   [s/n] " baixar
if [ "$baixar" = "s" ] || [ "$baixar" = "S" ] || [ -z "$baixar" ]; then
    bash scripts/models.sh
else
    echo "  pulei. quando quiser: bash scripts/models.sh"
fi

echo
echo "=== setup terminou ==="
echo
echo "proximo passo:"
echo "  source .venv/bin/activate"
echo "  python -m src.main status"
echo
echo "ou use os atalhos do Makefile:"
echo "  make status"
echo "  make buscar"
echo "  make baixar"
