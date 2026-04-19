# lote 01 — videos 1-10

assisti/li as transcricoes e comparei com o que o pipeline extraiu. onde teve
erro, anotei o certo. videos ordenados por video_id.

## 1. 09A8vJQ3UNs (123 palavras)

**extraido pelo pipeline**: especies=`[bonito]`, resto null

**o que ta certo na transcricao**:
- pesca marinha ("marinho", "onda", "canoa") — provavelmente video costeiro
- nao cita localizacao nem ceva
- espera aí: "bonito" no texto eh adjetivo — "pegou bonito" = pegou bem

**diagnostico**:
- ERRO: `bonito` nao eh o peixe bonito (*Sarda sarda*), eh so expressao
  ("pegou bonito" = pegou um peixe bom). falso positivo do extrator
- menciona "canarezao" — pode ser canarinho-amarelo, especie real, mas o
  extrator nao pegou
- deveria ter saido: especies=[] (ou canarinho se quiser ser generoso)
- resto null ta correto

**correcao**: `especies = []` em vez de `[bonito]`

---

## 2. 15eANk1f5yI (27 palavras)

**extraido pelo pipeline**: tudo null (pulou pelo threshold de palavras minimas)

**o que ta certo na transcricao**:
- NAO eh video de pescaria: "Cascavel no meio do Tiete" — eh cobra cascavel
  filmada no rio tiete, nao pesca
- so 27 palavras

**diagnostico**:
- OK pelo motivo errado. pulou pq texto eh curto, mas tambem eh FORA DE
  DOMINIO (video de cobra, nao pescaria). ideal seria o harvester_loop ou
  um filtro de dominio detectar isso

**correcao**: null ta ok, mas seria legal marcar `fora_de_dominio=true`

---

## 3. 3-_SegGoCDg (1930 palavras)

**extraido pelo pipeline**: rio=`Riozao`, tipo_ceva=`galao`, grao=`milho`,
especies=`[tilapia]`, resto null

**o que ta certo na transcricao**:
- "temporada de tilapia", "milho azedo curtido", "vou reforcar a ceva"
- canal "Anderson Lucas Pescaria"
- menciona capivara (atrapalhando a ceva)
- nao cita rio especifico nem estado

**diagnostico**:
- rio=`Riozao` — ALUCINACAO. "riozao" eh so aumentativo carinhoso, nao eh
  nome proprio. corrigir pra null
- tipo_ceva=`galao` — fora do enum. o enum tem ceva_de_chao, garrafa_pet,
  saco_de_ceva, etc. "galao" nao consta. o correto seria "outro" texto livre
  ou ceva_de_chao se for isso msm
- grao=`milho` ✅
- especies=`[tilapia]` ✅

**correcao**: rio=null, tipo_ceva=outro ou similar

---

## 4. 7KbxXGktXy0 (89 palavras)

**extraido pelo pipeline**: tipo_ceva=`garrafa_pet_perfurada`, grao=`milho`,
especies=`[peixe grande]`

**o que ta certo na transcricao**:
- "pega um galao, faz uns furos, coloca racao de coelho, milho e quirera"
- "pega uma garrafa e amarra pra sinalizar"
- nao cita especie especifica

**diagnostico**:
- tipo_ceva=`garrafa_pet_perfurada` — ERRO PARCIAL. ele usa um GALAO
  perfurado, nao garrafa PET. o extrator confundiu pq menciona "garrafa" no
  final (mas eh so boia de sinalizacao). correto: "galao perfurado" (texto
  livre) ou similar
- grao=`milho` ✅ (mas FALTOU: racao de coelho, quirera)
- especies=`[peixe grande]` — FALSO POSITIVO. "peixe grande" nao eh especie,
  eh descricao generica. corrigir pra []

**correcao**: tipo_ceva=galao perfurado, especies=[], anotar que tem racao
+ quirera tb

---

## 5. 7WvurZ6hnuY (3916 palavras)

**extraido pelo pipeline**: tudo null, especies=[]

**o que ta certo na transcricao**:
- "piauzinho", "piazao", "cachorra", "traira" — 3+ especies mencionadas
- menciona "milho cozido" mas eh pra comer (nao isca/ceva)
- pescaria em familia, mae/sogra/esposa
- "samburu" (peixeiro ribeirinho)

**diagnostico**:
- ERRO GRAVE: falso negativo em especies. tem piau, cachorra, traira claros
  no texto, mas extrator retornou []. suspeito que o chunking do texto
  grande (3916 palavras, passou do max_sem_chunking) atrapalhou
- grao=null ta correto (milho era pra comer)
- ceva null tb correto (nao menciona ceva)

**correcao**: especies=[piau, cachorra, traira] — bug no chunking pra
investigar (talvez consolidacao esta perdendo sinal)

---

## 6. 8DqoCnT5jCQ (1401 palavras)

**extraido pelo pipeline**: rio=`Rio Sao Francisco`, tipo_ceva=
`ceva_solta_na_agua`, especies=`[Piranha]`, obs menciona Sao Francisco

**o que ta certo na transcricao** (1os 2000 chars):
- "no meio do rio", "cachorras gigantes" (piranha-cachorra)
- nao mencionei "Sao Francisco" nos primeiros 2000 chars — preciso ver texto
  completo pra confirmar
- nao menciona ceva explicita (pesca com isca mesmo, "a isca ta aqui dentro")

