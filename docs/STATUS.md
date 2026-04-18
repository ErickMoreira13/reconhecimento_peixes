# onde a gente parou — 2026-04-18 (noite)

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

1. **escalar pra 500+ videos** com a config validada:
   ```bash
   make buscar Q="pesca com ceva" "pescaria tucunare" "pesca rio" N=100
   make baixar N=500 W=8
   make transcrever N=500
   make extrair N=500
   make verificar N=500
   make exportar
   ```
   tempo esperado: ~15h (pode rodar a noite)

2. **fine-tune do gliner local** (opcional, melhoraria especies/bacia):
   - dataset de 7011 exemplos ja existe (do projeto antigo)
   - ~3-5h treino em rtx 4060
   - substituiria o gliner zero-shot que a gente usa hoje

3. **testar chatbode7b** como extrator (pt-br nativo):
   - ja baixado na maquina
   - rodar `make benchmark MODELOS="llama3.1:8b chatbode7b" N=30`
   - ver se ganha em pt-br especificamente

## comandos pra retomar

- `make status` - ver etapa atual
- `make dashboard` - http://localhost:8000
- `make tests` - 138 testes
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
