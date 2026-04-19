# lote 04 — videos 31-40

## 31. axu85n0-34U (25 palavras)

**extraido**: tudo null
**transcricao**: denuncia de rede de pesca predatoria, muito curto
**diagnostico**: OK (pulou certo)

---

## 32. bdKr7GC3Q_w (2205 palavras)

**extraido**: municipio=`Entrevazante`, rio=`Rio Escurao`,
bacia=`Rio Sao Francisco`, tipo_ceva=`ceva_de_chao`, grao=`soja`,
especies=`[Piau]`

**transcricao**: "Temporada 2025 no Rio Escurao, municipio mineiro
Entrevazante, Paracatu", "ceva: milho moido, soja moida curtida, racao
de coelho azeda, farelo da casca do arroz, bolas redondas", "piau, pacu,
curimba, trincha"

**diagnostico**: segundo melhor extracao do dataset
- municipio=`Entrevazante` ✅ (correto)
- rio=`Rio Escurao` ✅
- bacia=`Rio Sao Francisco` — PARCIALMENTE CERTO. Rio Escurao eh afluente
  do Sao Francisco (bacia correta). mas o NOME do campo eh "bacia" e ele
  deveria ser "bacia do Sao Francisco" ou "Sao Francisco", nao
  "Rio Sao Francisco" (isso eh rio, nao bacia)
- tipo_ceva=`ceva_de_chao` — ERRO. eh BOLA_DE_MASSA (bolas redondas)
- grao=`soja` — parcial. tem milho+soja+racao coelho+farelo arroz
- especies=`[Piau]` — parcial. FALTOU pacu, curimba, trincha
- FALTOU: estado=MG (ele fala "municipio mineiro" explicito)

**correcao**: estado=MG, bacia=Sao Francisco (sem "Rio"),
tipo_ceva=bola_de_massa, especies=[piau, pacu, curimba, trincha]

**observacao: aqui a mencao a Sao Francisco eh LEGITIMA** (Rio Escurao
eh afluente). os outros casos do lote 1+2+3 com "Rio Sao Francisco"
sem evidencia textual continuam sendo alucinacao. mas isso sugere que
o modelo aprendeu a associacao "Rio Escurao/Paracatu -> Sao Francisco"
e pode estar projetando isso em outros contextos. investigar.

---

## 33. c6V4OBiQPAU (36 palavras)

**extraido**: tudo null
**transcricao**: "novo pescador da familia, menino sapeca", video muito curto
**diagnostico**: OK

---

## 34. cJm-UFNpOFw (1779 palavras)

**extraido**: rio=`Rio Iriri`, bacia=`rio iriri`,
tipo_ceva=`ceva_solta_na_agua`, especies=`[paca]`

**transcricao**: "acampamento na beira do rio iriri", "trairao muito
grande", "sair um cachara"

**diagnostico**:
- rio=`Rio Iriri` ✅
- bacia=`rio iriri` — ERRO. rio iriri eh afluente do xingu, bacia correta
  seria Amazonica (ou Xingu). MESMO ERRO do video 28 (bacia=nome do rio)
- tipo_ceva=`ceva_solta_na_agua` — ERRO. nem usa ceva, pesca com anzol
  simples + isca
- especies=`[paca]` — ERRO CLASSICO. "a paca deve estar comendo aqui" eh
  referencia ao MAMIFERO PACA comendo fruta na margem. paca nao eh peixe.
  alvos reais: trairao, cachara. segundo video do dataset com "paca"
  errada (1o foi video 26)

**correcao**: bacia=amazonica (ou xingu), tipo_ceva=null,
especies=[traira, cachara]

---

## 35. dJt0bE7QLQ0 (5872 palavras)

**extraido**: municipio=`Santarem`, rio=`Tapajos`,
tipo_ceva=`vara de bambu`, grao=`milho`, especies=`[pacuna]`

**transcricao**: "canal Pescadora Amazonica", "frente da cidade de
Santarem", "pescaria de piau e peixe de couro", "camarao como isca"

**diagnostico**:
- municipio=`Santarem` ✅
- rio=`Tapajos` — SUSPEITO mas defensavel. Santarem fica na confluencia
  Tapajos+Amazonas. mas nao vi nome explicito no trecho lido
- tipo_ceva=`vara de bambu` — ERRO CRASSO. VARA DE BAMBU eh equipamento
  de pesca, nao ceva. extrator confundiu material com ceva (similar ao
  video 27 com "Avenado GS" = carretilha)
- grao=`milho` — SUSPEITO. nao vi no trecho, pode ter no resto
- especies=`[pacuna]` — provavel distorcao de "pacu" ou nome regional
  raro. FALTOU piau (explicito) e peixe de couro
- FALTOU: estado=PA, bacia=amazonica

**correcao**: estado=PA, bacia=amazonica, tipo_ceva=null,
especies=[piau, peixe de couro]