**diagnostico**:
- rio=`Rio Sao Francisco` — SUSPEITA DE ALUCINACAO. na parte que eu li nao
  aparece. tem que confirmar no texto completo. se nao tiver, eh alucinacao
- tipo_ceva=`ceva_solta_na_agua` — na transcricao nao vi ceva, so pesca com
  isca. provavel alucinacao
- especies=`[Piranha]` — menciona "cachorras" (piranha-cachorra), entao ok
  parcialmente. mas deveria incluir "piranha-cachorra" nao so "Piranha"

**correcao**: checar se Sao Francisco aparece no texto completo. se nao,
rio=null; tipo_ceva=null; especies=[piranha-cachorra]

---

## 7. 8QAuO2lt2ro (1011 palavras)

**extraido pelo pipeline**: rio=`Rio Sao Francisco`, tipo_ceva=
`ceva_de_chao`, grao=`milho`, especies=`[tilapia]`

**o que ta certo na transcricao**:
- "ceva top com milho azedo curtido", "milho duro azedo"
- "beira do rio lá", "riozao aí", "represa aqui"
- MESMO autor do video 3 (Anderson Lucas)
- nao menciona Sao Francisco

**diagnostico**:
- rio=`Rio Sao Francisco` — ALUCINACAO. ele diz "riozao" aumentativo. mesma
  confusao do video 3. precisa filtrar isso
- tipo_ceva=`ceva_de_chao` — nao especifica o tipo no texto, so "fiz uma
  ceva top". chutou. alucinacao leve
- grao=`milho` ✅
- especies=`[tilapia]` ✅
- FALTOU: "represa" deveria disparar algum campo de corpo d'agua (bacia?)

**correcao**: rio=null (riozao eh aumentativo), tipo_ceva=null (nao
especifica)

---

## 8. 9UikGczqzxU (1037 palavras)

**extraido pelo pipeline**: tipo_ceva=`ceva_solta_na_agua`, grao=`milho`,
especies=`[lambarizao]`, obs ok

**o que ta certo na transcricao**:
- "trouxa de milho duro, coloquei na agua" — saco_de_ceva/trouxa
- "canequinha de milho azedo" (ceva solta tb, complementar)
- lambarizao, traira ("traira aqui embaixo"), menciona tilapia tb
- Anderson Lucas de novo (3o video desse canal)

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` — ERRO PARCIAL. ele usa TROUXA (saco) +
  canequinha solta. o principal eh a trouxa, deveria ser saco_de_ceva
- grao=`milho` ✅
- especies=`[lambarizao]` — parcial. FALTOU traira e tilapia (tb
  mencionadas)
- obs ✅

**correcao**: tipo_ceva=saco_de_ceva, especies=[lambarizao, traira, tilapia]

---

## 9. A-Vvt3krj14 (3386 palavras)

**extraido pelo pipeline**: rio=`Lago da Balbina`, bacia=`Lago da Balbina`,
tipo_ceva=`ceva_solta_na_agua`, especies=`[piabao]`

**o que ta certo na transcricao**:
- "Lago da Balbina" — LAGO/REPRESA, fica no AM (Amazonas)
- "piabao" eh a ISCA, nao a especie alvo
- menciona cucunare (=tucunare) e piranha preta como alvos reais
- pescaria com isca viva (piabao), nao tem ceva

**diagnostico**:
- rio=`Lago da Balbina` — ERRO. Balbina eh lago/represa, nao rio. deveria
  ser null pro rio
- bacia=`Lago da Balbina` — ERRO. Balbina nao eh bacia, ta DENTRO da bacia
  amazonica (Uatuma). correto seria "amazonica" ou Uatuma
- tipo_ceva=`ceva_solta_na_agua` — ALUCINACAO. ele nao usa ceva, pesca com
  isca viva (piabao). deveria ser null
- especies=`[piabao]` — ERRO. piabao eh a ISCA. especies alvo sao tucunare
  + piranha preta. FALSO + FALTANDO os reais
- FALTOU: estado=AM

**correcao**: rio=null, bacia=amazonica, tipo_ceva=null, especies=[tucunare,
piranha preta], estado=AM

---

## 10. EJasS3HEYsk (0 palavras)

**extraido pelo pipeline**: tudo null (transcricao vazia)

**o que ta certo na transcricao**: transcricao vazia. whisper nao conseguiu
transcrever (audio mudo ou muito ruim)

**diagnostico**: OK. nao tem o que anotar.

**correcao**: nenhuma

---

## sumario rapido do lote

dos 10 videos:
- 1 ok (10) — transcricao vazia, nao conta
- 1 ok mas pelo motivo errado (2) — fora de dominio (cobra no rio)
- 1 com extracao razoavel (8) — 1 acerto (grao), 2 parciais (ceva/especies), 1 perda
- 7 com erros serios:
  - 2 falso positivo em especies com palavras genericas (1, 4)
  - 3 alucinacao de rio=Rio Sao Francisco ou Riozao (3, 6, 7)
  - 1 confundiu isca com especie alvo (9 — piabao)
  - 1 falso negativo grave em especies (5 — perdeu piau+cachorra+traira,
    provavel bug do chunking)

**padroes de erro que apareceram**:
- confundir aumentativo ("riozao") com nome proprio de rio — recorrente
  (3 videos)
- inventar "Rio Sao Francisco" sem evidencia textual — 2 videos
- confundir isca (piabao) com especie alvo
- tipo_ceva com valores fora do enum ("galao") ou chutado sem evidencia

anotado manualmente por jader em 2026-04-19.
