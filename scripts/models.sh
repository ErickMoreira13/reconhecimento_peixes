#!/usr/bin/env bash
# baixa os modelos ollama que o pipeline usa
# pode re-rodar a vontade, se ja tem ele pula

set -e

if ! command -v ollama >/dev/null 2>&1; then
    echo "ollama nao instalado, ver em https://ollama.com"
    exit 1
fi

# sobe o servico se nao ta rodando ainda
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "ollama server nao ta respondendo, tentando subir em background..."
    nohup ollama serve >/tmp/ollama.log 2>&1 &
    sleep 3
fi

echo "baixando modelos (pode demorar, ~12gb no total)..."

# extrator principal - qwen 2.5 7b, melhor pt-br no tamanho
echo
echo ">> qwen2.5:7b (extrator)"
ollama pull qwen2.5:7b

# verificador - familia diferente pra evitar vies circular
echo
echo ">> llama3.1:8b (verificador)"
ollama pull llama3.1:8b

# fallback do retry loop
echo
echo ">> gemma3:4b (fallback de retry)"
ollama pull gemma3:4b

echo
echo "modelos prontos:"
ollama list | grep -E "^(qwen2.5|llama3.1|gemma3):" || true

echo
echo "tudo ok, bora rodar o pipeline"
