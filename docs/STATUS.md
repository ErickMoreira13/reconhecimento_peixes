# onde a gente parou — 2026-04-19

## o que ja ta pronto

- pipeline completo end-to-end funcional
- 52 videos de pescaria baixados e transcritos
- **benchmark** dos 3 modelos extratores em docs/benchmark-modelos-2026-04-18.md
- **validacao da opcao 1** rodada a noite do 2026-04-18 em docs/validacao-opcao1-2026-04-18_0333/
- config default .env com llama extrator + qwen verificador (opcao vencedora)
- dashboard web (make dashboard)
- **138 testes pytest passando**, coverage ~60% do codigo testavel sem externo
- ruff config frouxa (lint so pega bugs)
- scripts auxiliares: check-env, models, benchmark, comparar-resultados, analise

## decisao final sobre extrator/verificador

comparacao feita nos 51 videos (1 parse fail na nova extracao):

| campo       | qwen-extrator (velho) | llama-extrator (novo) | delta |
|-------------|-----------------------|-------------------------|-------|
| rio         | 10 (19%)              | **24 (47%)**            | +28pp |
| municipio   | 2 (4%)                | 3 (6%)                  | +2pp  |
| grao        | 13 (25%)              | 14 (27%)                | +2pp  |
| tipo_ceva   | 25 (48%)              | 25 (49%)                | +1pp  |
| estado      | 3 (6%)                | 3 (6%)                  | 0pp   |
| bacia       | 9 (17%)               | 7 (14%)                 | -4pp  |
| especies    | 35 (67%)              | 31 (61%)                | -7pp  |
| observacoes | 41 (79%)              | 27 (53%)                | -26pp |

ganho grande em rio. perda em observacoes eh correta (verificador qwen
rejeitou resumos genericos sem entidade ancorada). net positivo.

**manter config atual no .env** (llama extrator + qwen verificador).

## o que falta fazer

1. **escalar pra 500+ videos** com harvester infinito (issue #11, ja implementado):
   ```bash
   make harvester-loop        # roda em loop, para quando tudo saturar
   make queries               # acompanha status das queries
   make baixar N=500 W=8
   make transcrever N=500
   make extrair N=500
   make verificar N=500
   make exportar
   ```
   harvester loop rotaciona automaticamente entre ~30 queries em `data/queries.yaml`,
   detectando saturacao por dedup (>= 0.8) e por taxa de rejeicao (> 0.7).

2. **~~testar gliner 2 -> 4 labels~~** (issue #10): **REJEITADO** apos teste em
   50 videos. latencia +261%, cobertura de bacia -16pp. revertido em `e188759`.
   resultado em `docs/comparacao-gliner-labels/RESULTADO.md`.

3. **fine-tune do gliner local** (issue #9, adiado):
   - precisa ~20k exemplos validados antes, hoje so tem 7k do v1
   - reabrir quando dataset validado pelo pipeline atual chegar la

4. **anotacoes manuais dos 50 videos** (feito 2026-04-19) —
   `docs/anotacoes-manuais/sumario.md` tem 8 padroes de erro ranqueados,
   com recomendacoes de fix. destaque: apenas 10% dos videos tem extracao
   aproveitavel sem correcao.

5. **retry de schema errado** (feito 2026-04-19) — 3 camadas de defesa no
   extrator: parse robusto + retry 1x com feedback + budget estrito. visivel
   em `docs/teste-retry-schema/`. detalhes do caso que originou em
   `commit 888a990`.

6. **8 FIXES APLICADOS** (feito 2026-04-19) — todos os padroes do
   sumario-manual atacados. ver `docs/fixes-aplicados-2026-04-19.md`:
   - fix 1: tipo_ceva exige evidencia (prompt + verificador)
   - fix 2: rio precisa aparecer no texto (verificador)
   - fix 3: blacklist equipamento pra tipo_ceva
   - fix 4: stop-terms pra especies genericas
   - fix 5: prompt isca vs especie alvo
   - fix 6: prompt UF nome -> sigla
   - fix 7: dicionario 12 bacias BR + validacao + hint no prompt
   - fix 8: chunking observabilidade + reduz MAX_PALAVRAS pra 3000

   proximo: validar empiricamente quando GPU livre.

## comandos pra retomar

- `make status` - ver etapa atual
- `make dashboard` - http://localhost:8000
- `make tests` - 252 testes (~14s)
- `.venv/bin/python scripts/testar-retry-schema.py --limit 10` - smoke retry schema
- `make harvester-loop` - loop perpetuo de coleta
- `make queries` - status das queries do loop
- `make comparar A=qwen2.5_7b B=_default_` - diff entre resultados
- `make analise` - detalhe do ultimo benchmark

## config atual (.env)

```
MODEL_EXTRATOR=llama3.1:8b
MODEL_VERIFICADOR=qwen2.5:7b
WHISPER_MODEL=large-v3-turbo
WHISPER_DEVICE=auto
```

## arquivos que importam

- `docs/ARQUITETURA.md` - fluxo de dados, modulos, estados do video
- `docs/DESENVOLVIMENTO.md` - como rodar testes, padroes, gotchas
- `docs/benchmark-modelos-2026-04-18.md` - baseline dos 3 modelos
- `docs/validacao-opcao1-2026-04-18_0333/RELATORIO.md` - resultado da noite
- `docs/validacao-opcao1-2026-04-18_0333/planilha.csv` - dados extraidos
- `docs/anotacoes-manuais/sumario.md` - padroes de erro consolidados dos 50 videos
- `docs/comparacao-gliner-labels/RESULTADO.md` - motivo da rejeicao 4 labels
- `docs/teste-retry-schema/README.md` - smoke test do retry de schema
- `docs/fixes-aplicados-2026-04-19.md` - consolidacao dos 8 fixes do sumario-manual
