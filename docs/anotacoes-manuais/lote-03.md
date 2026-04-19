# lote 03 — videos 21-30

## 21. SzceiuMllLA (2521 palavras)

**extraido**: municipio=`Fernandopolis`, rio=`Rio Grande`,
especies=`[Tucunare]`

**transcricao**: "cidade de Fernandopolis, Sao Paulo", "pescar no Rio
Grande"

**diagnostico**: MELHOR EXTRACAO ATE AGORA
- municipio=`Fernandopolis` ✅
- rio=`Rio Grande` ✅
- especies=`[Tucunare]` ✅
- FALTOU: estado=SP (ele menciona explicitamente "Fernandopolis, Sao Paulo"
  mas o extrator so pegou o municipio — falha no cross-field SP↔SP)

**correcao**: estado=SP (mas bem proximo do ideal, so faltou inferir UF
a partir de "Sao Paulo" no texto)

---

## 22. T1xHA1ONgYw (5403 palavras)

**extraido**: rio=`Rio Araguaia`, tipo_ceva=`ceva_solta_na_agua`,
especies=`[piranha]`

**transcricao**: "vamos pescar", "dona juvani gosta de piranha gosta de
surubim e ai eh pra trazer", "vamos la pescar"

**diagnostico**:
- rio=`Rio Araguaia` — SUSPEITA DE ALUCINACAO. no trecho que li (2500
  chars) nao fala Araguaia. mais um caso do padrao "extrator inventa rio
  grande conhecido quando nao sabe"
