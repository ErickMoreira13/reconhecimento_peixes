# arquitetura do pipeline

essa doc eh pra quem for mexer no codigo entender o que cada peca faz e
como elas se encaixam. se ta procurando como USAR, ver README.md da raiz.

## visao geral

```
youtube api  ->  harvester  ->  transcriber  ->  extracao  ->  verificador  ->  exportar
    +                            (whisper)       (gliner +   (regras + llm        (csv)
  yt-dlp                                          llm)         critic)
```

cada estagio pode ser chamado isolado pela cli (`python -m src.main <cmd>`)
e mantem estado em `data/videos.db` (sqlite). se cair no meio, retoma de onde
parou olhando o campo `status` do video.

## estados do video

enum pelo campo `status` da tabela videos:

```
pendente    -> acabou de ser achado pelo harvester, ainda nao baixou o audio
baixado     -> audio em data/raw_audio/<id>.opus, pronto pra transcrever
transcrito  -> texto em data/transcriptions/<id>.json, pronto pra extrair
extraido    -> campos em data/results/<id>_extracao.json, pronto pra verificar
verificado  -> campos revisados pelo critic, pronto pra exportar
falhou      -> download/transcricao quebrou, skipa no resto do pipeline
```

## modulos e responsabilidades (SRP)

| modulo              | o que faz                                               |
|---------------------|---------------------------------------------------------|
| `src/config.py`     | carrega .env, detecta gpu, paths                        |
| `src/schemas.py`    | dataclasses compartilhadas (CampoExtraido, Veredito)    |
| `src/ui.py`         | wrapper do rich (progress, tabelas, cores)              |
| `src/utils/tempo.py` | timestamps iso                                         |
| `src/storage/db.py` | schema sqlite + crud (ssot do banco)                    |
| `src/harvester/`    | busca youtube + download audio via yt-dlp               |
| `src/transcriber/`  | faster-whisper + preload das libs cuda                  |
| `src/extracao/`     | gliner ner + qwen/llm single-prompt                     |
| `src/verificador/`  | regras deterministicas + llm critic + retry loop        |
| `src/dashboard/`    | fastapi pra monitorar em tempo real                     |
| `src/benchmark.py`  | compara varios extratores no mesmo dataset              |
| `src/main.py`       | cli, orquestra tudo                                     |

modulos nao sao acoplados: cada um so depende dos que estao a ESQUERDA na
tabela acima (pra cima no pipeline). ex: extracao nao sabe que existe
verificador.

## fluxo de dados

```
youtube api v3 --[metadata]--> videos.db (pendente)
videos.db (pendente) --[url]--> yt-dlp --[opus]--> data/raw_audio/
data/raw_audio/*.opus --[cuda]--> faster-whisper --[texto+segments]--> data/transcriptions/*.json
data/transcriptions/*.json --[texto]--> gliner --[spans peixe/bacia]--+
                                                                     |
                                  src/dicts/*.json --[hints]---------+
                                                                     v
                                              qwen (single-prompt) --[8 campos]--> data/results/<id>_extracao.json
data/results/<id>_extracao.json --[8 campos]--> regras + llama 3.1 critic --[vereditos]--> data/results/<id>_extracao.json (campo verificado=true)
data/results/*.json --[agrega]--> data/results/planilha_<ts>.csv
```

## vocabulario aberto (regra central)

isso esta espalhado no codigo mas aqui fica explicito: os arquivos em
`src/dicts/` sao EXEMPLOS e HINTS, nao filtros fechados.

- se o video menciona peixe/bacia/rio/ceva/grao **que nao esta no dict**,
  a gente captura mesmo assim e marca `fora_do_gazetteer: true`
- o verificador NAO rejeita por "valor fora do gazetteer"
- unica excecao eh `estados.json` (27 UFs eh enum fechado de verdade)

isso eh pra descobrir vocabulario novo ao longo da coleta.

## escolha de modelos (em 2026-04-18)

| funcao      | modelo                | por que                                        |
|-------------|-----------------------|------------------------------------------------|
| asr         | whisper large-v3-turbo | wer 1.9% (libre speech), 30x rt no rtx 4060    |
| ner         | gliner multi-v2.1     | zero-shot razoavel pra peixe/bacia em pt-br    |
| extrator    | llama 3.1 8b Q4       | maior cobertura (ver docs/benchmark-modelos-2026-04-18.md) |
| verificador | qwen 2.5 7b Q4        | conservador, familia diferente do llama        |
| fallback    | gemma 3 4b Q4         | pra 3a tentativa de retry, vies diferente      |

todos os llms rodam em ollama local. nao sai dado pra fora.

## retry do verificador

```
regras deterministicas (smith-waterman, pos, cross-field, length)
       |
       v
     passa?
    /     \
  sim     nao
   |       |
   |       v
   |    retry extracao com temp maior + feedback da razao
   |       |
   v       v
llm critic (llama 3.1 8b)
   |
   v
 passa?
/    \
sim  nao
 |    |
 v    v
ok   retry extracao (budget=1 antes de desistir)
```

retry budget eh estrito: 1 retentativa max. passa ou vira null+flag.

## sqlite schema (ssot em src/storage/db.py)

```sql
CREATE TABLE videos (
    video_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    channel TEXT,
    published_at TEXT,
    query_origem TEXT,
    audio_path TEXT,
    transcricao_path TEXT,
    resultado_path TEXT,
    status TEXT DEFAULT 'pendente',
    baixado_em TEXT,
    transcrito_em TEXT,
    extraido_em TEXT,
    verificado_em TEXT
);
```

nao mexe no schema em outros arquivos. se precisar de coluna nova, adicionar
em `SCHEMA_INICIAL` + `COLUNAS_OPCIONAIS` do `src/storage/db.py`.

## tradeoffs conhecidos

- gliner tem limite de 384 tokens, vai truncar texto longo. loga warning
  mas nao divide automaticamente
- qwen/llama as vezes cospem json quebrado apesar do `format="json"`.
  tem retry com temp maior em `src/extracao/utils.parse_json_safe`
- whisper demora ~1/30 do tempo de audio. 500 videos de 10min = 2.8h de asr
- single-prompt do extrator limita contexto a 8192 tokens, videos muito
  longos podem perder informacao do final
