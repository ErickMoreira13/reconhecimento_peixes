import json
import unicodedata
from pathlib import Path

from src import config


# prompt do extrator qwen
# filosofia central: VOCABULARIO ABERTO.
# se o modelo encontrar algo que nao ta nos dicts, retorna o valor bruto do texto
# os dicts so servem pra canonizar (ex: "velho chico" -> "Rio Sao Francisco")
#
# saida em JSON com 8 campos, cada um com valor/confianca/evidencia/fora_do_gazetteer


DICTS_DIR = Path(__file__).parent.parent / "dicts"

# palavras comuns que viram stop words pra nao pontuar tudo
_STOP = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma",
         "no", "na", "nos", "nas", "em", "pra", "para", "que", "com"}


def _carrega_dict(nome: str) -> dict:
    with open(DICTS_DIR / nome, encoding="utf-8") as f:
        return json.load(f)


def _sem_acento(s: str) -> str:
    # normaliza pra nao falhar em "tucunaré" vs "tucunare"
    # whisper as vezes transcreve sem acento, o dict tem com acento
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _top_peixes_por_bm25(texto: str, k: int = 20) -> list[str]:
    # retorna os top-k nomes canonicos mais parecidos com o texto
    # normaliza acentos pra matching mais robusto
    d = _carrega_dict("peixes_conhecidos.json")
    nomes = d.get("nomes_comuns_peixes", [])

    texto_norm = _sem_acento(texto.lower())
    scored: list[tuple[str, int]] = []
    for n in nomes:
        n_norm = _sem_acento(n.lower())
        # match direto (substring) tem score bem alto
        if n_norm in texto_norm:
            scored.append((n, 999))
            continue
        # fallback: quantas palavras do nome (ignorando stop words) aparecem
        tokens = [t for t in n_norm.split() if t not in _STOP and len(t) > 2]
        if not tokens:
            continue
        score = sum(1 for t in tokens if t in texto_norm)
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

== REGRA CENTRAL: VOCABULARIO ABERTO ==
Os exemplos abaixo NAO sao lista fechada. Se o video menciona peixe/bacia/rio/
ceva/grao que NAO esta nos exemplos, CAPTURE MESMO ASSIM usando o valor LITERAL
do texto. Essa captura eh VALIOSA, nao um erro.

FLAG fora_do_gazetteer=true: marque ASSIM quando o valor que voce retornou NAO
aparece nos exemplos listados nesta instrucao. Por exemplo, se o peixe
"piabanha" nao esta na lista top-20 abaixo, retorne especies=[{{"nome":
"piabanha", ...}}] com fora_do_gazetteer=true. Isso vale pra todos os campos.

fora_do_gazetteer=false SO quando o valor casa exatamente com um dos exemplos.

CAMPOS:
1. estado: sigla UF (AC,AL,AM,AP,BA,CE,DF,ES,GO,MA,MG,MS,MT,PA,PB,PE,PI,PR,RJ,RN,RO,RR,RS,SC,SE,SP,TO) ou null
2. municipio: nome livre ou null
3. rio: nome com prefixo "Rio " ou null. Normalizar "velho chico" -> "Rio Sao Francisco"
4. bacia: nome livre ou null. Candidatos NER: {bacias_ner or "nenhum"}
5. tipo_ceva: garrafa_pet_perfurada | ceva_de_chao | ceva_solta_na_agua | bola_de_massa | saco_de_ceva | cano_pvc_perfurado | outro texto livre | null.
   ATENCAO: so preencha tipo_ceva se o texto mencionar EXPLICITAMENTE
   alguma das palavras: "ceva", "seva", "ceba", "cevar", "cevador", "cevando"
   (ou variantes). pescaria sem ceva (so com isca viva, isca artificial,
   espinhel, rede, linha, anzol) DEVE vir com tipo_ceva=null. nao chute
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

Evidencia = trecho LITERAL do texto. Nunca inventar. Lembre de marcar
fora_do_gazetteer=true quando o valor nao esta na lista. Responda apenas o JSON.

TEXTO:
\"\"\"
{transcricao}
\"\"\"
"""
    return prompt


def monta_prompt_retry_schema(
    transcricao: str,
    spans_gliner: dict[str, list[dict]],
    campos_errados: list[str],
) -> str:
    # retry focado quando o llm cuspiu campo com schema ruim (list/str direto
    # em vez de envelope {valor, confianca, evidencia, fora_do_gazetteer}).
    #
    # reusa o prompt principal e prefixa um recado curto dizendo o que deu
    # errado e como corrigir. tentei manter sucinto — prompt muito grande
    # nao ajuda, ja dobrou o prefill
    base = monta_prompt_extrator(transcricao, spans_gliner)
    lista = ", ".join(campos_errados)
    aviso = f"""ATENCAO: tentativa anterior veio com schema errado nos campos: {lista}.
Cada um desses campos DEVE ser um objeto com as chaves valor, confianca e evidencia.
NAO retorne o campo direto como lista ou string — embrulhe no objeto.

exemplo errado:  "especies": ["tucunare"]
exemplo certo:   "especies": {{"valor": [{{"nome": "tucunare", "evidencia": "..."}}], "confianca": 0.9}}

Agora gere o JSON correto:

"""
    return aviso + base