- tipo_ceva=`ceva_solta_na_agua` — ERRO. sem mencao a ceva
- especies=`[piranha]` — parcial. menciona surubim tb ("gosta de piranha
  gosta de surubim")

**correcao**: rio=null (menos que confirme Araguaia no texto completo),
tipo_ceva=null, especies=[piranha, surubim]

---

## 23. TcxPSdqeP1E (36 palavras)

**extraido**: tudo null

**transcricao**: 36 palavras, video curto de "olha o peixe que escapou".
nao tem conteudo extraivel

**diagnostico**: OK. pulou corretamente.

---

## 24. VZ_n0XWOP54 (5650 palavras)

**extraido**: estado=`Sao Paulo`, especies=`[cimprao]`

**transcricao**: "rio Taquari", "Borretiro/Borretiro do Sul", "mandinhos
de respeito em cima da grelha", "meu cimprao" (girai de companheiro)

**diagnostico**:
- estado=`Sao Paulo` — ALUCINACAO. Rio Taquari + Borretiro do Sul eh
  provavelmente Rio Grande do Sul (tem cidade Bom Retiro do Sul/RS) ou
  Mato Grosso do Sul
- especies=`[cimprao]` — ERRO GRAVE. "cimprao" eh girai de "companheiro"
  usada varias vezes no video ("meu cimprao"). o PEIXE que ele cita eh
  MANDI ("mandinhos na grelha")
- FALTOU: rio=Rio Taquari, municipio=Bom Retiro do Sul (ou similar),
  especies=[mandi]

**correcao**: estado=RS, rio=Rio Taquari, municipio=Bom Retiro do Sul,
especies=[mandi], nao=cimprao

---

## 25. VZkXv5_BFKk (1761 palavras)

**extraido**: rio=`Igapo`, bacia=`Lago do Anzol`,
tipo_ceva=`ceva_solta_na_agua`, especies=`[peixe bonito]`

**transcricao**: "vou pro Igapo", "passar pelo Lago do Anzol", "botar uns
espinhel"

**diagnostico**:
- rio=`Igapo` — ERRO. IGAPO eh tipo de floresta alagada da Amazonia, nao
  nome de rio. substantivo comum, nao proprio
- bacia=`Lago do Anzol` — ERRO. Lago do Anzol eh corpo d'agua, nao bacia
- tipo_ceva=`ceva_solta_na_agua` — ERRO. ele usa ESPINHEL (linha com
  varios anzois, tipo de pesca passiva), nao ceva
- especies=`[peixe bonito]` — FALSO POSITIVO generico. pode ser adjetivo

**correcao**: rio=null, bacia=amazonica (se eh igapo, contexto
amazonico), tipo_ceva=null, especies=[]

---

## 26. XVLIgkdvWxA (1058 palavras)

**extraido**: rio=`Rio Negro`, bacia=`Amazonia`,
tipo_ceva=`ceva_solta_na_agua`, especies=`[paca]`

**transcricao**: "chuva na Amazonia", "pegou um acu", "olha os tucunares",
"que monstro" (peixe grande)

**diagnostico**:
- rio=`Rio Negro` — SUSPEITO mas razoavel pelo contexto amazonico. nao
  achei mencao explicita
- bacia=`Amazonia` ✅ (menciona "Amazonia" direto)
- tipo_ceva=`ceva_solta_na_agua` — ERRO. pesca com ISCA (natural ou
  artificial), sem ceva
- especies=`[paca]` — ERRO. "um paca" aqui eh exclamacao regional tipo
  "um baita peixe". as especies REAIS mencionadas sao ACU (pirarucu?) e
  TUCUNARE

**correcao**: tipo_ceva=null, especies=[tucunare, acu/pirarucu]

---

## 27. XZI5fBhsrLA (533 palavras)

**extraido**: tipo_ceva=`Isquinha Hunter Bait`, grao=`avenado`,
especies=`[tucunare]`

**transcricao**: "Isquinha Hunter Bait" (nome comercial de isca
artificial), "carretilha Avenado GS", "tucunare", "traira"

**diagnostico**: PROBLEMA CLASSIFICATORIO GRAVE
- tipo_ceva=`Isquinha Hunter Bait` — ERRO ABSURDO. isso eh NOME
  COMERCIAL de isca artificial (stick bait). nao eh ceva. ele nem usa
  ceva, usa isca de superficie
- grao=`avenado` — ERRO MAIS ABSURDO AINDA. "Avenado GS" eh modelo de
  CARRETILHA. extrator misturou material de pesca com insumo de ceva
- especies=`[tucunare]` ✅ (e tem traira tb, FALTOU)

**correcao**: tipo_ceva=null, grao=null,
especies=[tucunare, traira]

---

## 28. YcCP4cvTS3I (2144 palavras)

**extraido**: estado=`PA`, rio=`Rio Bonito`, bacia=`Rio Bonito`,
tipo_ceva=`ceva_de_chao`, grao=`milho`, especies=`[piau flamengo]`

**transcricao**: "estado do Para", "Rio Bonito", "tambor com soja ou
milho", "jogo a agua azeda no poco pra chamar os peixes", "piau flamengo",
"chimbore", "caracu piau", "piranha", "pacu"

**diagnostico**: EXTRACAO BOA mas com erros finos
- estado=`PA` ✅
- rio=`Rio Bonito` ✅
- bacia=`Rio Bonito` — ERRO. Rio Bonito eh RIO, nao bacia. bacia correta
  seria Tocantins-Araguaia ou similar
- tipo_ceva=`ceva_de_chao` — PARCIAL. ele joga milho direto no poco (agua)
  + agua azeda. mais proximo de "ceva_solta_na_agua" misturado com
  ceva_de_chao (ele usa os dois termos)
- grao=`milho` ✅ (soja tb como alternativa)
- especies=`[piau flamengo]` — parcial. pegou a principal mas FALTARAM
  chimbore, caracu piau, piranha, pacu

**correcao**: bacia=null ou tocantins-araguaia,
especies=[piau flamengo, chimbore, caracu, pacu]

---

## 29. ZMFOZdRijtM (0 palavras)

**extraido**: tudo null

**transcricao**: vazia. whisper nao transcreveu (audio ruim ou mudo).

**diagnostico**: OK.

---

## 30. _gIUFBsrEL0 (3045 palavras)

**extraido**: tipo_ceva=`ceva_solta_na_agua`, especies=`[matrincha]`

**transcricao**: "canal Pescadora Amazonica", "isca: pedaco de carne",
"matrincha", "piranha", "mandizinho", "peixe de couro"

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` — ERRO. ela usa CARNE como isca, sem
  ceva
- especies=`[matrincha]` — parcial. menciona piranha, mandi tb
- FALTOU: bacia=amazonica (contexto explicito), estado provavel AM,
  peixe de couro (termo generico pra surubim/pintado/cachara)

**correcao**: tipo_ceva=null, especies=[matrincha, piranha, mandi],
bacia=amazonica

---

## sumario do lote

destaques:

- **melhor extracao ate agora (video 21)**: municipio+rio+especie todos
  certos. mas falhou em inferir UF de "Sao Paulo" mencionado
- **pior extracao tecnica (video 27)**: classificou MODELO DE CARRETILHA
  como grao. total desconexao de dominio
- **novo padrao de alucinacao (video 22)**: "Rio Araguaia" aparece sem
  evidencia textual. somado ao "Rio Sao Francisco" do lote 1+2, parece
  que o extrator tem um conjunto de rios "default" que escolhe aleatorio
  quando nao sabe
- **"cimprao" (video 24)**: girai confundida com especie. similar ao
  "bonito" do lote 1 e "escar-viva" do lote 2 — o extrator as vezes
  pega palavras que soam como peixe mas nao sao
- **regionalismos pegaram o extrator**: "igapo" (25) como rio proprio,
  "paca" (26) como especie, "cimprao" (24) como peixe — falta
  conhecimento de contexto pt-br

**padroes acumulados (lotes 1+2+3)**:
1. bias em rios famosos: Rio Sao Francisco (5x) + Rio Araguaia (1x) +
   Rio Negro (1x) + Rio Grande (1x) — dos quais so 2 parecem certos
2. bias em `tipo_ceva=ceva_solta_na_agua` como default quando nao sabe —
   15+ ocorrencias erradas
3. bacia do mesmo nome do rio em video 28 — confunde rio com bacia
4. falsos positivos de especies com palavras genericas/girais: bonito,
   peixe grande, cimprao, paca, escar-viva, peixe bonito

anotado por jader, 2026-04-19.
