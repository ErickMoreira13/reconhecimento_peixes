# lote 05 — videos 41-50

## 41. mpQyF-xusWw (43 palavras)

**extraido**: grao=`milho`, especies=`[piapara]`, obs boa
**transcricao**: "milho molhado um dia, quirela com sangue, pra piapara"
**diagnostico**: OK. video curto mas extrator acertou o essencial
- grao=`milho` ✅
- especies=`[piapara]` ✅
- obs util

---

## 42. nr05u17DzBE (0 palavras)
**extraido**: tudo null. transcricao vazia. OK

---

## 43. ou9XkgNpMPA (984 palavras)

**extraido**: rio=`Rio Sao Francisco`, bacia=`Bacia de Sao Francisco`,
tipo_ceva=`ceva_de_chao`, grao=`milho`, especies=`[pai tainha]`

**transcricao**: "pescaria de ceva num PEQUENO AFLUENTE da bacia de sao
francisco, um rio bastante estreito", "piau, pacuma, trincha",
"massinha de fuba e trigo, milho cozido, querela de milho, soja",
"peixe bom viu pai tainha" (chamada/saudacao)

**diagnostico**:
- rio=`Rio Sao Francisco` — ERRO. ele diz AFLUENTE da bacia. o rio em si
  nao eh nomeado. mas o extrator pulou pra Sao Francisco de novo
- bacia=`Bacia de Sao Francisco` ✅ (texto literal! um dos poucos casos
  em que bacia ta certa)
- tipo_ceva=`ceva_de_chao` — ERRO. eh MASSINHA (bola_de_massa) +
  milho cozido
