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
    # carrega exemplos mas deixa o prompt curto pra nao explodir o prefill do qwen
    peixes_ner = [s["text"] for s in spans_gliner.get("peixe", [])][:10]
    bacias_ner = [s["text"] for s in spans_gliner.get("bacia hidrografica", [])][:5]

    # hint curtinho dos top peixes no texto (pra canonizar girias)
    top_peixes = _top_peixes_por_bm25(transcricao, k=10)

    prompt = f"""Analise a transcricao de um video de pescaria brasileira e extraia 8 campos em JSON.

REGRA: vocabulario aberto. Se o texto menciona algo fora dos exemplos, retorne o valor bruto. Marque fora_do_gazetteer=true quando nao casar com exemplos. Se nao mencionado, null.

CAMPOS:
1. estado: sigla UF (AC,AL,AM,AP,BA,CE,DF,ES,GO,MA,MG,MS,MT,PA,PB,PE,PI,PR,RJ,RN,RO,RR,RS,SC,SE,SP,TO) ou null
2. municipio: nome livre ou null
3. rio: nome com prefixo "Rio " ou null. Normalizar "velho chico" -> "Rio Sao Francisco"
4. bacia: nome livre ou null. Candidatos NER: {bacias_ner or "nenhum"}
5. tipo_ceva: garrafa_pet_perfurada | ceva_de_chao | ceva_solta_na_agua | bola_de_massa | saco_de_ceva | cano_pvc_perfurado | outro texto livre | null
6. grao: soja | milho | trigo | arroz | sorgo | aveia | outro texto livre | null
7. especies: lista de peixes. NER candidatos: {peixes_ner or "nenhum"}. Canonicos similares: {top_peixes}
8. observacoes: RESUMO CURTO em 1-2 frases (MAXIMO 50 palavras) sobre horario/clima/dicas/resultado. NUNCA copiar trechos longos da transcricao. Se nada relevante, "Sem observacoes adicionais relevantes."

FORMATO JSON:
{{
  "estado":{{"valor":null,"confianca":0,"evidencia":"","fora_do_gazetteer":false}},
  "municipio":{{"valor":null,"confianca":0,"evidencia":"","fora_do_gazetteer":false}},
  "rio":{{"valor":null,"confianca":0,"evidencia":"","fora_do_gazetteer":false}},
  "bacia":{{"valor":null,"confianca":0,"evidencia":"","fora_do_gazetteer":false}},
  "tipo_ceva":{{"valor":null,"confianca":0,"evidencia":"","fora_do_gazetteer":false}},
  "grao":{{"valor":null,"confianca":0,"evidencia":"","fora_do_gazetteer":false}},
  "especies":{{"valor":[],"confianca":0}},
  "observacoes":{{"valor":null,"confianca":0,"evidencia":""}}
}}

Evidencia = trecho LITERAL do texto. Nunca inventar. Responda apenas o JSON.

TEXTO:
\"\"\"
{transcricao}
\"\"\"
"""
    return prompt
