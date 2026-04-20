# sumario das anotacoes manuais (50 videos)

revisei os 50 videos em 5 lotes (lote-01 a lote-05). esse doc consolida
os padroes de erro mais fortes e aponta o que dar pra consertar sem muito
esforco.

## contagem por tipo de erro

| tipo de erro | qtd | % videos |
|--------------|-----|----------|
| tipo_ceva=ceva_solta_na_agua errado (default) | 25+ | 50% |
| palavra generica/giria virando especie | 10+ | 20% |
| isca confundida com especie alvo | 7 | 14% |
| bacia=mesmo nome do rio | 6 | 12% |
| "Rio Sao Francisco" alucinado | 5 | 10% |
| bug chunking em texto >4500 palavras | 4 | 8% |
| equipamento virando ceva | 3 | 6% |
| "paca" (mamifero) virando peixe | 3 | 6% |
| threshold de palavras pula video bom | 2 | 4% |
| outros rios famosos alucinados | 3 | 6% |

videos que sairam bem (extracao aproveitavel sem grande correcao):

- **video 21** (SzceiuMllLA): Fernandopolis + Rio Grande + Tucunare
- **video 32** (bdKr7GC3Q_w): Entrevazante + Rio Escurao + Sao Francisco
- **video 46** (uEVUMnSMcTI): cano_pvc_perfurado + milho + piapara
- **video 41** (mpQyF-xusWw): grao=milho + especies=piapara (curto)
- **video 19** (SYYey9_vJr4): tipo_ceva=ceva_solta_na_agua correto

so ~5 dos 50 (10%) sao aproveitaveis quase sem correcao. 45 precisam
de ajuste em pelo menos 1 campo.

## padroes consolidados (por ordem de impacto)

### 1. tipo_ceva=ceva_solta_na_agua como DEFAULT errado

metade dos videos vem com esse valor. muitos deles sao videos SEM ceva
(pesca com isca viva, isca artificial, espinhel, etc). o llama ta
chutando esse valor quando nao sabe.

**fix possivel**: ajustar o prompt pra exigir evidencia textual literal
("ceva" ou variantes: ceba, seva, cevar) antes de preencher tipo_ceva.
sem evidencia -> null.

### 2. alucinacao de rios famosos

"Rio Sao Francisco" (5 alucinados + 2 certos), "Rio Araguaia" (1
alucinado), "Rio Negro" (1 pode ser certo). o modelo tem vies forte
em rios grandes brasileiros.

**fix possivel**: exigir que o rio apareca LITERALMENTE na transcricao.
adicionar ao verificador uma checagem: se rio nao aparece como substring
(case-insensitive, sem acento), rejeita por `evidencia_nao_alinha`.

### 3. isca vs especie alvo

piau-flamengo, camarao, piabao, lambari viram "especies" quando sao
ISCAS. o prompt nao distingue "peixe usado como isca" de "peixe que foi
pescado".

**fix possivel**: no prompt, deixar claro: "especies = o que foi PEGO
pelo pescador, NAO o que foi usado como isca". exemplos especificos
("camarao e geralmente isca, nao especie alvo").

### 4. bacia = mesmo nome do rio

6 videos com bacia igual ao rio (ex: Rio Canoas / Rio Canoas, Rio Bonito
/ Rio Bonito). o extrator nao entende que bacia eh um agrupamento maior
de rios.

**fix possivel**: dicionario de bacias (Amazonica, Sao Francisco,
Tocantins-Araguaia, Parana, Paraiba do Sul, Uruguai) + regra: bacia
deve aparecer na lista. se rio nao tem evidencia de bacia, bacia=null.

### 5. gírias e palavras genericas como especie

exemplos: "bonito" (adjetivo), "paca" (exclamacao), "cimprao" (girai
de companheiro), "pai tainha" (saudacao), "ceba" (ceva mal transcrita),
"escar-viva" (isca viva mal transcrita), "peixe grande" (generico),
"peixe bonito" (generico), "piau sul" (variedade).

**fix possivel**:
- regra POS-tag: se token eh vocativo/adjetivo/expressao no contexto,
  rejeita
- verificador tem que comparar com gazetteer `peixes_conhecidos.json`.
  se nao casa nem por fuzzy, flag `fora_do_gazetteer=true` E marca pra
  revisao manual
- filtros literal: rejeitar se valor em stop_words ["pai","mae","bonito",
  "grande","bicho","peixe","especie"]

### 6. bug do chunking em textos grandes

videos de 5k+ palavras (17, 20, 35, 38) perdem TUDO. todos os campos
vem null. suspeita: o consolida_chunks descarta campo quando chunks
divergem ou tem conflito.

**fix possivel**: ler o codigo de `_consolida_chunks` em
`src/extracao/qwen_extrator.py`. provavel: a regra de consolidacao ta
muito restritiva. deveria ser: valor que aparece em >=1 chunk ganha
(nao precisa de consenso).

### 7. equipamento confundido com ceva

- video 27: `tipo_ceva=Isquinha Hunter Bait` (eh uma isca artificial)
- video 27: `grao=avenado` (modelo de carretilha)
- video 35: `tipo_ceva=vara de bambu` (equipamento)

**fix possivel**: blacklist simples de termos de equipamento no
verificador: se tipo_ceva contem "vara", "carretilha", "bait", "isca",
"linha", "anzol", "molinete" — rejeita.

### 8. faltou campo estado

so 4 de 50 videos tiveram estado preenchido. varios videos mencionam
UF explicitamente (Sao Paulo video 21, Pará video 28, mineiro video 32,
interior paulista video 15) mas so o 28 pegou. o prompt lista o enum
mas o modelo nao relaciona nome completo com sigla UF.

**fix possivel**: prompt especificar "se o texto menciona 'Sao Paulo'
preencha estado=SP, se menciona 'Minas Gerais' ou 'mineiro' -> MG".
mapeamento explicito.

## recomendacoes de fix rankeadas por ROI

| # | fix | esforco | impacto | **status** |
|---|-----|---------|---------|------------|
| 1 | exigir evidencia literal no rio (verificador)  | baixo | alto | ✅ feito (fix 2) |
| 2 | prompt: ceva precisa de evidencia textual | baixo | alto | ✅ feito (fix 1) |
| 3 | stop-words pra especies genericas | baixo | medio-alto | ✅ feito (fix 4) |
| 4 | dicionario fechado de bacias BR + validacao | medio | medio | ✅ feito (fix 7) |
| 5 | prompt: isca vs especie alvo | baixo | alto | ✅ feito (fix 5) |
| 6 | blacklist equipamento pra tipo_ceva | baixo | medio | ✅ feito (fix 3) |
| 7 | investigar bug do consolida_chunks | medio | alto | ✅ feito (fix 8) |
| 8 | mapeamento nome UF -> sigla no prompt | baixo | medio | ✅ feito (fix 6) |

**todos os 8 fixes aplicados em 2026-04-19**. ver consolidacao em
[../fixes-aplicados-2026-04-19.md](../fixes-aplicados-2026-04-19.md).

## proxima acao

~~fazer PRs pequenos, um por fix~~ **concluido em 2026-04-19**.

proximo passo eh validar empiricamente quando a GPU estiver livre:

```bash
.venv/bin/python scripts/testar-retry-schema.py --limit 50
```

compara com as contagens deste sumario pra ver se taxa de erro caiu.
tabela de expectativas em [fixes-aplicados-2026-04-19.md](../fixes-aplicados-2026-04-19.md).

anotado por jader, 2026-04-19.
