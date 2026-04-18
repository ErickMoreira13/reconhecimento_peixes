import json
import time

import ollama

from src import config
from src.schemas import CampoExtraido
from src.extracao.prompts import monta_prompt_extrator
from src.extracao import gliner_client
from src.extracao.utils import parse_json_safe as _parse_json_safe


# extrator principal: ollama/qwen single-prompt pra sair os 8 campos
# filosofia de vocabulario aberto ja ta no prompt
#
# 1 chamada por video eh mt mais rapido que 8 agentes separados (5s vs 13s no 4060)
# se o json vier quebrado, tenta retry com temp maior


# se texto tem menos que isso nao vale nem chamar o llm, retorna null direto.
# alguns videos sao shorts de 15s ou audios com falha de transcricao —
# whisper as vezes retorna 0 palavras em cortes publicitarios
MIN_PALAVRAS_PRA_EXTRAIR = 30

# acima disso o contexto do qwen (8192 tokens) nao aguenta a transcricao
# inteira mais o prompt. divide em chunks.
# 1 palavra ~ 1.4 tokens em pt-br, entao 4500 palavras ~ 6300 tokens + prompt
# pode chegar em ~7800 tokens. deixa margem de seguranca.
MAX_PALAVRAS_SEM_CHUNKING = 4500


def _chama_ollama(prompt: str, modelo: str, temperature: float = 0.0, seed: int = 42) -> tuple[str, int]:
    # retorna (resposta, latencia_ms)
    cliente = ollama.Client(host=config.OLLAMA_HOST)

    t0 = time.monotonic()
    resp = cliente.generate(
        model=modelo,
        prompt=prompt,
        format="json",
        options={
            "temperature": temperature,
            "seed": seed,
            "num_ctx": 8192,
        },
    )
    latencia_ms = int((time.monotonic() - t0) * 1000)
    return resp["response"], latencia_ms


def extrai_campos(
    transcricao: str,
    gliner_checkpoint: str | None = None,
    modelo: str | None = None,
) -> dict[str, CampoExtraido]:
    # se nao passar modelo usa o do .env
    modelo = modelo or config.MODEL_EXTRATOR

    # 0. pula cedo se texto muito curto. whisper as vezes cuspe ""
    # em cortes publicitarios ou audios com so musica, nao vale rodar llm.
    n_palavras = len(transcricao.split())
    if n_palavras < MIN_PALAVRAS_PRA_EXTRAIR:
        print(f"transcricao muito curta ({n_palavras} palavras), pulando llm")
        return _tudo_null(0, modelo, motivo="texto_insuficiente")

    # se texto for gigante, chunking: extrai de cada metade e consolida
    if n_palavras > MAX_PALAVRAS_SEM_CHUNKING:
        print(f"transcricao grande ({n_palavras} palavras), dividindo em chunks")
        return _extrai_com_chunking(transcricao, gliner_checkpoint, modelo)

    return _extrai_chunk_unico(transcricao, gliner_checkpoint, modelo)


def _extrai_chunk_unico(
    transcricao: str,
    gliner_checkpoint: str | None,
    modelo: str,
) -> dict[str, CampoExtraido]:
    # fluxo normal, um prompt do extrator em cima do texto inteiro
    spans = gliner_client.extrai_por_label(transcricao, checkpoint_path=gliner_checkpoint)
    prompt = monta_prompt_extrator(transcricao, spans)

    raw, lat_ms = _chama_ollama(prompt, modelo, temperature=0.0)
    data = _parse_json_safe(raw)

    if data is None:
        # retry com temp 0.2, as vezes funciona
        print("json quebrado no primeiro try, tentando com temp maior")
        raw, lat_ms2 = _chama_ollama(prompt, modelo, temperature=0.2, seed=99)
        lat_ms += lat_ms2
        data = _parse_json_safe(raw)

    if data is None:
        print(f"{modelo} nao gerou json valido, resposta: {raw[:300]}")
        return _tudo_null(lat_ms, modelo, motivo="llm_json_invalido")

    return _monta_resultado(data, lat_ms, modelo)


def _dividir_em_chunks(texto: str, max_palavras: int) -> list[str]:
    # divide preservando frases (quebra em ponto final sempre que possivel)
    palavras = texto.split()
    chunks: list[str] = []
    i = 0
    while i < len(palavras):
        # encontra o ponto final mais proximo antes de max_palavras
        fim = min(i + max_palavras, len(palavras))
        # tenta expandir ou recuar ate achar "." pra nao quebrar frase no meio
        if fim < len(palavras):
            for j in range(fim, max(i, fim - 200), -1):
                if palavras[j - 1].endswith((".", "!", "?")):
                    fim = j
                    break
        chunks.append(" ".join(palavras[i:fim]))
        i = fim
    return chunks


def _extrai_com_chunking(
    transcricao: str,
    gliner_checkpoint: str | None,
    modelo: str,
) -> dict[str, CampoExtraido]:
    # divide em 2 partes (ou mais se mt grande), extrai cada, merge no final.
    # custos: 2x chamadas ao llm, mas nao perde info do final do video.
    chunks = _dividir_em_chunks(transcricao, MAX_PALAVRAS_SEM_CHUNKING)
    print(f"  dividido em {len(chunks)} chunks")

    resultados: list[dict[str, CampoExtraido]] = []
    for i, ch in enumerate(chunks, 1):
        print(f"  chunk {i}/{len(chunks)} ({len(ch.split())} palavras)")
        resultados.append(_extrai_chunk_unico(ch, gliner_checkpoint, modelo))

    return _consolida_chunks(resultados, modelo)


