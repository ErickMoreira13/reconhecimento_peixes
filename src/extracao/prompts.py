import json
from pathlib import Path

from src import config


# prompt do extrator qwen
# filosofia central: VOCABULARIO ABERTO.
# se o modelo encontrar algo que nao ta nos dicts, retorna o valor bruto do texto
# os dicts so servem pra canonizar (ex: "velho chico" -> "Rio Sao Francisco")
#
# saida em JSON com 8 campos, cada um com valor/confianca/evidencia/fora_do_gazetteer


DICTS_DIR = Path(__file__).parent.parent / "dicts"


def _carrega_dict(nome: str) -> dict:
    with open(DICTS_DIR / nome, encoding="utf-8") as f:
        return json.load(f)


def _top_peixes_por_bm25(texto: str, k: int = 20) -> list[str]:
    # retorna os top-k nomes canonicos mais parecidos com o texto, por bm25 simples
    # (bm25 de biblioteca seria melhor mas pra comecar uso soup-match por tokens em comum)
    # TODO trocar pra rank_bm25 ou similar se a qualidade ficar ruim
    d = _carrega_dict("peixes_conhecidos.json")
    nomes = d.get("nomes_comuns_peixes", [])

    texto_lower = texto.lower()
    scored = []
    for n in nomes:
        if n.lower() in texto_lower:
            # match direto = score maximo
            scored.append((n, 999))
            continue
        # fallback: quantas palavras do nome aparecem no texto
        tokens = n.lower().split()
        score = sum(1 for t in tokens if t in texto_lower)
        if score > 0:
            scored.append((n, score))

    scored.sort(key=lambda x: -x[1])
    return [n for n, _ in scored[:k]]


def monta_prompt_extrator(
    transcricao: str,
    spans_gliner: dict[str, list[dict]],
) -> str:
    # carrega exemplos dos dicts pra passar como contexto
    cevas = _carrega_dict("cevas.json")["categorias"]
    graos = _carrega_dict("graos.json")["graos"]
    ufs = _carrega_dict("estados.json")["ufs"]
    top_peixes = _top_peixes_por_bm25(transcricao, k=20)

    # spans crus do gliner (peixes + bacias candidatos)
    peixes_ner = [s["text"] for s in spans_gliner.get("peixe", [])]
    bacias_ner = [s["text"] for s in spans_gliner.get("bacia hidrografica", [])]

    # monta exemplos de ceva (nome canonico + gírias)
    cevas_desc = []
    for cat, vars_ in cevas.items():
        cevas_desc.append(f"- {cat}: variacoes tipo {', '.join(vars_[:3])}")
    cevas_block = "\n".join(cevas_desc)

    # graos exemplos
    graos_desc = []
    for g, vars_ in graos.items():
        graos_desc.append(f"- {g}: {', '.join(vars_)}")
    graos_block = "\n".join(graos_desc)

    # lista ufs
    ufs_siglas = ", ".join(u["sigla"] for u in ufs)

    prompt = f"""Voce eh um analista especialista em pesca esportiva brasileira.

Leia a transcricao abaixo e extraia 8 campos em formato JSON.

REGRA CENTRAL — VOCABULARIO ABERTO:
- se o texto menciona algo (peixe, bacia, rio, ceva, grao) que NAO esta nos exemplos abaixo, RETORNE O VALOR BRUTO DO TEXTO mesmo assim
- os exemplos servem SO pra canonizar (ex: "velho chico" -> "Rio Sao Francisco", "tucunazao" -> "tucunare-acu")
- se nao for parecido com nenhum exemplo, use o valor literal do texto
- marque "fora_do_gazetteer": true quando o valor NAO casa com os exemplos
- se o campo nao foi mencionado, use null

CAMPOS:

1. estado (UF brasileira) — LISTA FECHADA de 27 UFs (essa eh unica excecao):
{ufs_siglas}
   Deduza pelo municipio ou rio se nao for citada direto. Se ambiguo, null.

2. municipio — string LIVRE, capture o nome mencionado (ex: "Porto Velho", "Caceres").
   Se nao foi citado, null.

3. rio — string LIVRE com prefixo "Rio " (ex: "Rio Madeira").
   Normalize: "velho chico" -> "Rio Sao Francisco".
   Se nao foi citado, null.

4. bacia — string LIVRE. Exemplos de candidatos (NAO eh lista fechada):
   Bacia Amazonica, Bacia do Parana, Bacia do Sao Francisco, Bacia Tocantins-Araguaia,
   Bacia do Paraguai, Bacia do Uruguai, outras possiveis.
   Extraido por NER, candidatos: {bacias_ner or "nenhum"}
   Se nao foi citada, null.

5. tipo_ceva — string. Tenta canonizar em:
{cevas_block}
   Se mencionar ceva diferente (ex: "gororoba de farelo e sardinha"), RETORNE O TEXTO LIVRE.
   Se nao foi citada, null.

6. grao — string. Exemplos:
{graos_block}
   Se mencionar grao diferente (amendoim, milhete, etc), RETORNE O TEXTO LIVRE.
   Se nao foi citado, null.

7. especies — LISTA de strings. Nomes canonicos de peixes mencionados.
   NER candidatos: {peixes_ner or "nenhum"}
   Top-20 canonicos similares pra ajudar (NAO eh lista fechada): {top_peixes}
   Girias: "tucunazao" -> "tucunare-acu", "pirambeba" -> "piranha-vermelha" (quando contexto permitir).
   Se mencionar especie nao listada, USE O TEXTO LIVRE (ex: "piabanha", "mapara").
   Se nenhuma citada, [].

8. observacoes — resumo em 1-2 frases de coisas NAO capturadas nos campos acima:
   horario/periodo, clima, comportamento dos peixes, resultado, dicas, etc.
   Entre 20 e 80 palavras.
   Cite pelo menos 1 entidade real da transcricao pra nao alucinar.
   Se nada relevante alem dos campos, retorne "Sem observacoes adicionais relevantes."

FORMATO DE SAIDA (JSON estrito):
{{
  "estado": {{"valor": "<sigla UF ou null>", "confianca": <0-1>, "evidencia": "<trecho literal>", "fora_do_gazetteer": false}},
  "municipio": {{"valor": "<nome ou null>", "confianca": <0-1>, "evidencia": "<trecho>", "fora_do_gazetteer": <bool>}},
  "rio": {{"valor": "<Rio X ou null>", "confianca": <0-1>, "evidencia": "<trecho>", "fora_do_gazetteer": <bool>}},
  "bacia": {{"valor": "<bacia ou null>", "confianca": <0-1>, "evidencia": "<trecho>", "fora_do_gazetteer": <bool>}},
  "tipo_ceva": {{"valor": "<categoria canonica OU texto livre OU null>", "confianca": <0-1>, "evidencia": "<trecho>", "fora_do_gazetteer": <bool>}},
  "grao": {{"valor": "<grao ou null>", "confianca": <0-1>, "evidencia": "<trecho>", "fora_do_gazetteer": <bool>}},
  "especies": {{"valor": [{{"nome": "<especie>", "evidencia": "<trecho>", "fora_do_gazetteer": <bool>}}], "confianca": <0-1>}},
  "observacoes": {{"valor": "<texto 1-2 frases ou 'Sem observacoes adicionais relevantes.'>", "confianca": <0-1>, "evidencia": "<trecho>"}}
}}

Regra dura: NUNCA inventar valor que nao aparece no texto. Evidencia deve ser trecho LITERAL.
Responda APENAS o JSON.

TRANSCRICAO:
\"\"\"
{transcricao}
\"\"\"
"""
    return prompt
