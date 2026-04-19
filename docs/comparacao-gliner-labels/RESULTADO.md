# teste gliner 2 vs 4 labels — rejeitado

rodado em 50 transcricoes, 2026-04-19.

## criterio de sucesso (issue #10)

- latencia >= -20%, OU
- cobertura >= +5pp em rio|municipio sem regressao >= 3pp nos outros

## resultado

| campo | 2lab | 4lab | delta |
|-------|------|------|-------|
| bacia | 11 | 3 | **-8 (-16pp)** |
| especies | 35 | 35 | 0 |
| estado | 2 | 2 | 0 |
| grao | 15 | 17 | +2 |
| municipio | 3 | 6 | +3 |
| observacoes | 34 | 36 | +2 |
| rio | 20 | 22 | +2 |
| tipo_ceva | 29 | 32 | +3 |

**latencia**: 51716ms -> 186776ms (**+261%**)

## o que aconteceu

- nenhum criterio batido. latencia triplicou em vez de cair
- bacia regrediu feio. hipotese: adicionar label `rio` no gliner zero-shot
  fez spans que iam pra bacia virarem rio (overlap semantico forte em pt-br)
- ganhos em municipio/rio/ceva foram marginais (+2-3 cada)
- prefill do llm cresceu pq agora tem 2 listas a mais de candidatos NER

## decisao

revertido em commit `e188759` pra `LABELS_PADRAO = ["peixe", "bacia hidrografica"]`.

## arquivos preservados

- `comparacao.csv` — tabela numerica
- `parciais/2labels/*.json` — 50 extracoes com 2 labels
- `parciais/4labels/*.json` — 50 extracoes com 4 labels
- `run.log` — log completo da execucao
- `run-cancelado-*.log` — log do run anterior interrompido

essas pastas ficam pra referencia mas nao sao source-of-truth pro pipeline.
