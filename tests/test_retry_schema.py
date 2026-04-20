# testes do retry de schema no _extrai_chunk_unico
#
# cenarios:
#   1. schema ok de primeira -> nao faz retry
#   2. schema errado -> faz 1 retry, usa o novo se vier ok
#   3. retry tbm vem errado -> mantem parse do 1o try corrigido
#   4. budget estrito: no maximo 1 retry por video (nao loop)
#   5. telemetria conta direito

import json

import pytest

from src.extracao import qwen_extrator


@pytest.fixture(autouse=True)
def _reset_stats():
    qwen_extrator.reset_stats_retry()
    yield
    qwen_extrator.reset_stats_retry()


def _json_ok():
    # payload valido com todos os campos em envelope
    return json.dumps({
        "estado": {"valor": "RO", "confianca": 0.9, "evidencia": "rondonia"},
        "municipio": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "rio": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "bacia": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "tipo_ceva": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "grao": {"valor": None, "confianca": 0.0, "evidencia": ""},
        "especies": {"valor": [{"nome": "tucunare", "evidencia": "x"}], "confianca": 0.8},
        "observacoes": {"valor": None, "confianca": 0.0, "evidencia": ""},
    })


def _json_schema_errado():
    # payload com especies e municipio em formato errado
    return json.dumps({
        "estado": {"valor": "RO", "confianca": 0.9, "evidencia": "rondonia"},
        "municipio": "porto velho",  # string direto, errado
        "rio": {"valor": None, "confianca": 0.0},
        "bacia": {"valor": None, "confianca": 0.0},
        "tipo_ceva": {"valor": None, "confianca": 0.0},
        "grao": {"valor": None, "confianca": 0.0},
        "especies": ["tucunare", "pacu"],  # lista direto, errado
        "observacoes": {"valor": None, "confianca": 0.0},
    })


def _patch_ollama(monkeypatch, respostas: list[str]):
    # respostas eh uma lista de strings, cada chamada pega a proxima
    chamadas = {"n": 0}

    def fake(prompt, modelo, temperature=0.0, seed=42):
        i = chamadas["n"]
        chamadas["n"] += 1
        return respostas[i], 100

    monkeypatch.setattr(qwen_extrator, "_chama_ollama", fake)
    return chamadas


def _patch_gliner(monkeypatch):
    # nao quero chamar gliner de verdade nos testes
    monkeypatch.setattr(
        qwen_extrator.gliner_client,
        "extrai_por_label",
        lambda *a, **k: {"peixe": [], "bacia hidrografica": []},
    )


def _patch_gazetteer(monkeypatch):
    # nao quero mexer nos dicts reais
    monkeypatch.setattr(
        qwen_extrator,
        "aplica_flag_fora_do_gazetteer",
        lambda c: c,
    )


def test_schema_ok_nao_faz_retry(monkeypatch):
    _patch_gliner(monkeypatch)
    _patch_gazetteer(monkeypatch)
    chamadas = _patch_ollama(monkeypatch, [_json_ok()])

    qwen_extrator._extrai_chunk_unico("texto qualquer", None, "fake:model")

    assert chamadas["n"] == 1
    stats = qwen_extrator.get_stats_retry()
    assert stats["videos_com_retry"] == 0


def test_schema_errado_dispara_retry(monkeypatch):
    _patch_gliner(monkeypatch)
    _patch_gazetteer(monkeypatch)
    chamadas = _patch_ollama(monkeypatch, [_json_schema_errado(), _json_ok()])

    qwen_extrator._extrai_chunk_unico("texto", None, "fake:model")

    # 1a chamada + 1 retry
    assert chamadas["n"] == 2
    stats = qwen_extrator.get_stats_retry()
    assert stats["videos_com_retry"] == 1
    assert stats["retries_ok"] == 1


def test_retry_tbm_errado_mantem_parse_corrigido(monkeypatch):
    _patch_gliner(monkeypatch)
    _patch_gazetteer(monkeypatch)
    # 1o vem errado, 2o tbm vem errado — fica com parse do 1o (corrigido)
    chamadas = _patch_ollama(monkeypatch, [_json_schema_errado(), _json_schema_errado()])

    campos = qwen_extrator._extrai_chunk_unico("texto", None, "fake:model")

    # 2 chamadas no maximo, nao vira loop
    assert chamadas["n"] == 2
    stats = qwen_extrator.get_stats_retry()
    assert stats["videos_com_retry"] == 1
    assert stats["retries_falhos"] == 1
    # especies foi normalizada mesmo com schema errado
    assert len(campos["especies"].valor) == 2


def test_budget_estrito_max_1_retry(monkeypatch):
    # se o llm insistir no erro em 3 respostas, so chama 2 vezes no total
    _patch_gliner(monkeypatch)
    _patch_gazetteer(monkeypatch)
    chamadas = _patch_ollama(monkeypatch, [_json_schema_errado()] * 5)

    qwen_extrator._extrai_chunk_unico("texto", None, "fake:model")

    assert chamadas["n"] == 2  # nunca mais que 2


def test_retry_com_json_invalido_mantem_primeiro(monkeypatch):
    _patch_gliner(monkeypatch)
    _patch_gazetteer(monkeypatch)
    # 2a resposta eh lixo, nao parseavel
    chamadas = _patch_ollama(monkeypatch, [_json_schema_errado(), "nao eh json"])

    campos = qwen_extrator._extrai_chunk_unico("texto", None, "fake:model")

    assert chamadas["n"] == 2
    stats = qwen_extrator.get_stats_retry()
    assert stats["retries_falhos"] == 1
    # ainda deve ter campos do primeiro parse
    assert campos["estado"].valor == "RO"


def test_telemetria_acumula_entre_videos(monkeypatch):
    _patch_gliner(monkeypatch)
    _patch_gazetteer(monkeypatch)
    # video 1: schema ok. video 2: schema errado + retry ok. video 3: ok.
    _patch_ollama(monkeypatch, [
        _json_ok(),
        _json_schema_errado(), _json_ok(),
        _json_ok(),
    ])

    for _ in range(3):
        qwen_extrator._extrai_chunk_unico("texto", None, "fake:model")

    stats = qwen_extrator.get_stats_retry()
    assert stats["videos_com_retry"] == 1
    assert stats["retries_ok"] == 1
    assert stats["retries_falhos"] == 0
