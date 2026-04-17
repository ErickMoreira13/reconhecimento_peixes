#!/usr/bin/env bash
# script pra checar se a maquina tem tudo que precisa antes de rodar o pipeline
# usa codigo de saida != 0 se faltar algo critico

set -u

ok=0
falha=0
aviso=0

check() {
    local nome="$1"
    local cmd="$2"
    local obrigatorio="${3:-sim}"
    if command -v "$cmd" >/dev/null 2>&1; then
        local ver
        ver=$("$cmd" --version 2>&1 | head -n 1 || echo "?")
        echo "  ok   $nome -> $ver"
        ok=$((ok+1))
    else
        if [ "$obrigatorio" = "sim" ]; then
            echo "  FALHA $nome nao encontrado (obrigatorio)"
            falha=$((falha+1))
        else
            echo "  aviso $nome nao encontrado (opcional)"
            aviso=$((aviso+1))
        fi
    fi
}

echo "checando pre-requisitos do pipeline..."
echo

check "python3" python3
check "pip"    pip3
check "ffmpeg" ffmpeg
check "ollama" ollama
check "git"    git

# gpu eh opcional, so pra acelerar whisper
echo
echo "checando gpu..."
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "  aviso nvidia-smi existe mas nao rodou"
else
    echo "  aviso nvidia-smi nao encontrado -> whisper vai rodar em cpu (mais lento)"
    aviso=$((aviso+1))
fi

# verifica se o ollama ta respondendo
echo
echo "checando servidor ollama..."
if command -v ollama >/dev/null 2>&1; then
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  ok   ollama server ta on em localhost:11434"
        ok=$((ok+1))
    else
        echo "  aviso ollama instalado mas o servico nao ta on, rodar: ollama serve &"
        aviso=$((aviso+1))
    fi
fi

# versao do python
echo
if command -v python3 >/dev/null 2>&1; then
    ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
        echo "  ok   python $ver atende o minimo (3.11+)"
    else
        echo "  FALHA python $ver muito antigo, precisa de 3.11+"
        falha=$((falha+1))
    fi
fi

echo
echo "resumo: $ok ok, $aviso avisos, $falha falhas"

if [ "$falha" -gt 0 ]; then
    echo
    echo "faltou algo obrigatorio, nao da pra rodar o pipeline"
    exit 1
fi
exit 0
