#!/usr/bin/env bash
# bootstrap do projeto - cria venv, instala deps, configura .env
# idempotente: pode re-rodar tranquilo

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# cores (so se o terminal suportar)
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
    C_RESET=$(tput sgr0)
    C_GREEN=$(tput setaf 2)
    C_YELLOW=$(tput setaf 3)
    C_RED=$(tput setaf 1)
    C_CYAN=$(tput setaf 6)
    C_BOLD=$(tput bold)
else
    C_RESET="" C_GREEN="" C_YELLOW="" C_RED="" C_CYAN="" C_BOLD=""
fi

titulo() { echo; echo "${C_BOLD}${C_CYAN}==> $1${C_RESET}"; }
ok()     { echo "${C_GREEN}[ok]${C_RESET} $1"; }
aviso()  { echo "${C_YELLOW}[!]${C_RESET}  $1"; }
erro()   { echo "${C_RED}[X]${C_RESET}  $1"; }

echo "${C_BOLD}${C_CYAN}"
cat <<'EOF'
 reconhecimento_peixes — setup
 ------------------------------
EOF
echo "${C_RESET}"

# 1. check de pre-requisitos
titulo "1/7 checando pre-requisitos"
if ! bash scripts/check-env.sh; then
    erro "faltou coisa, veja acima"
    aviso "ollama: https://ollama.com/download"
    aviso "ffmpeg: sudo apt install ffmpeg (ubuntu/debian)"
    exit 1
fi

# 2. cria venv se nao tem
titulo "2/7 venv python"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "venv criado em .venv/"
else
    ok "ja existe"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# 3. upgrade pip
titulo "3/7 atualizando pip"
pip install -q --upgrade pip
ok "pip atualizado"

# 4. instala requirements base
titulo "4/7 instalando deps base"
pip install -q -r requirements.txt
ok "deps instaladas"

# 5. se tem gpu, instala extras
titulo "5/7 checando gpu pra deps extras"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
    ok "gpu detectada: $gpu_name"
    pip install -q -r requirements-gpu.txt
    ok "onnxruntime-gpu instalado"
else
    aviso "sem gpu nvidia, pulando deps gpu (tudo bem, roda em cpu)"
fi

# 6. cria .env se nao tem
titulo "6/7 configurando .env"
if [ ! -f ".env" ]; then
    cp .env.example .env
    ok ".env criado a partir do exemplo"
    aviso "edita o .env e poe suas keys do youtube antes de rodar 'buscar'"
else
    ok ".env ja existe"
fi

# pastas de dados
mkdir -p data/raw_audio data/transcriptions data/results

# 7. baixa modelos ollama
titulo "7/7 modelos ollama"
echo "vai baixar ~12gb de modelos (qwen, llama, gemma fallback)"
read -rp "baixar agora? [S/n] " baixar
if [ -z "$baixar" ] || [ "$baixar" = "s" ] || [ "$baixar" = "S" ]; then
    bash scripts/models.sh
else
    aviso "quando quiser rodar: bash scripts/models.sh (ou: make models)"
fi

# resumo final bonito
echo
echo "${C_BOLD}${C_GREEN}"
cat <<'EOF'
 setup terminou!
 ------------------------------
EOF
echo "${C_RESET}"

cat <<EOF
proximo passo (copia e cola):

  ${C_CYAN}source .venv/bin/activate${C_RESET}
  ${C_CYAN}make status${C_RESET}                 # ver status do pipeline
  ${C_CYAN}make buscar Q="pesca com ceva" N=10${C_RESET}
  ${C_CYAN}make baixar N=10${C_RESET}
  ${C_CYAN}make transcrever N=10${C_RESET}
  ${C_CYAN}make extrair N=10${C_RESET}
  ${C_CYAN}make verificar N=10${C_RESET}
  ${C_CYAN}make exportar${C_RESET}

ou tudo de uma vez com poucos videos pra testar:

  ${C_CYAN}make run-tudo Q="pesca com ceva" N=5${C_RESET}

pra abrir o dashboard web com progresso em tempo real:

  ${C_CYAN}make dashboard${C_RESET}          # abre em http://localhost:8000

EOF