def _consolida_chunks(
    resultados: list[dict[str, CampoExtraido]],
    modelo: str,
) -> dict[str, CampoExtraido]:
    # merge dos resultados dos chunks. estrategia:
    # - campos escalares (estado, rio, etc): pega o primeiro que for nao-null
    #   com maior confianca
    # - especies: uniao dos nomes, deduplicado
    # - observacoes: concatena resumos curtos com " | "
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out: dict[str, CampoExtraido] = {}
    lat_total = sum(r.get("estado").latencia_ms for r in resultados if r.get("estado"))

    for c in campos:
        # pega so os chunks que tem valor pra esse campo
        com_valor = [
            r[c] for r in resultados
            if c in r and r[c].valor not in (None, "", [])
        ]

        if not com_valor:
            out[c] = CampoExtraido(
                valor=None if c != "especies" else [],
                confianca=0.0, evidencia="", modelo_usado=modelo,
                fora_do_gazetteer=False, latencia_ms=lat_total,
            )
            continue

        if c == "especies":
            # uniao deduplicando por nome
            vistos = set()
            uniao = []
            for campo in com_valor:
                for item in (campo.valor or []):
                    nome = (item.get("nome") if isinstance(item, dict) else str(item)).strip().lower()
                    if nome and nome not in vistos:
                        vistos.add(nome)
                        uniao.append(item)
            conf = max(c.confianca for c in com_valor)
            out[c] = CampoExtraido(
                valor=uniao, confianca=conf, evidencia="",
                modelo_usado=modelo, fora_do_gazetteer=False, latencia_ms=lat_total,
            )
        elif c == "observacoes":
            # concatena
            textos = [campo.valor for campo in com_valor if campo.valor]
            texto = " | ".join(textos)
            conf = sum(c.confianca for c in com_valor) / len(com_valor)
            out[c] = CampoExtraido(
                valor=texto, confianca=conf, evidencia="",
                modelo_usado=modelo, fora_do_gazetteer=False, latencia_ms=lat_total,
            )
        else:
            # escalares: pega o de maior confianca
            melhor = max(com_valor, key=lambda x: x.confianca)
            out[c] = CampoExtraido(
                valor=melhor.valor, confianca=melhor.confianca,
                evidencia=melhor.evidencia, modelo_usado=modelo,
                fora_do_gazetteer=melhor.fora_do_gazetteer,
                latencia_ms=lat_total,
            )

    return out


def _tudo_null(latencia_ms: int, modelo: str, motivo: str = "") -> dict[str, CampoExtraido]:
    # fallback quando o llm nao respondeu nada util
    # motivo ajuda a distinguir no csv final se foi culpa do llm ou texto insuficiente
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}
    for c in campos:
        out[c] = CampoExtraido(
            valor=None if c != "especies" else [],
            confianca=0.0,
            evidencia=motivo,
            modelo_usado=modelo,
            fora_do_gazetteer=False,
            latencia_ms=latencia_ms,
        )
    return out


def _normaliza_especies(valor) -> list[dict]:
    # forca especies a ser sempre lista de dicts, pra nao aceitar string solta
    # (qwen as vezes cospe "especies": "peixe_x" em vez de lista — se deixar passar,
    # uma alucinacao tipo "só filapossauro" entra como string e ninguem pega)
    if valor is None or valor == "":
        return []
    if isinstance(valor, list):
        normalizada = []
        for item in valor:
            if isinstance(item, dict):
                normalizada.append({
                    "nome": str(item.get("nome", "")).strip(),
                    "evidencia": str(item.get("evidencia", "")).strip(),
                    "fora_do_gazetteer": bool(item.get("fora_do_gazetteer", False)),
                })
            elif isinstance(item, str):
                normalizada.append({"nome": item.strip(), "evidencia": "", "fora_do_gazetteer": False})
        # tira entradas vazias
        return [e for e in normalizada if e.get("nome")]
    if isinstance(valor, str):
        # qwen cuspiu string solta, tenta separar por virgula/ponto-e-virgula
        # se for algo muito estranho, a camada seguinte (critic) deve pegar
        partes = [p.strip() for p in valor.replace(";", ",").split(",") if p.strip()]
        return [{"nome": p, "evidencia": "", "fora_do_gazetteer": False} for p in partes]
    return []


def _monta_resultado(data: dict, latencia_ms: int, modelo: str) -> dict[str, CampoExtraido]:
    # converte o dict cru do llm em CampoExtraido pra cada um
    campos = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}

    for c in campos:
        item = data.get(c, {}) or {}

        if c == "especies":
            valor = _normaliza_especies(item.get("valor"))
        else:
            valor = item.get("valor")

        out[c] = CampoExtraido(
            valor=valor,
            confianca=float(item.get("confianca", 0.0) or 0.0),
            evidencia=str(item.get("evidencia", "") or ""),
            modelo_usado=modelo,
            fora_do_gazetteer=bool(item.get("fora_do_gazetteer", False)),
            latencia_ms=latencia_ms,
        )

    return out
