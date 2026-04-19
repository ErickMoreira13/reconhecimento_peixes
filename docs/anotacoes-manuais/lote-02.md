# lote 02 — videos 11-20

## 11. F6AcoBAAsXI (503 palavras)

**extraido**: tipo_ceva=`ceva_solta_na_agua`, grao=`milho`, especies=`[tilapia]`

**transcricao**: "massinha que eu fiz", "grao de milho", "so no milho",
"tilapia gigante", "carazao na massinha"

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` — ERRO. ele usa MASSINHA (pelotas de
  massa). deveria ser `bola_de_massa`
- grao=`milho` ✅
- especies=`[tilapia]` ✅ (cara tb aparece mas passa batido)

**correcao**: tipo_ceva=bola_de_massa

---

## 12. Fr0IvypLlsU (129 palavras)

**extraido**: tipo_ceva=`ceva_solta_na_agua`, grao=`arroz`,
especies=`[tilapia]`

**transcricao**: "ceva de racao em pelotas pra tilapia. racao de coelho,
farelo de arroz, racao de peixe, leite vencido"

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` — ERRO. sao PELOTAS (bola_de_massa)
- grao=`arroz` — parcial. tem farelo de arroz sim, mas o principal eh
  RACAO DE COELHO + racao de peixe. o campo "grao" como esta nao aguenta
  multi-ingrediente
- especies=`[tilapia]` ✅
- obs vazia — FALTOU: os ingredientes sao a receita, perfeito pra obs

**correcao**: tipo_ceva=bola_de_massa, grao=arroz+racao (ou deixar livre)

---

## 13. GI9l523Qt3I (787 palavras)

**extraido**: tipo_ceva=`ceva_solta_na_agua`, especies=`[escar-viva]`

**transcricao**: "isca escar-viva, sardinha, peixinhos vivos", "cascudinho",
"traira"

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` — ERRO. pescaria com isca viva, sem ceva
- especies=`[escar-viva]` — ERRO GRAVE. "escar-viva" eh a ISCA. e nem eh
  nome de especie, eh uma descricao de "isca viva" mal transcrita pelo
  whisper (provavelmente "isca viva" virou "escar-viva"). alvo real:
  cascudinho, traira

**correcao**: tipo_ceva=null, especies=[cascudinho, traira]

---

## 14. GV_FY3MM_IA (1771 palavras)

**extraido**: rio=`Rio Sao Francisco`, tipo_ceva=`ceva_solta_na_agua`,
especies=`[Piau]`

**transcricao**: "canal Pescadora Amazonica", "inverno amazonico",
"Amazonia", "piau Flamengo cortar rodelas" (isca), "cachara"

**diagnostico**:
- rio=`Rio Sao Francisco` — ALUCINACAO PESADA. o contexto inteiro eh
  AMAZONIA, oposto total. MESMO padrao do lote 1 (videos 6 e 7). o extrator
  tem um vies forte pra "Rio Sao Francisco" quando nao sabe
- tipo_ceva=`ceva_solta_na_agua` — ERRO. usa piau como ISCA, nao ceva
- especies=`[Piau]` — ERRO. piau eh a isca (cortada em rodelas!). o peixe
  alvo que ela PEGOU eh CACHARA
- FALTOU: bacia=amazonica

**correcao**: rio=null, bacia=amazonica, tipo_ceva=null, especies=[cachara]

---

## 15. GmLxYVSMnAw (1900 palavras)

**extraido**: rio=`Rio Sao Francisco`, tipo_ceva=`ceva_solta_na_agua`,
especies=`[camarao]`

**transcricao**: "interior paulista", "camarao de isca",
"tucunare, porquinho, curvina, tilapia, piau"

**diagnostico**:
- rio=`Rio Sao Francisco` — ALUCINACAO de novo. ele diz INTERIOR PAULISTA
- tipo_ceva=`ceva_solta_na_agua` — ERRO. sem ceva, isca de camarao
- especies=`[camarao]` — ERRO. camarao eh ISCA. alvos: tucunare, curvina,
  tilapia, piau (ele lista explicitamente "essa isca pega tucunare,
  porquinho, curvina, tilapia, piau")
- FALTOU: estado=SP (interior paulista)

**correcao**: rio=null, estado=SP, tipo_ceva=null,
especies=[tucunare, porquinho, curvina, tilapia, piau]

---

## 16. KpPYnnbw7-8 (529 palavras)

**extraido**: tipo_ceva=`ceva_solta_na_agua`, especies=`[traira]`

**transcricao**: "traira pequena", "traira bruta", "garrota", "lambarizinho
escado" (isca), "calanguinho"

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` — ERRO. ele usa LAMBARI COMO ISCA VIVA
  (escado = vivo). sem ceva
- especies=`[traira]` — parcial. pegou traira OK, mas perdeu "garrota"
  (peixe galo da regiao?)
- "calanguinho" provavelmente eh "lambarizinho" mal transcrito pelo whisper

**correcao**: tipo_ceva=null, especies=[traira, garrota]

---

## 17. L450LUqSYJw (8982 palavras — monstro)

