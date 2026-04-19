# teste-retry-schema

smoke tests do retry de schema errado no extrator (`src/extracao/qwen_extrator.py`).

## o que tem aqui

- `smoke-NN-videos-X-a-Y.json` — sumario por batch (n videos, elapsed,
  stats do retry, modelo usado)
- `<video_id>.json` — resultado da extracao por video (campos + latencia)
- `run-*.log` — stdout/stderr da execucao

## como rodar

```bash
# primeiros 10 videos
.venv/bin/python scripts/testar-retry-schema.py --limit 10

# videos 11-20 (com offset)
.venv/bin/python scripts/testar-retry-schema.py --limit 10 --offset 10
```

## como ler o sumario

cada `smoke-NN-*.json` tem:

```json
{
  "n": 10,
  "elapsed_s": 141.4,
  "stats_retry": {
    "videos_com_retry": 0,
    "retries_ok": 0,
    "retries_falhos": 0
  },
  "modelo": "llama3.1:8b"
}
```

- **videos_com_retry**: quantos videos tiveram pelo menos 1 campo com schema
  errado, disparando o retry. se >10% do total, sinal de que o prompt base
  precisa de tuning pra reduzir isso de primeira
- **retries_ok**: dos que tentaram retry, quantos vieram com schema certo
  na segunda tentativa
- **retries_falhos**: retry que ainda veio errado. nesse caso, mantemos o
  parse corrigido do 1o try (confianca=0 nos campos errados) em vez de
  tentar 3a vez — budget estrito

## o que eh "schema errado"

qwen/llama as vezes cospe JSON valido mas com campo em formato errado:

```json
// ERRADO: especies direto como lista
"especies": ["tucunare", "pacu"]

// CERTO: especies como envelope com valor/confianca
"especies": {"valor": [{"nome": "tucunare", "evidencia": "..."}], "confianca": 0.9}
```

o extrator tem 3 camadas de defesa:

1. **parse robusto** (`_monta_resultado`): aceita schema errado, converte
   pra envelope com confianca=0. nunca crasha
2. **retry 1x com feedback** (`_extrai_chunk_unico`): se parse corrigiu
   algo, chama llm de novo com prompt especifico explicando o formato
   certo
3. **budget estrito**: max 1 retry por video. se retry falhar, fica com
   parse corrigido — zero risco de loop

## historico de execucoes

| batch | videos | elapsed (s) | s/video | retries | retries_ok | retries_falhos |
|-------|--------|-------------|---------|---------|------------|----------------|
| smoke 1 (1-10) | 10 | 141.4 | 14.1 | 0 | 0 | 0 |
| smoke 2 (11-20) | 10 | 209.2 | 20.9 | 0 | 0 | 0 |
| smoke 3 (21-30) | 10 | 295.7 | 29.6 | 1 | 0 | 1 |

acumulado: 30 videos, 1 retry (3.3%).

### caso real que ativou retry (smoke 3)

video VZ_n0XWOP54 tem 5650 palavras, passou por chunking em 2 pedacos.
o chunk 1 (4494 palavras) veio com o campo `rio` em schema errado.

fluxo:
- parse 1 detectou `corrigidos=['rio']` → disparou retry
- retry chegou com `rio` ainda errado → caiu no fallback (parse corrigido,
  confianca=0 no rio do chunk 1)
- chunk 2 rodou normal, veio com rio em schema certo
- `_consolida_chunks` pegou o valor do chunk 2 (maior confianca)
- resultado final: coerente, sem crash, sem loop

confirmacao em producao real de que as 3 camadas funcionam exatamente
como projetado. camadas de defesa:

1. **parse robusto** pegou o schema errado no chunk 1 sem crashar
2. **retry 1x com feedback** tentou recuperar (nao deu, mas nao
   piorou — ficou no mesmo valor do parse corrigido)
3. **consolidacao de chunks** usou o valor do chunk 2 que veio certo

sem o fix, chunk 1 teria crashado. com o fix, o pipeline se auto-recupera.
