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
| smoke 3 (21-30) | 10 | — | — | — | — | — |

conclusao parcial: com llama3.1:8b + prompt atual, a incidencia de
schema errado eh **zero** em producao normal. o retry fica como rede
de seguranca. o caso que motivou o fix original era especifico do
qwen2.5:7b rodando com monkey-patch de labels (via
`scripts/comparar-gliner-labels.py`), nao acontece na rotina.

isso sugere que o parse robusto (camada 1) eh suficiente pra 99%+
dos casos. a camada 2 (retry) eh justificada como defesa pra modelos
menores ou menos capazes — ficar com ela eh barato (zero custo quando
nao dispara) e cobre backdoor de mudancas de modelo no futuro.
