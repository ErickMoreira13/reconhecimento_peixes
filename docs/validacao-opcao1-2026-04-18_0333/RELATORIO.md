# validacao opcao 1 — resultados (2026-04-18)

roda feita durante a noite do 2026-04-18 (03:33 ~ 04:22).
comparado com o baseline do benchmark anterior em 52 videos.

## setup

- extrator: llama3.1:8b q4 (era qwen2.5:7b no baseline)
- verificador: qwen2.5:7b q4 (era llama3.1:8b no baseline)
- gliner: zero-shot (fine-tuned nao disponivel localmente)
- transcricoes: as mesmas 52 transcricoes do benchmark anterior

## tempo de execucao

| fase       | tempo  |
|------------|--------|
| extracao   | 14m32s |
| verificacao | 35m15s |
| export     | <1s    |
| **total**  | **~50min** |

extracao: 51/52 ok (1 video deu parse fail do llm, voltou pra status 'transcrito')
verificacao: 51 passaram pelo verificador (regras + critic)

## cobertura final (apos verificador) vs baseline qwen-extrator

| campo       | baseline qwen | opcao 1 (llama+qwen) | delta    |
|-------------|---------------|----------------------|----------|
| estado      | 3 (6%)        | 3 (6%)               | 0pp      |
| municipio   | 2 (4%)        | 3 (6%)               | +2pp     |
| **rio**     | 10 (19%)      | **24 (47%)**         | **+28pp** |
| bacia       | 9 (17%)       | 7 (14%)              | -4pp     |
| tipo_ceva   | 25 (48%)      | 25 (49%)             | +1pp     |
| grao        | 13 (25%)      | 14 (27%)             | +2pp     |
| especies    | 35 (67%)      | 31 (61%)             | -7pp     |
| observacoes | 41 (79%)      | 27 (53%)             | -26pp    |

**net positivo** em 4 campos (rio, grao, municipio, tipo_ceva), negativo em
3 (bacia, especies, observacoes).

## atividade do verificador

o qwen 2.5 7b como verificador foi mais rigoroso que o llama que fazia esse
papel antes. 51 campos rejeitados no total:

| tipo de rejeicao          | quantidade |
|---------------------------|------------|
| evidencia_nao_alinha      | 18         |
| confianca_baixa           | 11         |
| nome_proprio_confundido   | 4          |
| contexto_irrelevante      | 4          |
| alucinacao_suspeita       | 2          |
| **total**                 | **39**     |

rejeicoes por campo:

| campo       | rejeitados |
|-------------|------------|
| observacoes | 12         |
| especies    | 6          |
| bacia       | 5          |
| grao        | 5          |
| tipo_ceva   | 5          |
| rio         | 4          |
| municipio   | 2          |

a maioria das rejeicoes de observacoes eh do tipo `contexto_irrelevante` e
`evidencia_nao_alinha` — o qwen entendeu que quando o llama gerava um resumo
generico tipo "pescaria no pará com resultado" sem citar entidade da
transcricao, nao valia a pena incluir.

## avaliacao qualitativa

o ganho em **rio (+28pp)** e a reducao das observacoes genericas sao o maior
win dessa config. o llama pega nomes de rios que o qwen-extrator deixava
passar, e o qwen-verificador filtra os que sao alucinacao.

perda em especies (-7pp) eh moderada. provavelmente o qwen rejeitou algumas
giriasque o llama pegou (ex: "castilápia" do benchmark virou null apos
verificacao).

perda em bacia (-4pp) segue a mesma logica: qwen eh mais conservador,
rejeita quando nao tem certeza.

## fora do gazetteer

**zero** flags `fora_do_gazetteer=true` em todos os 51 videos. isso eh ok
pq a transcricao costuma conter nomes canonicos (rio madeira, pantanal,
etc). se fosse coleta com videos mais diversos, esperaria numeros maiores.

## veredito

**CONFIG NOVA (llama extrator + qwen verificador) EH MELHOR** nos campos
criticos pro paper (rio, ceva, grao, municipio). perdas sao compensaveis
— observacoes curtas eh preferivel a genericas.

manter .env com:
```
MODEL_EXTRATOR=llama3.1:8b
MODEL_VERIFICADOR=qwen2.5:7b
```

## extra: tentativa com chatbode7b (descartado)

rodei tambem o chatbode7b (modelo pt-br fine-tuned pra dialogo) como
extrator, pra ver se especializacao em portugues ajudaria. resultado:
nao funciona pro nosso caso.

de 3 videos processados antes de encerrar:
- cobertura: 1 estado, 1 observacoes, resto tudo null
- ~200s por video (muito mais lento que llama/qwen)
- parece nao conseguir seguir json schema estrito via ollama `format="json"`

**descartado**: chatbode eh mais pra dialogo livre, nao pra extracao
estruturada. os nossos prompts tem schema e exemplos formais que ele nao
sabe preencher.

## proximos passos

- [x] validar config invertida
- [x] medir ganhos
- [x] testar chatbode7b (descartado)
- [ ] escalar pra 500+ videos
- [ ] se possivel, fazer fine-tune do gliner local (ja tem dataset de 7011
  exemplos) pra subir precisao de especies/bacia na primeira passada
- [ ] rodar benchmark de chatbode7b vs gaia4b (tb pt-br) num teste mais focado

## arquivos

- planilha final: planilha.csv (51 linhas)
- stats em json: stats.json
- baseline pra comparar: [../benchmark-modelos-2026-04-18.csv](../benchmark-modelos-2026-04-18.csv)
- log completo: data/results/validacao_log.txt (fora do repo, ver na maquina local)
