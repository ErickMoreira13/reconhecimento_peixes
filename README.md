# reconhecimento_peixes

coleta e analise de videos de pescaria brasileira pra montar uma planilha com:
plataforma, autor, link, data, estado, municipio, rio, bacia, tipo de ceva, grao, especies capturadas, observacoes.

roda em maquina pessoal (cpu ou gpu nvidia). usa whisper pra transcrever e modelos locais (ollama) pra extrair as infos do texto.

## setup rapido

clona o repo e roda **uma linha**:

```bash
git clone https://github.com/ErickMoreira13/reconhecimento_peixes
cd reconhecimento_peixes
bash setup.sh
```

o script cuida de tudo: checa pre-requisitos, cria venv, instala deps (base e gpu se der), copia `.env`, baixa modelos ollama.

depois abre o `.env` e poe suas keys do youtube.

## pre-requisitos

- python 3.11+
- ffmpeg (pra yt-dlp extrair audio)
- ollama ([install](https://ollama.com/download))
- gpu nvidia **opcional** (acelera whisper, mas roda em cpu tb)

na duvida roda `bash scripts/check-env.sh` que lista o que ta faltando.

## uso

usa o makefile pra atalho ou chama o python direto.

```bash
# ativa o venv
source .venv/bin/activate

# fluxo padrao (cada etapa depende da anterior)
make buscar Q="pesca com ceva" N=50        # busca na api do youtube
make baixar N=50 W=4                        # yt-dlp baixa o audio (W workers paralelos)
make transcrever N=50                       # whisper turbo
make extrair N=50                           # gliner + qwen (8 campos em 1 chamada)
make verificar N=50                         # regras + llama critic (2 retries)
make exportar                               # gera csv final

# ver como ta
make status
```

ou rodar tudo de uma vez:

```bash
make run-tudo Q="pesca com ceva" N=20
```

o csv final sai em `data/results/planilha_YYYYMMDD_HHMM.csv` com coluna `flags_fora_do_gazetteer` pra ver quais campos vieram de texto livre (nao bateram com dict).

### dashboard web

pra acompanhar o pipeline em tempo real:

```bash
make dashboard       # abre em http://localhost:8000
```

tem cards de status por etapa, barra de progresso geral, tabelas de ultimos processados, e uma secao que mostra os **termos novos** (fora do dict) que foram descobertos — util pra ver que vocabulario novo ta aparecendo nos videos.

### testes

```bash
make tests           # pytest
```

testa o parse de json, regras do verificador, schemas, dicts. nao precisa de rede nem modelo baixado.

## estrutura

```
src/
  config.py              - carrega .env, detecta gpu auto
  schemas.py             - dataclasses comuns (CampoExtraido, Veredito)
  ui.py                  - wrapper do rich (progress, tabelas, cores)
  harvester/youtube.py   - busca api + download via yt-dlp (threadpool)
  transcriber/           - whisper turbo
  extracao/
    gliner_client.py     - ner (spans de peixe e bacia)
    qwen_extrator.py     - qwen 2.5 single-prompt, 8 campos
    prompts.py           - template do prompt, vocabulario aberto
  verificador/
    regras.py            - smith-waterman + cross-field + pos filter
    critic.py            - llama 3.1 8b (familia diferente do qwen)
    retry_loop.py        - budget 2, temp escalation, feedback injection
  dashboard/
    server.py            - fastapi pra monitorar em tempo real
    templates/index.html - pagina com status + termos novos
  dicts/                 - peixes, bacias, estados (EXEMPLOS, nao filtro)
  main.py                - cli

scripts/
  check-env.sh           - valida pre-requisitos
  models.sh              - baixa modelos ollama

tests/                   - pytest (regras, schemas, parse_json, dicts)

data/
  raw_audio/             - .opus 32kbps
  transcriptions/        - json por video
  results/               - json de extracao + csv final
  videos.db              - sqlite com checkpoint do pipeline
```

## modelos usados

- **whisper large-v3-turbo** (2.5gb vram, fp16) - transcricao
- **gliner multi-v2.1** - ner zero-shot (ou fine-tuned se tiver local)
- **qwen 2.5 7b** (q4_k_m, 4.7gb vram) - extrator de 8 campos
- **llama 3.1 8b** (q4_k_m, 4.9gb vram) - verificador (familia diferente pra evitar vies)
- **gemma 3 4b** (q4, 2.6gb vram) - fallback de retry

roda tudo no mesmo ollama em localhost:11434, alternando em memoria no 4060 8gb.

## notas

- os dicts em `src/dicts/` sao **exemplos**, nao lista fechada. se o video menciona peixe/ceva/bacia que nao ta la, a gente captura mesmo assim
- o verificador tem 2 camadas: regras (barato, ~10ms) e llm critic (caro, so se passar regras)
- se rejeitar, re-extrai o campo isolado com temperatura maior e feedback da razao
- todo o pipeline tem checkpoint em sqlite, pode parar e retomar a vontade

## referencias

base inicial veio do tcc antigo do erick (projeto-erick no meu github), mas ficou bem diferente.

- whisper: https://github.com/SYSTRAN/faster-whisper
- gliner: https://github.com/urchade/GLiNER
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- ollama: https://ollama.com
