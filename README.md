# reconhecimento_peixes

coleta e analise de videos de pescaria brasileira pra montar uma planilha com:
plataforma, autor, link, data, estado, municipio, rio, bacia, tipo de ceva, grao, especies capturadas, observacoes.

roda em maquina pessoal, sem cloud. usa whisper pra transcrever e modelos locais (ollama) pra extrair as infos do texto.

## setup

precisa de: python 3.11+, ffmpeg, ollama (com qwen2.5:7b e llama3.1:8b baixados), cuda (opcional mas recomendado pra whisper).

```bash
# deps python
pip install -r requirements.txt

# config
cp .env.example .env
# edita .env e poe suas keys do youtube

# modelos ollama (se ainda nao tiver)
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```

## uso basico

```bash
# 1. busca videos no youtube (salva metadata no db)
python -m src.main buscar --queries "pesca com ceva" --max-por-query 50

# 2. baixa audio dos pendentes
python -m src.main baixar --limit 50

# 3. transcreve os audios
python -m src.main transcrever --limit 50

# ver status
python -m src.main status
```

os audios vao pra `data/raw_audio/`, transcricoes pra `data/transcriptions/`, e o estado do pipeline fica em `data/videos.db`.

## estrutura

```
src/
  config.py              # carrega .env
  harvester/youtube.py   # busca + download via yt-dlp
  transcriber/           # whisper turbo
  extracao/              # gliner + qwen (a fazer)
  verificador/           # regras + llm critic (a fazer)
  dicts/                 # peixes, bacias, estados, cevas, graos
  main.py
data/
  raw_audio/
  transcriptions/
  results/
```

## referencias

- base inicial veio do tcc antigo do erick (projeto-erick no meu github)
- whisper: https://github.com/SYSTRAN/faster-whisper
- gliner: https://github.com/urchade/GLiNER
- yt-dlp: https://github.com/yt-dlp/yt-dlp
