# anotacoes manuais — extracoes dos 50 videos

revisei os 50 videos que o pipeline processou com config 2 labels (peixe+bacia)
e anotei o que o extrator acertou, errou ou alucinou. a ideia eh ter uma
base minima de correcao manual pra calibrar thresholds e detectar padroes
de erro.

fonte dos dados: `docs/comparacao-gliner-labels/parciais/2labels/<video_id>.json`
fonte das transcricoes: `data/transcriptions/<video_id>.json` (local, nao
commitado)

## formato das anotacoes

cada lote tem um arquivo `lote-NN.md` com uma secao por video. cada secao
tem 3 partes:

- **extraido pelo pipeline**: copio o que saiu do qwen extrator (sumarizado)
- **o que ta certo na transcricao**: o que eu vi assistindo/lendo
- **diagnostico**: o que errou, acertou, faltou. se acertou tudo, so marco ok

assinatura no final de cada lote: quem anotou + data.

## lotes

- [lote-01.md](lote-01.md) — videos 1-10
- [lote-02.md](lote-02.md) — videos 11-20
- [lote-03.md](lote-03.md) — videos 21-30
- [lote-04.md](lote-04.md) — videos 31-40
- [lote-05.md](lote-05.md) — videos 41-50

sumario geral em [sumario.md](sumario.md) com os padroes que apareceram.

## porque existe

duas razoes:

1. precisa de base de comparacao pra saber quanto o verificador esta rejeitando
   coisa certa (falso positivo) ou deixando passar erro (falso negativo)
2. quando o dataset crescer pra +500 videos, esses 50 viram a base pra treinar
   um verificador melhor ou ajustar thresholds do critic