- grao=`milho` ✅
- especies=`[pai tainha]` — ERRO CLASSICO. "pai tainha" eh como o
  pescador chama o companheiro ("peixe bom viu pai tainha" = "vem ver
  esse peixe parceiro"). nao eh especie. alvos reais: piau, pacuma
  (pacu), trincha, carainha, piau acu

**correcao**: rio=null, tipo_ceva=bola_de_massa,
especies=[piau, pacuma, trincha, carainha]

---

## 44. s1hg1HC1UkQ (6 palavras)
**extraido**: tudo null
**transcricao**: "so filapossauro, so filape bruta galera" (giria)
**diagnostico**: OK (curto + giria fora de qualquer dict)

---

## 45. sCQu7FSW3pc (6 palavras)
**extraido**: tudo null
**transcricao**: "tirando o file do tucunare amarelo"
**diagnostico**: OK tecnico (curto), mas PERDA de info. tinha TUCUNARE
amarelo explicito. se o threshold fosse menor pegava

---

## 46. uEVUMnSMcTI (1604 palavras)

**extraido**: tipo_ceva=`cano_pvc_perfurado`, grao=`milho`,
especies=`[piapara]`, obs ok

**transcricao**: "aula Segredos da Pesca... ceva pode ser pra Piapara,
Piau, Matrecha, Pira Canjuva, Pacu, Tambaqui... milho de molho 24h,
fervido 1h... cebador de cano de PVC com varios buraquinhos"

**diagnostico**: EXCELENTE extracao
- tipo_ceva=`cano_pvc_perfurado` ✅
- grao=`milho` ✅
- especies=`[piapara]` — parcial. eh uma AULA geral, todas as especies
  citadas sao possibilidades (nao pescadas concretas). pegar a primeira
  foi decisao razoavel
- obs ok

**correcao**: essencialmente certo. se quiser ser completista:
especies=[piapara, piau, matrecha, pira canjuva, pacu, tambaqui]

---

## 47. vhgon9C1-DA (2176 palavras)

**extraido**: especies=`[Mandube]`

**transcricao**: "mandube", "sardinhao", "pescada", "piranha",
"cascudinha"

**diagnostico**:
- especies=`[Mandube]` — parcial. pegou a primeira mencionada.
  FALTARAM: sardinhao, pescada, piranha, cascudinha
- resto null ta mais ok pq nao tem localizacao explicita no trecho

**correcao**: especies=[mandube, sardinhao, pescada, piranha,
cascudinha]

---

## 48. wl1X5jtLNbc (894 palavras)

**extraido**: rio=`Rio Canoas`, bacia=`Rio Canoas`,
tipo_ceva=`ceva_solta_na_agua`, grao=`milho`, especies=`[carpa]`

**transcricao**: "canal Serra Ficha", "Rio Canoas", "carpa capim",
"milho azedo, silagem, leite azedo, cachaca", "bolsinha amarrar no
fio jogar na agua"

**diagnostico**:
- rio=`Rio Canoas` ✅
- bacia=`Rio Canoas` — ERRO (bacia=rio, caso numero 5). Rio Canoas eh
  afluente do Uruguai. bacia correta=Uruguai
- tipo_ceva=`ceva_solta_na_agua` — PARCIAL. ele usa BOLSINHA amarrada
  no fio = saco_de_ceva. mas a bolsinha fica solta na agua, entao eh
  meio termo
- grao=`milho` ✅
- especies=`[carpa]` ✅ (carpa capim, especifico)

**correcao**: bacia=Uruguai, tipo_ceva=saco_de_ceva

---

## 49. wqO7XQQR8Pw (55 palavras)

**extraido**: bacia=`Piau Sul`, tipo_ceva=`ceva_solta_na_agua`,
especies=`[Piau]`

**transcricao**: "ceva top tres dias... isso eh ceva pra Piau Sul,
Piau, Piapara, top"

**diagnostico**:
- bacia=`Piau Sul` — ERRO ABSURDO. "Piau Sul" eh VARIEDADE/SUBESPECIE
  de piau (*Leporinus obtusidens*?), nao bacia hidrografica
- tipo_ceva=`ceva_solta_na_agua` — SUSPEITO, sem detalhe textual
- especies=`[Piau]` — parcial. FALTOU "Piau Sul" (variedade) e piapara

**correcao**: bacia=null, especies=[piau, piau sul, piapara]

---

## 50. xRURhakx4Mw (3155 palavras)

**extraido**: rio=`Jequitiba`, especies=`[bagre]`, obs="Pescaria raiz"

**transcricao**: "pescaria raiz", caminhada na mata com medo de onca,
"pegadas de onca", "pescaria de barranco", "almoco na beira" —
trecho lido fala quase so de onca, nao de peixe

**diagnostico**:
- rio=`Jequitiba` — SUSPEITO. Jequitiba eh nome de arvore da mata
  atlantica/cerrado. pode ser nome de rio tambem mas NAO vi mencao
  explicita no trecho. possivel alucinacao
- especies=`[bagre]` — nao vi mencao no trecho lido. pode estar no
  resto do texto
- obs=`Pescaria raiz` ✅ (texto literal)

**correcao**: precisa validar no texto completo se tem "Jequitiba" e
"bagre"

---

## sumario do lote

destaques:

- **video 46 (uEVUMnSMcTI)** = melhor extracao completa de ceva em todo
  o dataset. cano_pvc_perfurado + milho + piapara + obs util. extrator
  foi bem em aula didatica estruturada
- **video 43 (ou9XkgNpMPA)** = outro Sao Francisco, mas so a bacia esta
  certa. o rio foi alucinado de novo (texto diz explicitamente
  "afluente", nao o Sao Francisco)
- **"pai tainha"** como especie eh novo tipo de erro: gíria de saudacao
  ("vem ver pai tainha") foi confundida com nome de peixe
- **"Piau Sul"** como bacia (video 49) eh erro novo: variedade de
  peixe virou bacia hidrografica
- videos 44/45 mostram outro padrao: textos muito curtos com
  girai/info pontual (tucunare amarelo) sao pulados pelo threshold,
  perdendo info util

## padroes acumulados TODOS os 5 lotes

1. **bias "Rio Sao Francisco"**: 7 ocorrencias no total, das quais 2
   sao legitimas (videos 32 + 43 parcial). 5 sao alucinacao pura
2. **tipo_ceva=ceva_solta_na_agua como default**: 25+ ocorrencias, maioria
   errada quando o video nao usa ceva
3. **isca confundida com especie**: piau (x3), camarao (x2), piabao,
   lambari, piranha — 7+ videos
4. **bacia=nome do rio**: videos 9, 18, 28, 34, 37, 48 = 6 casos
5. **palavras genericas/gírias viram especie**: bonito, paca (x3),
   cimprao, ceba, escar-viva, peixe bonito, peixe grande, pai tainha,
   piau sul — 10+ casos
6. **equipamento vira ceva**: vara de bambu, Hunter Bait (isca), Avenado
   GS (carretilha) — 3 casos graves
7. **bug do chunking em textos >4500 palavras**: videos 17, 20, 35, 38
   perdem sinal sistematicamente
8. **threshold de palavras minimas**: videos 45 (tucunare amarelo
   explicito) perdidos por serem curtos
9. **campo estado RARO**: dos 50 videos, so 4 tiveram estado extraido
   (PA, SP, RO implicito, outro). muitos videos mencionam UF mas nao
   pega

anotado por jader, 2026-04-19.
