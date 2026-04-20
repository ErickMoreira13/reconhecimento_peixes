import json
import time

import ollama

from src import config
from src.log import get_logger
from src.schemas import CampoExtraido
from src.extracao.prompts import monta_prompt_extrator, monta_prompt_retry_schema
from src.extracao import gliner_client
from src.extracao.utils import parse_json_safe as _parse_json_safe
from src.extracao.gazetteer_check import aplica_flag_fora_do_gazetteer


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
# 1 palavra ~ 1.4 tokens em pt-br, entao 3000 palavras ~ 4200 tokens + prompt
# (~1500 tokens com os hints) pode chegar em ~5700 tokens. margem folgada.
#
# antes tava 4500 mas videos grandes (>8000 palavras) perdiam TUDO — todos
# os chunks voltavam null. hipotese: prefill apertado + hint da sumario-manual
# inflaram o prompt, estourando num_ctx. fix 8: reduzir pra 3000 pra dar
# folga. custo: videos muito grandes viram 3 chunks em vez de 2 (+1 chamada
# llm), mas ganha robustez em nao perder o conteudo inteiro
MAX_PALAVRAS_SEM_CHUNKING = 3000


_log = get_logger()


# telemetria simples pra saber se o retry de schema ta acontecendo demais.
# se videos_com_retry > 10% do total processado, vale revisar o prompt base
# pra reduzir schema errado de primeira. acesso via get_stats_retry()
_stats_retry: dict[str, int] = {
    "videos_com_retry": 0,
    "retries_ok": 0,
    "retries_falhos": 0,
}


def get_stats_retry() -> dict[str, int]:
    # snapshot atual dos contadores de retry de schema
    return dict(_stats_retry)


def reset_stats_retry() -> None:
    # util pra teste ou quando comecar novo batch
    _stats_retry["videos_com_retry"] = 0
    _stats_retry["retries_ok"] = 0
    _stats_retry["retries_falhos"] = 0


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
        _log.info("transcricao muito curta (%d palavras), pulando llm", n_palavras)
        return _tudo_null(0, modelo, motivo="texto_insuficiente")

    # se texto for gigante, chunking: extrai de cada metade e consolida
    if n_palavras > MAX_PALAVRAS_SEM_CHUNKING:
        _log.info("transcricao grande (%d palavras), dividindo em chunks", n_palavras)
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
        _log.warning("json quebrado no primeiro try, tentando com temp maior")
        raw, lat_ms2 = _chama_ollama(prompt, modelo, temperature=0.2, seed=99)
        lat_ms += lat_ms2
        data = _parse_json_safe(raw)

    if data is None:
        _log.error("%s nao gerou json valido, resposta: %s", modelo, raw[:300])
        return _tudo_null(lat_ms, modelo, motivo="llm_json_invalido")

    campos, corrigidos = _monta_resultado(data, lat_ms, modelo)

    # retry com feedback se algum campo veio com schema errado.
    # budget ESTRITO de 1 retry (nao vira loop nem se a LLM insistir no erro).
    # se o retry tbm vier errado, usa o parse corrigido do primeiro try.
    if corrigidos:
        _stats_retry["videos_com_retry"] += 1
        _log.warning("[schema-retry] campos %s vieram errados, tentando 1x com feedback", corrigidos)
        prompt_retry = monta_prompt_retry_schema(transcricao, spans, corrigidos)
        raw2, lat_retry = _chama_ollama(prompt_retry, modelo, temperature=0.0)
        lat_ms += lat_retry
        data2 = _parse_json_safe(raw2)
        if data2 is not None:
            campos2, corrigidos2 = _monta_resultado(data2, lat_ms, modelo)
            if not corrigidos2:
                # retry deu bom, usa ele
                campos = campos2
                _stats_retry["retries_ok"] += 1
                _log.info("[schema-retry] retry deu bom, usando o novo resultado")
            else:
                # retry ainda veio errado, fica com o parse corrigido do 1o
                _stats_retry["retries_falhos"] += 1
                _log.warning("[schema-retry] retry tbm veio com erro em %s, usando parse corrigido", corrigidos2)
        else:
            # retry nao gerou json valido, fica com primeiro parse
            _stats_retry["retries_falhos"] += 1
            _log.warning("[schema-retry] retry gerou json invalido, usando parse corrigido")

    # pos-processa: marca fora_do_gazetteer quando o valor nao bate com dict
    # (o llm nao eh confiavel pra essa flag, usa check deterministico)
    return aplica_flag_fora_do_gazetteer(campos)


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


def _chunk_tem_dados(campos: dict[str, CampoExtraido]) -> int:
    # conta quantos campos do chunk tem valor nao-nulo util.
    # serve pra observabilidade: se todos chunks retornam 0, video monstro
    # ta estourando o prompt ou algo similar. fix 8 investigacao.
    n = 0
    for nome, campo in campos.items():
        if campo.valor not in (None, "", []):
            n += 1
    return n


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
    vazio_count = 0
    for i, ch in enumerate(chunks, 1):
        print(f"  chunk {i}/{len(chunks)} ({len(ch.split())} palavras)")
        r = _extrai_chunk_unico(ch, gliner_checkpoint, modelo)
        resultados.append(r)
        n_campos = _chunk_tem_dados(r)
        if n_campos == 0:
            vazio_count += 1
            print(f"  [chunking-warn] chunk {i} retornou TUDO null — possivel estouro de contexto")
        else:
            print(f"  chunk {i} preencheu {n_campos}/8 campos")

    # warn pra investigar bug real do chunking (fix 8 do sumario-manual)
    if vazio_count == len(chunks):
        print(f"  [chunking-bug] TODOS os {len(chunks)} chunks retornaram null — video perdido!")

    consolidado = _consolida_chunks(resultados, modelo)
    # aplica flag pos-consolidacao (cada chunk ja aplicou, mas a uniao das
    # especies pode ter novos valores que precisam de re-check)
    return aplica_flag_fora_do_gazetteer(consolidado)


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


def _monta_resultado(
    data: dict, latencia_ms: int, modelo: str
) -> tuple[dict[str, CampoExtraido], list[str]]:
    # converte o dict cru do llm em CampoExtraido pra cada um
    #
    # retorna tupla (campos, campos_corrigidos):
    #   campos = dict normal com os 8 CampoExtraido
    #   campos_corrigidos = lista com os nomes dos campos em que o llm
    #     cuspiu schema errado (list/str direto em vez de envelope dict).
    #     se vier vazia ta tudo ok. se vier com itens, o caller pode decidir
    #     fazer retry com feedback pro llm
    campos_esperados = ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao", "especies", "observacoes"]
    out = {}
    corrigidos: list[str] = []

    for c in campos_esperados:
        item = data.get(c, {})
        # as vezes o llm cospe direto a lista/string em vez do objeto envelope
        # ex: "especies": ["tucunare", "pacu"]  em vez de {"valor": [...], ...}
        # nesse caso trata como valor puro e deixa confianca=0
        if isinstance(item, list) or isinstance(item, str):
            item = {"valor": item}
            corrigidos.append(c)
        elif not isinstance(item, dict):
            item = {}
            corrigidos.append(c)

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

    return out, corrigidos
