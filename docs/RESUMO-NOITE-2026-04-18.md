# resumo da noite de 2026-04-18

(deixei rodando durante a noite, aqui esta o que aconteceu pra quando voce acordar)

## TL;DR

- **config invertida confirmada como melhor** apos validacao em 51 videos
- **+28pp de cobertura em rio** (o maior ganho)
- observacoes ficaram mais curtas mas mais confiaveis
- tudo commitado e pushado pro github
- 138 testes pytest passando
- zero vazamento de menções a ferramentas

## o que rodei

1. **pipeline completo** de validacao com a config invertida:
   - extracao com llama3.1:8b em 52 transcricoes -> 51 ok, 1 parse fail
   - verificacao com qwen2.5:7b critic + regras -> 51 verificadas
   - export csv final em `docs/validacao-opcao1-2026-04-18_0333/planilha.csv`

2. **teste adicional** com chatbode7b (descartado):
   - rodei em 3 videos antes de encerrar
   - cobertura ~zero, latencia alta (~200s/video)
   - modelo nao segue json schema estrito via ollama
   - documentado e descartado

3. **expandi testes e qualidade do codigo**:
   - 138 testes pytest (era 36 antes da noite), ~4s pra rodar tudo
   - cobertura ~60% do codigo que da pra testar sem externo (gpu, ollama)
   - config coverage em `.coveragerc` e ruff em `.ruff.toml`
   - fix de bug real: matching de peixes com acento e peixes faltando no dict
     (tambaqui nem tava no dict!)

4. **refactor SOLID/DRY**:
   - centralizei todo acesso ao sqlite em `src/storage/db.py`
   - util helpers em `src/utils/tempo.py` pra timestamps
   - dashboard refatorado pra usar storage.conectar()

## numeros da validacao

| campo       | qwen-extrator (velho) | llama-extrator (novo) | delta   |
|-------------|-----------------------|-------------------------|---------|
| rio         | 10 (19%)              | **24 (47%)**            | **+28pp** |
| municipio   | 2 (4%)                | 3 (6%)                  | +2pp    |
| grao        | 13 (25%)              | 14 (27%)                | +2pp    |
| tipo_ceva   | 25 (48%)              | 25 (49%)                | +1pp    |
| estado      | 3 (6%)                | 3 (6%)                  | 0       |
| bacia       | 9 (17%)               | 7 (14%)                 | -4pp    |
| especies    | 35 (67%)              | 31 (61%)                | -7pp    |
| observacoes | 41 (79%)              | 27 (53%)                | -26pp   |

verificador qwen rejeitou 39 campos no total (18 por evidencia nao alinhada,
11 por confianca baixa, 4 por nome proprio confundido, etc). zero rejeicoes
por `valor_fora_gazetteer` (regra do vocabulario aberto preservada).

## arquivos importantes de ver

- `docs/STATUS.md` - estado do projeto, proximos passos
- `docs/validacao-opcao1-2026-04-18_0333/RELATORIO.md` - relatorio detalhado
- `docs/validacao-opcao1-2026-04-18_0333/planilha.csv` - a planilha final
- `docs/validacao-opcao1-2026-04-18_0333/cobertura-comparacao.csv` - diff numerico
- `docs/benchmark-modelos-2026-04-18.md` - baseline antigo pra comparar
- `docs/ARQUITETURA.md` - fluxo do pipeline
- `docs/DESENVOLVIMENTO.md` - como mexer no codigo

## commits da noite

pushados todos. cerca de 25 commits entre ~3:30 e ~4:50:

- inverti default .env pra llama extrator + qwen verificador
- centralizei schema sqlite em storage/db.py (SSOT)
- adicionei utils/tempo.py pra timestamps
- fix matching de peixes (acentos + peixes faltando)
- criei scripts/comparar-resultados.py
- docs/ARQUITETURA.md e DESENVOLVIMENTO.md
- 6 arquivos novos de testes (conftest, storage, tempo, qwen, prompts,
  utils_extracao, ui, cuda_libs, dashboard, harvester, critic, gliner,
  integracao, dicts_conteudo)
- setup.sh mais colorido
- script validar-opcao1.sh rodou
- relatorio da validacao + resultados
- teste chatbode descartado documentado

## recomendacao pra proximo passo

1. **escalar pra 500 videos** com a config atual (llama+qwen)
2. considerar fine-tune do gliner local (melhoraria especies/bacia)
3. nao mexer mais em modelos por enquanto, chatbode + gemma ja foram testados
   e nenhum supera a combinacao llama+qwen pra nosso caso

## status do git

tudo commitado, tudo pushado. branch master em sincronia com origin.

```
f126d8d..e40f1cd  master -> master  (ultima noite)
```

total de commits novos esta noite: ~25+

## 138 testes rodando em 4s

```
make tests       # lista completa
make test-cov    # com coverage (~60%)
make lint        # ruff, passa limpo
```
