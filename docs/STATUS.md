# onde a gente parou — 2026-04-18

## o que ja ta pronto

- pipeline completo end-to-end funcional (buscar -> baixar -> transcrever -> extrair -> verificar -> exportar)
- 52 videos de pescaria ja baixados e transcritos em data/transcriptions/
- benchmark feito dos 3 modelos (qwen 2.5 7b, llama 3.1 8b, gemma 3 4b)
  em docs/benchmark-modelos-2026-04-18.md
- config default do .env atualizada pra recomendacao: llama extrai, qwen verifica
- dashboard web (make dashboard) com auto-refresh 3s
- testes pytest (36/36 passando)

## o que falta fazer

1. **validar a inversao da config** (prioridade alta, ~1h de compute):
   ```bash
   bash scripts/validar-opcao1.sh
   ```
   vai gerar docs/validacao-opcao1-DATA/ com planilha.csv + stats.json.
   comparar com docs/benchmark-modelos-2026-04-18.csv pra ver se melhorou.

2. **se validacao deu certo**, escalar pra 500 videos:
   ```bash
   make buscar Q="pesca com ceva" "pescaria" "pesca no rio" ... N=100
   make baixar N=500 W=8
   make transcrever N=500
   make extrair N=500
   make verificar N=500
   make exportar
   ```
   tempo esperado: ~15h wall-clock (pode rodar a noite)

3. **se validacao piorou** em algum campo, investigar e ajustar prompt
   do extrator llama ou do verificador qwen. depois re-rodar validacao.

## como retomar

- ver o que ja rodou: `make status`
- se precisar, rodar `make dashboard` e abrir http://localhost:8000
  pra ver estado em tempo real enquanto extrair/verificar rodam

## dados que ficam preservados

tudo que eh resultado do benchmark ja ta em:
- `data/results/<vid>_extracao_qwen2.5_7b.json` (52 arquivos)
- `data/results/<vid>_extracao_llama3.1_8b.json` (51 arquivos)
- `data/results/<vid>_extracao_gemma3_4b.json` (45 arquivos)
- `data/results/benchmark_TIMESTAMP.json` (relatorio rich)
- `docs/benchmark-modelos-2026-04-18.csv`

o script validar-opcao1.sh NAO apaga nenhum desses. so gera novos em
`data/results/<vid>_extracao.json` (sem suffix).

## config atual (.env)

```
MODEL_EXTRATOR=llama3.1:8b
MODEL_VERIFICADOR=qwen2.5:7b
WHISPER_MODEL=large-v3-turbo
WHISPER_DEVICE=auto
```

## notas soltas

- o .notes/ (ignorado pelo git, local only) tem as convencoes de estilo
  e a regra do vocabulario aberto. sempre ler quando voltar pro repo
- os modelos ollama ja estao baixados na maquina atual (qwen2.5, llama3.1,
  gemma3, gemma3:4b, llama3.2:3b, chatbode7b, gaia4b)
- se quiser testar outros modelos no benchmark depois:
  `python -m src.benchmark --modelos chatbode7b gaia4b llama3.2:3b --limit 52`
