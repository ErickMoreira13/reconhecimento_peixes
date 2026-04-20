# guia de desenvolvimento

notas pra quem for mexer no codigo desse repo.

## setup de dev

```bash
bash setup.sh                      # bootstrap: venv + deps + modelos
source .venv/bin/activate
pip install -r requirements-dev.txt  # pytest, ruff, pytest-cov
```

## rodar testes

```bash
make tests              # roda pytest completo verbose (~14s, 247 testes)
make test-fast          # sem verbose (pra loop rapido)
make test-cov           # com report de coverage
```

testes usam mocks, nao precisam de ollama/gpu/rede rodando.

testes nao precisam de:
- rede (mocks do requests/yt-dlp)
- gpu (whisper_turbo e gliner_client nao sao testados)
- ollama rodando (qwen_extrator so testa parse e normalizadores)

cobertura real do que da pra testar sem externo: ~60%.

### smoke test contra ollama (opcional)

quando a GPU estiver livre (sem jogo rodando), da pra validar que o
pipeline funciona end-to-end com modelo real:

```bash
# roda extracao em 10 videos e mostra stats de retry schema
.venv/bin/python scripts/testar-retry-schema.py --limit 10

# com offset pra testar subset diferente
.venv/bin/python scripts/testar-retry-schema.py --limit 10 --offset 20
```

gera `docs/teste-retry-schema/_sumario.json` + 1 json por video. ver
`docs/teste-retry-schema/README.md` pros detalhes.

## lint

```bash
make lint
```

usa ruff com config frouxa (so pega bugs obvios: `F` pyflakes + `E9` syntax).
nao forca estilo — comentarios, line length, blank lines ficam como o dev
quer.

## estrutura de teste

```
tests/
  conftest.py              - fixtures globais (db_isolado, videos_exemplo)
  test_schemas.py          - dataclasses CampoExtraido/Veredito
  test_dicts.py            - json dos gazetteers
  test_dicts_conteudo.py   - integridade dos dicts (peixes, ufs, etc)
  test_tempo.py            - utils/tempo.py
  test_storage.py          - src/storage/db.py (sqlite crud)
  test_queries_storage.py  - crud da tabela queries do harvester loop
  test_config.py           - src/config.py (env vars)
  test_ui.py               - src/ui.py (rich wrapper)
  test_ui_banners.py       - banners ASCII do src/ui_banners.py
  test_cuda_libs.py        - whitelist de libs cuda (zero libnvblas!)
  test_parse_json.py       - parse_json_safe casos tipicos
  test_utils_extracao.py   - parse_json_safe edge cases
  test_prompts.py          - monta_prompt_extrator, bm25, retry schema
  test_qwen_extrator.py    - _normaliza_especies, _monta_resultado,
                             chunking, consolidacao
  test_retry_schema.py     - retry de schema errado com budget
  test_regras.py           - regras deterministicas do verificador
                             (inclui ceva_keywords, rio_aparece,
                             blacklist equip, stop-terms, bacias)
  test_retry_loop.py       - loop de retry do critic com mocks
  test_critic.py           - llm critic
  test_benchmark.py        - analisa_suffix com arquivos fake
  test_harvester.py        - youtube api com mocks (sem rede)
  test_harvester_loop.py   - loop perpetuo de coleta
  test_saturacao.py        - detectores de dedup/rejeicao
  test_dashboard.py        - endpoints http com TestClient
  test_gazetteer_check.py  - aplica_flag_fora_do_gazetteer
  test_integracao.py       - integracao entre modulos
  test_cli.py              - src/main.py (cli commands)
  test_gliner_client.py    - gliner com mocks
  test_cuda_libs.py        - whitelist libs nvidia
```

## padroes que o repo segue

### SOLID
cada modulo tem uma responsabilidade (ver docs/ARQUITETURA.md).
harvester nao sabe que existe verificador. storage eh o unico que mexe
com schema do sqlite.

### DRY + SSOT
- schema do sqlite: **so** em `src/storage/db.py`
- timestamps: `src/utils/tempo.py`
- gazetteers: `src/dicts/*.json`
- parse json: `src/extracao/utils.py`

se vc for replicar uma logica mais de 2 vezes, extrai pra modulo.

### KISS
- evita abstracoes que tu vai usar uma vez so
- try/except simples com print, nao hierarquia de excecoes custom
- preferir funcao de 20 linhas a 3 classes pequenas
- logging eh print() em script, nao logger configurado com handler

### vocabulario aberto (regra hard do projeto)
os dicts em `src/dicts/` sao exemplos, nao filtros. se o video menciona
peixe/bacia que nao ta na lista, a gente captura mesmo assim e marca
`fora_do_gazetteer=true`. unica excecao: `estados.json` (27 UFs).

