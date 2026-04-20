# changelog

## 2026-04-19 — 8 fixes dos padroes de erro

revisao manual de 50 videos identificou 8 padroes de erro. todos
atacados. detalhes em `docs/fixes-aplicados-2026-04-19.md`.

- [#12](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/12)
  fix 1: tipo_ceva exige evidencia literal no texto
- [#13](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/13)
  fix 2: rio precisa aparecer no texto (corta alucinacao Rio Sao
  Francisco)
- [#14](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/14)
  fix 3: blacklist equipamento em tipo_ceva (vara, carretilha, bait)
- [#15](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/15)
  fix 4: stop-terms pra especies genericas (bonito, paca, cimprao,
  pai tainha)
- [#16](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/16)
  fix 5: prompt distingue isca de especie alvo
- [#17](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/17)
  fix 6: prompt mapeia UF nome -> sigla
- [#18](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/18)
  fix 7: dicionario 12 bacias BR + validacao + hint no prompt
- [#19](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/19)
  fix 8: reduz MAX_PALAVRAS_SEM_CHUNKING pra 3000 (videos grandes
  perdiam todo conteudo)

## 2026-04-19 — retry de schema errado

3 camadas de defesa pra quando llm cospe json com tipo errado:

- parse robusto em `_monta_resultado` (nunca crasha)
- retry 1x com feedback pro llm
- budget estrito, telemetria via `get_stats_retry()`

ver `docs/teste-retry-schema/README.md` com caso real pego em smoke
test.

## 2026-04-19 — rejeicao do gliner 2→4 labels

[#10](https://github.com/ErickMoreira13/reconhecimento_peixes/issues/10)
testado em 50 videos, latencia +261% e cobertura bacia -16pp. revertido
em commit e188759. ver `docs/comparacao-gliner-labels/RESULTADO.md`.

## 2026-04-18 — 8 issues iniciais resolvidas

primeira leva de bugs apos rodada de 51 videos. fechadas #1-#8.
