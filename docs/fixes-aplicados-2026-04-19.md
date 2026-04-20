# fixes aplicados 2026-04-19

consolidacao dos 8 fixes feitos em resposta ao sumario das anotacoes
manuais (`docs/anotacoes-manuais/sumario.md`).

## contexto

revisei manualmente os 50 videos em 5 lotes. identifiquei 8 padroes
de erro. fix por fix:

## fix 1: tipo_ceva exige evidencia literal

- **problema**: 50% dos videos tinham tipo_ceva errado (ceva_solta_na_agua
  como default quando nao havia ceva)
- **solucao**:
  - prompt: exige texto mencionar ceva/seva/ceba/cevar/cevador
  - verificador: regra `_passa_ceva_keywords` rejeita se nao bater
- **commits**: `18c5dd7`, `e2b1ace`, `e9ce6dd`

## fix 2: rio precisa aparecer no texto

- **problema**: "Rio Sao Francisco" alucinado em 5 videos sem evidencia
- **solucao**: funcao `rio_aparece_no_texto` (substring + fuzzy 85%) +
  regra `_passa_rio_aparece` que rejeita com `alucinacao_suspeita`
- **commits**: `a7f09f2`, `a1b743b`

## fix 3: blacklist de equipamento em tipo_ceva

- **problema**: "vara de bambu", "Avenado GS" (carretilha), "Isquinha
  Hunter Bait" viraram tipo_ceva em 3 videos
- **solucao**: `EQUIPAMENTO_BLACKLIST` + regra `_passa_tipo_ceva_blacklist`
- **commits**: `cbb56a6`, `f0445d9`

## fix 4: stop-words de especies genericas

- **problema**: 10+ casos de "bonito" (adjetivo), "paca" (mamifero),
  "cimprao" (giria), "pai tainha" (saudacao), "ceba" (ceva mal
  transcrita), "peixe grande" como especies
- **solucao**: `ESPECIES_STOP_TERMS` + regra `_passa_especies_stop_terms`
- **commits**: `c4efbd2`, `1c1a6d5`

## fix 5: prompt isca vs especie alvo

- **problema**: 7 videos com isca (camarao, piabao, lambari, piau)
  confundidas com especie alvo
- **solucao**: prompt lista iscas tipicas (camarao, piabao, lambari,
  minhoca, sardinha) + 3 exemplos "peguei X com Y (isca)"
- **commits**: `d6aee1c`, `8aaceb5`

## fix 6: UF nome -> sigla no prompt

- **problema**: so 4 dos 50 videos tinham estado extraido, mesmo com
  mencao explicita a UF
- **solucao**: prompt lista 9 pares nome/adjetivo -> sigla ("Sao Paulo"
  ou "paulista" -> SP)
- **commits**: `f0ab7db`, `541eb2f`

## fix 7: dicionario de bacias BR

- **problema**: bacia=nome do rio em 6 casos (bacia=Rio Turvo etc) +
  bacia inventada ("Piracema", "Piau Sul")
- **solucao**: `bacias_principais.json` com 12 bacias oficiais + aliases +
  rios associados. funcao `bacia_reconhecida` pra validacao. prompt lista
  as 12 como hint.
- **commits**: `72a768e`, `f4866d0`, `60a2b13`, `1642a74`

## fix 8: investigar bug chunking >4500 palavras

- **problema**: 4 videos com >4500 palavras tinham TODOS os campos null
- **hipotese**: prompt inflado (com hints dos fixes 1-7) + transcricao
  grande = estouro de num_ctx (8192 tokens), resposta esvaziada
- **solucao parte 1**: observabilidade (`_chunk_tem_dados` + logs
  `[chunking-warn]` e `[chunking-bug]` pra pegar flagrante)
- **solucao parte 2**: reduz MAX_PALAVRAS_SEM_CHUNKING de 4500 pra 3000.
  custo: videos muito grandes ganham +1 chamada llm. beneficio:
  ~2500 tokens de folga pra evitar truncagem
- **commits**: `9d3d0eb`, `438598a`, `f3a32f7`

## resultado esperado

taxa de correcao de erros nas proximas rodadas (a validar quando rodar
o pipeline nos 50 videos de novo):

| padrao | casos atuais | fix | casos esperados apos fix |
|--------|--------------|-----|--------------------------|
| tipo_ceva default errado | 25+ | #1 | <5 |
| Rio Sao Francisco alucinado | 5 | #2 | 0 |
| equipamento como ceva | 3 | #3 | 0 |
| especies genericas | 10+ | #4 | <3 |
| isca como especie | 7 | #5 | 2-3 (soft) |
| estado vazio | 46/50 | #6 | 30-35/50 vazio |
| bacia=nome rio | 6 | #7 | 1-2 (soft) |
| video grande tudo null | 4 | #8 | 0-1 |

## como validar

quando jader liberar a GPU:

```bash
.venv/bin/python scripts/testar-retry-schema.py --limit 50
```

depois comparar com as anotacoes manuais do sumario pra ver se a taxa
de erro caiu nos padroes esperados.

## totais

- **8 fixes aplicados**
- **20+ commits** (media 2.5 commits por fix: codigo + testes + as
  vezes ajustes)
- **~40 testes unitarios novos** (ainda com mocks, sem ollama)
- **zero mudanca de comportamento nao coberto por teste**
- **pipeline principal nao quebrou** — fixes sao todos aditivos
  (regras extras no verificador, instrucoes extras no prompt, hint
  do dict)
