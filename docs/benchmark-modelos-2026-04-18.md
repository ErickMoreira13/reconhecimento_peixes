# benchmark dos modelos extratores — 2026-04-18

ponto de partida do projeto. 52 videos de youtube transcritos pelo whisper
large-v3-turbo e extraidos por 3 modelos diferentes do ollama. objetivo eh
decidir quem vira o extrator default e quem vira o verificador.

## setup

- maquina: rtx 4060 8gb, 64gb ram
- whisper: large-v3-turbo fp16 em cuda (~30x realtime)
- prompt: single-prompt com 8 campos, vocabulario aberto (ver src/extracao/prompts.py)
- videos: 52 transcritos, 44 em comum entre os 3 modelos (gemma falhou em 7)
- queries: "pesca com ceva", "pescaria de tucunare", "pesca no rio", "pesca amazonia", "ceva pesca"

## resumo dos modelos

| metrica                     | qwen 2.5 7b | llama 3.1 8b | gemma 3 4b |
|-----------------------------|-------------|---------------|------------|
| videos processados          | 52          | 51            | 45         |
| latencia media (s)          | **17.8**    | 18.4          | 20.2       |
| latencia p95 (s)            | 26.0        | 35.2          | **9.9**    |
| parse fail (%)              | 15.4%       | **9.8%**      | 11.1%      |
| especies unicas descobertas | 56          | 53            | **66**     |
| obs comprimento medio (pal) | 14          | 12            | **8**      |
| obs max (pal)               | 41          | 38            | 72         |
| vram ocupada                | 4.7 gb      | 4.9 gb        | **2.6 gb** |

## cobertura por campo (% videos com valor nao-nulo)

| campo       | qwen    | llama      | gemma      |
|-------------|---------|------------|------------|
| bacia       | 17%     | 14%        | **47%**    |
| especies    | 67%     | 73%        | **76%**    |
| estado      | 6%      | 6%         | **49%**    |
| grao        | 25%     | 27%        | **53%**    |
| municipio   | 4%      | 12%        | **40%**    |
| observacoes | 79%     | **88%**    | 87%        |
| rio         | 19%     | 55%        | **60%**    |
| tipo_ceva   | 48%     | **69%**    | **69%**    |

gemma ganha em cobertura mas ver secao de alucinacao antes de sair
recomendando.

## divergencias em campos geograficos

"divergencia" = modelo preencheu estado/municipio/rio/bacia, os outros 2
deixaram null. proxy de alucinacao (nao prova, mas suspeita).

| modelo       | divergencias (de 44 videos em comum) |
|--------------|--------------------------------------|
| qwen 2.5 7b  | **1**                                |
| llama 3.1 8b | 6                                    |
| gemma 3 4b   | 52                                   |

gemma preenche 52 vezes o que os outros 2 deixaram null. quase todas dessas
eh alucinacao — ele chuta estado, municipio, rio quando a transcricao nao
deixa claro.

## evidencias nao alinhadas com a transcricao

medido com smith-waterman partial ratio < 80 entre o campo `evidencia`
retornado pelo modelo e o texto da transcricao completa.

| modelo       | desalinhadas | total checadas | taxa      |
|--------------|--------------|----------------|-----------|
| qwen 2.5 7b  | 2            | 51             | **3.9%**  |
| gemma 3 4b   | 4            | 37             | 10.8%     |
| llama 3.1 8b | 21           | 72             | 29.2%     |

atencao: a taxa do llama eh alta mas grande parte eh canonizacao agressiva,
nao alucinacao:
- llama devolve `rio = "Rio Sao Francisco"` com `evidencia = "velho chico"`
  — "velho chico" ESTA no texto, so que ele normalizou pro nome canonico
- ja o gemma tem alucinacao real: `estado = "SP"` com
  `evidencia = "Acordei cedinho hoje, sabadao"` (nem cita SP)

entao a metrica castiga o llama injustamente. na pratica o llama canoniza
bem, so usa a expressao popular como evidencia em vez da forma normalizada.

## exemplos qualitativos

video F6AcoBAAsXI (pescaria generica de tilapia):

| campo     | qwen            | llama           | gemma            |
|-----------|-----------------|-----------------|------------------|
| estado    | null            | null            | SP (inventado)   |
| rio       | null            | null            | Rio Sao Francisco (inventado) |
| tipo_ceva | cano_pvc (errado) | saco_de_ceva (ok) | saco_de_ceva (ok) |
| grao      | milho (ok)      | milho (ok)      | milho (ok)       |
| especies  | [castilapia, tilapia] | [tilapia] | [castilapia, tilapia] |
| obs       | bom resumo      | vazio           | "sem obs"        |

## veredito

- **qwen 2.5 7b como extrator**: conservador demais. cobertura de rio 19%,
  municipio 4% significa que ta deixando info real na mesa em >30% dos videos
- **llama 3.1 8b como extrator**: melhor cobertura com alucinacao aceitavel.
  canonizacao agressiva eh gerenciavel com um verificador bom
- **gemma 3 4b como extrator**: alucina UF/municipio/rio/bacia. **descartado
  pra campos geograficos**. serve pra descobrir especies (66 unicas vs 56/53)
- **qwen 2.5 7b como verificador**: perfeito. conservador, familia diferente
  do llama (evita vies circular), baixa taxa de alucinacao propria
- **llama como verificador** (config atual): ruim. ele aceita demais, nao filtra
  as canonizacoes dele mesmo

### recomendacao

inverter config:
- extrator: **llama 3.1 8b** (era qwen)
- verificador: **qwen 2.5 7b** (era llama)

### por que inverter

| problema da config atual | como a inversao resolve |
|--------------------------|--------------------------|
| qwen extrai = perde 36pp de rio, 21pp de ceva | llama pega mais info |
| llama critica = aceita demais | qwen critica = rejeita alucinacao |
| mesma familia entre extrator e criticoeh duvidoso | familia diferente (qwen vs llama) |

### o que falta validar

o benchmark mediu **so o extrator**. nao medimos ainda a combinacao
llama-extrator + qwen-verificador no pipeline completo. antes de escalar
pra 500 videos, rodar essa validacao nos 52 que ja estao transcritos.

eh barato: ~1h de compute, reusa as transcricoes.

## dados brutos

CSV em [benchmark-modelos-2026-04-18.csv](./benchmark-modelos-2026-04-18.csv).

arquivos por video em `data/results/<video_id>_extracao_<suffix>.json` (fora
do repo, gitignored).

## proximos passos

- [ ] rodar extrair+verificar+exportar nos 52 videos com config invertida
      (llama-extrator + qwen-verificador)
- [ ] comparar csv resultante com o baseline (qwen extrator + llama crit)
- [ ] se melhor, escalar pra 500 videos
- [ ] se pior, investigar qual campo regrediu