**extraido**: tudo null, especies=`[]`

**transcricao**: "Amazonia, peixe mais desejado Tucunare", "Rio Negro",
"Santa Isabel do Rio Negro", "Manaus", "temporada 2024-2025"

**diagnostico**:
- ERRO GRAVISSIMO. esse video eh um tutorial de preparacao pra pescaria
  no Rio Negro. tem TUDO explicito:
  - rio=Rio Negro ✅ (alvo)
  - municipio=Santa Isabel do Rio Negro
  - estado=AM
  - especies=tucunare
  - bacia=amazonica
- tudo null em vez disso. eh falha do CHUNKING em texto de 8982 palavras
  (passou dos 4500 do threshold). o _consolida_chunks ta perdendo sinal
  em textos muito grandes

**correcao**: rio=Rio Negro, municipio=Santa Isabel do Rio Negro,
estado=AM, especies=[tucunare], bacia=amazonica. **bug pra investigar:
consolidador de chunks descartando campos bons**

---

## 18. L7blIPNXbs0 (619 palavras)

**extraido**: rio=`Rio Sao Francisco`, bacia=`Piracema`,
tipo_ceva=`ceva_solta_na_agua`, grao=`arroz`, especies=`[Tilapia selvagem]`

**transcricao**: "represa do tablado", "piracema chegou" (= epoca de
desova, fechou pesca no rio), "farelo de arroz, milho azedo, milhao como
isca", "tilapia selvagem", "cara"

**diagnostico**:
- rio=`Rio Sao Francisco` — ALUCINACAO (3a vez neste lote). ele ta numa
  REPRESA chamada "tablado"
- bacia=`Piracema` — ERRO GRAVE. PIRACEMA NAO EH BACIA, eh o periodo de
  reproducao dos peixes. o extrator nao conhece o termo e inventou
- tipo_ceva=`ceva_solta_na_agua` — ERRO. ele faz BOLAS/PELOTAS de massa
  (bola_de_massa)
- grao=`arroz` — parcial. tem farelo de arroz + milho azedo
- especies=`[Tilapia selvagem]` ✅ (adiciona "cara" tb)

**correcao**: rio=null, bacia=null, tipo_ceva=bola_de_massa,
especies=[tilapia, cara]

---

## 19. SYYey9_vJr4 (56 palavras — curto)

**extraido**: tipo_ceva=`ceva_solta_na_agua`, especies=[]

**transcricao**: "pescador de ceva", "cevador assim mais aberto",
"solta dois, tres cevadores"

**diagnostico**:
- tipo_ceva=`ceva_solta_na_agua` ✅ (ele literalmente fala de CEVADOR
  aberto solto na agua)
- resto null ok (texto muito curto, nao da pra extrair mais)

**correcao**: nenhuma, esse acertou

---

## 20. SaYc56i-OTk (10366 palavras — mega)

**extraido**: tipo_ceva=`garrafa_pet_perfurada`, especies=[], obs null

**transcricao** (so li 2500 chars): conversa familiar, crianca brincando
("quem eh mais bonito"), castanhas, comida. NAO parece video de pescaria
pelo inicio. provavelmente eh video de vlog de comunidade ribeirinha com
trechos de pescaria misturados

**diagnostico**:
- sem poder ver tudo, confio no que extraiu mas com reservas
- tipo_ceva=`garrafa_pet_perfurada` — SUSPEITO. pode aparecer no texto
  completo. em 10k palavras, provavel
- especies=[] — em 10k palavras e sendo um video pelo menos parcialmente de
  pescaria, ESTRANHO zerar. de novo chunking em texto monstro
- video de dominio parcial (vlog de comunidade com pescaria)

**correcao**: precisa de revisao completa do texto inteiro. por agora,
marco como "video com chunking problematico". MESMO BUG do video 17

---

## sumario do lote

10 videos, principais achados:

- **"Rio Sao Francisco" alucinacao** aparece em MAIS 3 videos (14, 15, 18)
  — total no lote 1+2: 5 videos. eh vies sistematico
- **piracema confundida com bacia** (18) — extrator nao entende o termo e
  chuta
- **isca confundida com especie alvo** apareceu mais vezes: video 14
  (piau), 15 (camarao), 13 (escar-viva)
- **tipo_ceva=ceva_solta_na_agua** eh o default quando extrator nao sabe
  — deveria ser null. apareceu em 6 videos desse lote, sendo errado em 5
- **textos gigantes (>4500 palavras)** perdem TUDO no chunking (videos 17
  e 20). bug real do consolida_chunks
- 1 acerto completo (19)

padroes novos pra anotar:

1. bias forte em "Rio Sao Francisco" — investigar se eh do treino do
   llama3.1 ou do prompt que enviesa
2. "escar-viva" como alucinacao — whisper provavelmente transcreveu
   "isca viva" como "escar-viva" e o extrator pegou o erro do asr
3. bug do chunking em textos monstros (>4500 palavras)
4. tipo_ceva padrao errado pra `ceva_solta_na_agua`

anotado por jader, 2026-04-19.
