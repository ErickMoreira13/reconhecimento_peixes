#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import ollama
from tqdm import tqdm


MODEL = "qwen3:14b"

TRANSCRIPTIONS = Path("data/transcriptions")

OUTPUT = Path("data/classified")

CHECKPOINT = Path("checkpoint.json")

OUTPUT.mkdir(parents=True, exist_ok=True)

PROMPT = """
Você é um especialista em pesca esportiva brasileira.

Sua tarefa é analisar uma transcrição de vídeo.

Extraia as informações abaixo.

Retorne exatamente este objeto JSON.

Formato:

{
    "especies": [],
    "equipamentos": [],
    "iscas": [],
    "cevas": [],
    "graos": [],
    "tecnicas": [],
    "rios": [],
    "bacias": [],
    "estado": "",
    "municipio": "",
    "tipo_pesca": [],
    "observacoes": []
}

Responda SOMENTE um JSON válido.

Nunca escreva explicações.

Nunca utilize markdown.

Nunca utilize ```json.

Não adicione nenhum campo.

Não remova nenhum campo.

Todos os campos devem existir.

Quando não houver informação utilize:

[]

ou

""

Nunca utilize null.

Nunca escreva texto fora do JSON.

Você deve NORMALIZAR os nomes.

Não copie literalmente a transcrição.

Agrupe apelidos, diminutivos, aumentativos, erros de pronúncia e variações regionais para um único nome padrão.

Exemplos:

"tilapim"
"tilapinha"

→ Tilápia

"piau açu"
"piauaçu"
"piau açuzão"
"piauzinho"
"pialzinho"

→ Piau

"trairão"
"trairinha"

→ Traíra

"tamba"

→ Tambaqui

"pacuzim"

→ Pacu

"pirara"

→ Pirarara

"doura"

→ Dourado

Sempre utilize o nome mais conhecido da espécie.


Você deve identificar e normalizar TODOS os tipos de grãos, sementes, farelos, rações, farinhas, essências e ingredientes utilizados em iscas, massas e cevas.

========================
GRÃOS
========================

Sempre identifique todos os grãos mencionados na transcrição.

Exemplos:

"milho"
"milho verde"
"milho azedo"
"milho cozido"
"milho fermentado"

→ Milho

"soja"
"soja cozida"
"soja fermentada"

→ Soja

"trigo"
"trigo cozido"
"trigo azedo"

→ Trigo

"arroz"
"quirera"
"quirera de milho"
"painço"
"sorgo"
"aveia"
"ervilha"
"feijão"
"amendoim"
"girassol"
"alpiste"
"linhaça"
"canjica"

Sempre normalize para o nome mais conhecido do grão.

========================
CEVAS
========================

Além de identificar os ingredientes, identifique também o TIPO DA CEVA utilizada.

Classifique sempre em uma ou mais categorias abaixo.

Ceva Natural
- milho
- soja
- trigo
- arroz
- quirera
- canjica
- grãos naturais em geral

Ceva Proteica
- ração
- ração de peixe
- ração de coelho
- ração para cachorro
- ração para aves
- farinha de peixe
- farelo de arroz
- farelo de soja
- farelos em geral
- proteína animal

Ceva Aromática
- baunilha
- alho
- erva-doce
- mel
- açúcar
- frutas
- essências
- aromatizantes
- atrativos líquidos
- atrativos em pó

Ceva de Partículas
Sempre classifique como Ceva de Partículas quando os grãos estiverem acondicionados em recipientes perfurados que liberam alimento lentamente.

Exemplos:

- galão perfurado
- galão plástico perfurado
- garrafão perfurado
- garrafa PET perfurada
- PET furada
- saco de ráfia
- saco furado
- saco telado
- saco de cebola
- tubo de PVC perfurado
- cano de PVC perfurado
- balde perfurado
- recipiente perfurado
- cocho perfurado

Todos esses exemplos representam Ceva de Partículas.

========================
IMPORTANTE
========================

Um mesmo vídeo pode conter mais de um tipo de ceva.

Exemplo:

Milho + soja + ração dentro de um galão perfurado.

Resultado esperado:

"graos": [
    "Milho",
    "Soja"
],

"cevas": [
    "Ceva Natural",
    "Ceva Proteica",
    "Ceva de Partículas"
]

Nunca copie literalmente o texto da transcrição.

Sempre normalize os nomes.

Nunca invente informações.

Caso não exista determinado tipo de ceva, retorne uma lista vazia.

Remova duplicatas.

Ordene alfabeticamente todas as listas.

========================
FUNÇÃO
========================

Você NÃO é um assistente de escrita.

Você NÃO deve resumir.

Você NÃO deve explicar.

Você NÃO deve analisar narrativa.

Você NÃO deve traduzir.

Você NÃO deve criar títulos.

Você NÃO deve gerar comentários.

Sua única função é extrair entidades da transcrição e preencher o JSON solicitado.

========================
PROIBIDO
========================

Nunca retorne campos como:

summary
overview
analysis
translation
title
content
recommendations
notes
insights
reflection
cultural_significance
personal_reflection
key_themes

Se qualquer um desses campos aparecer, sua resposta está incorreta.

========================
FORMATO OBRIGATÓRIO
========================

A resposta deve conter EXATAMENTE os seguintes campos:

{
    "especies": [],
    "equipamentos": [],
    "iscas": [],
    "cevas": [],
    "graos": [],
    "tecnicas": [],
    "rios": [],
    "bacias": [],
    "estado": "",
    "municipio": "",
    "tipo_pesca": [],
    "observacoes": []
}

Não adicione nenhum outro campo.

Não remova nenhum campo.

Todos os campos devem existir.

Quando não houver informação:

listas → []

texto → ""

Nunca utilize null.

Nunca utilize objetos extras.

Nunca utilize markdown.

Nunca escreva qualquer texto antes ou depois do JSON.

A resposta inteira deve ser um único objeto JSON válido.


"""