---

## 36. ek1z0smMBz4 (27 palavras)

**extraido**: tudo null
**transcricao**: "saco de batata, pedras, nos no saco, amarra linha" —
truque de saco de ceva rapido
**diagnostico**: OK (pulou pelo threshold)

**observacao**: eh descricao EXPLICITA de saco_de_ceva. se o threshold
fosse menor, teria dado pra extrair

---

## 37. esls9bNSaUw (1515 palavras)

**extraido**: rio=`Rio Turvo`, bacia=`Rio Turvo`, especies=`[tucunare]`,
obs ok

**transcricao**: "Rio Turvo", "tucunare, camarao como isca,
lambarizinho", "piau grande"

**diagnostico**:
- rio=`Rio Turvo` ✅
- bacia=`Rio Turvo` — ERRO. mesmo padrao recorrente (rio=bacia=mesmo nome)
- tipo_ceva=null ✅ (nao tem ceva, pesca com isca)
- especies=`[tucunare]` — parcial. FALTOU piau
- obs boa

**correcao**: bacia=null (ou "Tiete-Parana" se quiser inferir regiao),
especies=[tucunare, piau]

---

## 38. f-AIQY6Hqok (6288 palavras — mega)

**extraido**: rio=`Rio Sao Francisco`, tipo_ceva=`ceva_solta_na_agua`,
especies=`[Ceba]`

**transcricao**: "Mariana do ceu" (expressao de susto), pescaria com
esposa, menciona "Luzinautica" (loja de motores), muita conversa
motor/barco

**diagnostico**:
- rio=`Rio Sao Francisco` — ALUCINACAO. mais um caso do padrao
- tipo_ceva=`ceva_solta_na_agua` — ERRO
- especies=`[Ceba]` — ERRO ABSURDO. "Ceba" eh CEVA mal transcrita pelo
  whisper (ele fala muito de ceva no video). nao eh peixe. o extrator
  pegou a palavra ceba achando que era nome de especie
- provavel falta de sinal por ser texto gigante (chunking perde)

**correcao**: tudo null exceto pela reexaminacao do texto completo

---

## 39. hRVlgQX5ohA (70 palavras)

**extraido**: especies=`[camaraozinho]`, obs null

**transcricao**: "camaraozinho como isca, esperar os tucuna bater"

**diagnostico**:
- especies=`[camaraozinho]` — ERRO (padrao ja visto). camarao eh ISCA.
  alvo real: TUCUNARE (explicito no texto!)
- "viu rapaziada? eh assim que se pega o tucunar" — frase final do video
  confirma especie

**correcao**: especies=[tucunare]

---

## 40. ksyD6vm3gOA (28 palavras)

**extraido**: tudo null
**transcricao**: "cachaca e leite, preparar a ceva aqui, amanha previsao
chuva, 4 dias esta pronta"
**diagnostico**: OK (pulou por ser curto)

**observacao**: descricao interessante de ceva caseira com cachaca+leite
se tivesse mais conteudo

---

## sumario do lote

destaques:

- **video 32 (bdKr7GC3Q_w)** eh a segunda melhor extracao e traz uma
  descoberta: a mencao ao **Sao Francisco aqui eh LEGITIMA** (Rio Escurao
  eh afluente). isso significa que o extrator associou corretamente em
  um caso real — sugerindo que as alucinacoes em outros videos sao
  projecao dessa associacao em contextos errados
- **mais 2 videos com "paca" como especie** (video 34, somado ao 26 do
  lote 3): total de 3 ocorrencias. eh erro sistematico — extrator nao
  sabe que paca eh mamifero
- **novo "equipamento como ceva"**: video 35 tem tipo_ceva="vara de
  bambu" (equipamento). similar ao video 27 do lote 3 com "Avenado GS"
  (carretilha). o extrator nao entende dominio tecnico de pesca
- **"Ceba" como especie** (video 38): whisper transcreveu "ceva" como
  "ceba" e o extrator pegou como peixe
- **bacia=nome do rio**: video 34, 37 repetem o erro dos videos 28, 18.
  ja eh 4 casos

padroes acumulados lotes 1-4:

1. alucinacao em rios: Rio Sao Francisco (6x agora, sendo 1 legitima)
2. `tipo_ceva=ceva_solta_na_agua` como default errado: ja passou de 20
   ocorrencias
3. confusao isca/especie: piau, camarao, piabao, lambarizinho como
   especies quando sao iscas — 7+ videos
4. bacia=rio mesmo nome: 4 casos
5. equipamento virando ceva: 2 casos graves (carretilha, vara bambu)
6. "paca" confundida com especie: 3 casos
7. palavras genericas pegas como especies: bonito, cimprao, ceba,
   camaraozinho, peixe bonito, peixe grande, escar-viva, paca — 8+ casos

anotado por jader, 2026-04-19.
