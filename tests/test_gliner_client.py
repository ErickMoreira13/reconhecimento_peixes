from unittest.mock import MagicMock, patch

import pytest

from src.extracao import gliner_client


def test_labels_padrao():
    # sanity check do que o gliner espera extrair (4 labels agora)
    assert "peixe" in gliner_client.LABELS_PADRAO
    assert "bacia hidrografica" in gliner_client.LABELS_PADRAO
    assert "rio" in gliner_client.LABELS_PADRAO
    assert "municipio" in gliner_client.LABELS_PADRAO
    assert len(gliner_client.LABELS_PADRAO) == 4


def test_extrai_por_label_agrupa_spans(monkeypatch):
    # mocka _carrega e extrai_spans pra nao chamar gliner real
    fake_spans = [
        {"text": "tucunare", "label": "peixe", "start": 0, "end": 8, "score": 0.9},
        {"text": "pacu", "label": "peixe", "start": 10, "end": 14, "score": 0.85},
        {"text": "bacia amazonica", "label": "bacia hidrografica", "start": 20, "end": 35, "score": 0.8},
        {"text": "rio madeira", "label": "rio", "start": 40, "end": 51, "score": 0.7},
        {"text": "porto velho", "label": "municipio", "start": 60, "end": 71, "score": 0.6},
    ]
    monkeypatch.setattr(gliner_client, "extrai_spans", lambda *a, **k: fake_spans)

    result = gliner_client.extrai_por_label("texto qualquer")

    assert "peixe" in result
    assert "bacia hidrografica" in result
    assert "rio" in result
    assert "municipio" in result
    assert len(result["peixe"]) == 2
    assert len(result["bacia hidrografica"]) == 1
    assert len(result["rio"]) == 1
    assert len(result["municipio"]) == 1


def test_extrai_por_label_vazio_quando_sem_spans(monkeypatch):
    monkeypatch.setattr(gliner_client, "extrai_spans", lambda *a, **k: [])

    result = gliner_client.extrai_por_label("texto sem entidade nenhuma")

    # todas as labels presentes mas vazias
    assert result["peixe"] == []
    assert result["bacia hidrografica"] == []
    assert result["rio"] == []
    assert result["municipio"] == []


def test_extrai_por_label_subset_customizado(monkeypatch):
    # passar labels customizado permite rodar so com 2 pra comparar
    fake_spans = [
        {"text": "tucunare", "label": "peixe"},
        {"text": "porto velho", "label": "municipio"},
    ]
    monkeypatch.setattr(gliner_client, "extrai_spans", lambda *a, **k: fake_spans)

    # so peixe e bacia, municipio nao deve entrar
    result = gliner_client.extrai_por_label("x", labels=["peixe", "bacia hidrografica"])
    assert "peixe" in result
    assert "municipio" not in result
    assert len(result["peixe"]) == 1


def test_extrai_por_label_ignora_labels_desconhecidos(monkeypatch):
    # se o modelo por algum motivo retornar spans de outros tipos, filtra
    fake_spans = [
        {"text": "tucunare", "label": "peixe"},
        {"text": "invasor", "label": "label_maluco_nao_esperado"},
    ]
    monkeypatch.setattr(gliner_client, "extrai_spans", lambda *a, **k: fake_spans)

    result = gliner_client.extrai_por_label("x")
    assert len(result["peixe"]) == 1
    # label desconhecido nao entra
    assert "label_maluco_nao_esperado" not in result


def test_extrai_spans_falha_graceful(monkeypatch):
    # se o modelo falhar, deve retornar [] nao levantar excecao
    class FakeModel:
        def predict_entities(self, texto, labels, threshold):
            raise RuntimeError("gliner quebrou")

    monkeypatch.setattr(gliner_client, "_carrega", lambda ckpt=None: FakeModel())
    monkeypatch.setattr(gliner_client, "_modelo", FakeModel())

    # nao deve levantar
    result = gliner_client.extrai_spans("texto")
    assert result == []