client = ollama.Client()


def load_checkpoint():

    if not CHECKPOINT.exists():
        return {}

    with open(CHECKPOINT, encoding="utf8") as f:
        return json.load(f)


def save_checkpoint(data):

    with open(
        CHECKPOINT,
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def clean_response(text):

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    if text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def parse_json(text):

    text = clean_response(text)

    try:
        return json.loads(text)

    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(text[start:end + 1])

    except Exception:
        return None
    
def classificar(texto):

    resposta = client.chat(

        model=MODEL,

        format="json",

        messages=[
            {
                "role": "user",
                "content": PROMPT + "\n\n" + texto
            }
        ],

        options={
            "temperature": 0
        }

    )

    dados = parse_json(

        resposta["message"]["content"]

    )

    # print(dados)

    if dados is None:

        raise RuntimeError(

            "O Ollama retornou um JSON inválido."

        )

    return dados


def obter_texto(dados):

    texto = dados.get("texto", "").strip()

    if texto:
        return texto

    segmentos = dados.get("segmentos", [])

    partes = []

    for segmento in segmentos:

        if "text" in segmento:

            partes.append(segmento["text"])

        elif "texto" in segmento:

            partes.append(segmento["texto"])

    return " ".join(partes)


def carregar_transcricao(arquivo):

    with open(

        arquivo,

        encoding="utf8"

    ) as f:

        dados = json.load(f)

    return obter_texto(dados)


def salvar_resultado(

    arquivo,

    classificacao

):

    destino = OUTPUT / arquivo.name

    resultado = {

        "arquivo": arquivo.stem,

        "modelo": MODEL,

        "data_classificacao": datetime.now().isoformat(),

        "classificacao": classificacao

    }

    with open(

        destino,

        "w",

        encoding="utf8"

    ) as f:

        json.dump(

            resultado,

            f,

            indent=2,

            ensure_ascii=False

        )

def processar_arquivo(

    arquivo,

    checkpoint

    ):

    nome = arquivo.stem

    if checkpoint.get(nome):

        return False

    texto = carregar_transcricao(arquivo)

    if not texto:

        print(f"[IGNORADO] {nome} (sem texto)")

        checkpoint[nome] = True

        save_checkpoint(checkpoint)

        return False

    try:

        classificacao = classificar(texto)

        salvar_resultado(

            arquivo,

            classificacao

        )

        checkpoint[nome] = True

        save_checkpoint(

            checkpoint

        )

        return True

    except Exception as e:

        print()

        print("=" * 60)

        print(f"ERRO: {nome}")

        print("=" * 60)

        print(e)

        print()

        return False


def listar_transcricoes():

    arquivos = sorted(

        TRANSCRIPTIONS.glob("*.json")

    )

    return arquivos


def main():

    checkpoint = load_checkpoint()

    arquivos = listar_transcricoes()

    arquivos = [

    a

    for a in arquivos

    if a.stem not in checkpoint

    ]

    if len(arquivos) == 0:

        print()

        print("Nenhuma transcrição encontrada.")

        return

    total = len(arquivos)

    novos = 0

    ignorados = 0

    print()

    print("=" * 60)

    print(f"Modelo      : {MODEL}")

    print(f"Arquivos    : {total}")

    print("=" * 60)

    print()

    for arquivo in tqdm(

        arquivos,

        desc="Classificando"

    ):

        if checkpoint.get(arquivo.stem):

            ignorados += 1

            continue

        ok = processar_arquivo(

            arquivo,

            checkpoint

        )

        if ok:

            novos += 1

    print()

    print("=" * 60)

    print("PROCESSAMENTO FINALIZADO")

    print("=" * 60)

    print(f"Total encontrados : {total}")

    print(f"Novos             : {novos}")

    print(f"Ignorados         : {ignorados}")

    print(f"Checkpoint        : {len(checkpoint)}")

    print(f"Saída             : {OUTPUT}")

    print("=" * 60)


if __name__ == "__main__":

    main()