**NUNCA** adicionar `"valor_fora_gazetteer"` ao TipoRejeicao do verificador.
tem teste guardiao em `tests/test_schemas.py::test_tipo_rejeicao_nao_inclui_fora_gazetteer`
que quebra se alguem fizer isso.

## como adicionar um campo novo no resultado

roteiro:

1. adicionar o campo no prompt em `src/extracao/prompts.py::monta_prompt_extrator`
2. adicionar em `src/extracao/qwen_extrator.py::_monta_resultado` (na lista `campos`)
3. adicionar regra especifica em `src/verificador/regras.py` se precisa validar algo
4. adicionar coluna no csv em `src/main.py::cmd_exportar`
5. adicionar teste em `tests/test_qwen_extrator.py`
6. update `docs/ARQUITETURA.md`

## como adicionar um modelo extrator novo

1. `ollama pull <modelo>`
2. `python -m src.main extrair --modelo <modelo> --suffix <nome_curto>`
   (flag --suffix salva em arquivo separado, nao polui o default)
3. rodar benchmark pra comparar:
   `python -m src.benchmark --modelos <antigo> <novo> --limit 50 --so-analise`
4. se melhor, atualizar `.env`:
   `MODEL_EXTRATOR=<novo>`
5. atualizar `docs/benchmark-modelos-*.md`

## controlar verbosidade via env

o codigo usa `src/log.py` pra logs internos (progresso, erros). por default
os logs sao silenciados (level=WARNING). ligue setando `PEIXES_LOG`:

```bash
PEIXES_LOG=info make extrair N=10
PEIXES_LOG=debug make harvester-loop
```

valores aceitos: `debug`, `info`, `warn`, `error`.

prints diretos no terminal (sem logger) continuam visiveis sempre —
sao mensagens user-facing (banners, tabelas, resumos finais).

## cores ANSI nos banners

`src/ascii_art.py` usa cores ANSI (verde pra ok, amarelo pra warn,
vermelho pra erro). se o terminal nao suporta ou voce quer output plain
(ex: pra grepar em log file):

```bash
NO_COLOR=1 make queries
```

a convencao `NO_COLOR` eh padrao de facto pra desligar cores.

## pre-commit hooks

instala os hooks uma vez:

```bash
make install-hooks
```

a partir daí, todo `git commit` roda:

1. **pytest -q** — falha se algum teste quebrou
2. **valida json dos dicts** — pega corrupcao em src/dicts/*.json
3. **ruff check** — pega bugs obvios (F + E9)

se precisar commitar mesmo com hook falhando (raro): `git commit --no-verify`.
melhor consertar o erro antes.

## fixes aplicados 2026-04-19

revisamos 50 videos e aplicamos 8 fixes pros padroes de erro comuns.
lista completa em `docs/fixes-aplicados-2026-04-19.md`. resumo:

- **fix 1**: tipo_ceva exige evidencia literal (prompt + verificador)
- **fix 2**: rio precisa aparecer no texto (verificador)
- **fix 3**: blacklist equipamento em tipo_ceva
- **fix 4**: stop-terms pra especies genericas
- **fix 5**: prompt isca vs especie alvo
- **fix 6**: prompt UF nome -> sigla
- **fix 7**: dicionario 12 bacias BR + validacao + hint
- **fix 8**: chunking com observabilidade + reduz MAX_PALAVRAS 4500->3000

dependendo do fix, mudanca foi no prompt, no verificador, em dict novo,
ou nos tres. testes cobrem todos.

## gotchas conhecidos

- **gliner trunca em 384 tokens**: textos muito longos podem perder info.
  loga warning mas nao divide automaticamente
- **json do llm as vezes quebra**: `src/extracao/utils.parse_json_safe`
  tem fallback pra recuperar {...} de textos com ruido antes/depois
- **ollama cold start**: primeira chamada num modelo demora uns 10s a
  mais pra carregar em vram. normal
- **faster-whisper precisa de cuBLAS/cuDNN**: o `src/transcriber/cuda_libs.py`
  pre-carrega via ctypes. filtra `libnvblas.so` que se carregar causa
  segfault no numpy de todo o app
- **nao pre-carregar TODAS as .so do pacote nvidia-***: tem libnvblas
  junto. use o filtro de whitelist em `cuda_libs._eh_lib_permitida`
- **retry de schema errado**: se o llm cospe campo com tipo errado
  (list/str no lugar de envelope dict), o parse robusto corrige com
  confianca=0. se `corrigidos` nao vazio, dispara 1 retry com feedback.
  budget estrito: max 1 retry por video. telemetria em
  `qwen_extrator.get_stats_retry()`
- **chunking em video grande**: acima de 3000 palavras divide em chunks.
  se TODOS os chunks retornam null, loga `[chunking-bug]` — provavel
  estouro de contexto. ajustar MAX_PALAVRAS_SEM_CHUNKING pra menos
