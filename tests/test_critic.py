from unittest.mock import MagicMock, patch

import pytest

from src.schemas import CampoExtraido, Veredito
from src.verificador import critic


TRANSC = "peguei um tambaqui de 5kg no rio madeira com milho como isca"


def _campo(valor, confianca=0.8, evidencia="", fora=False):
    return CampoExtraido(
        valor=valor, confianca=confianca, evidencia=evidencia,
        modelo_usado="test", fora_do_gazetteer=fora, latencia_ms=0,
    )


def test_avalia_retorna_aceito_se_valor_null():
    # regra de eficiencia: valores null nao gastam chamada ao llm
    v = critic.avalia("estado", _campo(None), TRANSC, {})
    assert v.aceito
    assert "null" in v.razao.lower() or "verificar" in v.razao.lower()


def test_avalia_retorna_aceito_se_lista_vazia():
    v = critic.avalia("especies", _campo([]), TRANSC, {})
    assert v.aceito


def test_avalia_retorna_aceito_se_string_vazia():
    v = critic.avalia("rio", _campo(""), TRANSC, {})
    assert v.aceito


def test_tipos_validos_nao_inclui_fora_gazetteer():
    # guardiao: se alguem acidentalmente adicionar valor_fora_gazetteer
    # em TIPOS_VALIDOS, o teste quebra e avisa
    assert "valor_fora_gazetteer" not in critic.TIPOS_VALIDOS


def test_tipos_validos_inclui_os_esperados():
    esperados = {
        "evidencia_nao_alinha", "conflito_cross_field", "alucinacao_suspeita",
        "confianca_baixa", "nome_proprio_confundido", "contexto_irrelevante",
    }
    assert critic.TIPOS_VALIDOS == esperados


def test_avalia_batch_mock_ollama_aceito(monkeypatch):
    # mocka o ollama pra retornar resposta aceitando tudo
    class FakeResp:
        def __init__(self, text):
            self.text = text
        def __getitem__(self, k):
            return self.text if k == "response" else None

    resp_json = """
    {
      "estado": {"aceito": true, "razao": "ok", "tipo_rejeicao": null},
      "grao": {"aceito": true, "razao": "milho claro", "tipo_rejeicao": null}
    }
    """

    class FakeClient:
        def __init__(self, host=None):
            pass
        def generate(self, **kwargs):
            return {"response": resp_json}

    monkeypatch.setattr("ollama.Client", FakeClient)

    campos = {
        "estado": _campo("RO", confianca=0.9, evidencia="rondonia"),
        "grao": _campo("milho", confianca=0.95, evidencia="com milho"),
    }
    result = critic.avalia_batch(campos, TRANSC)

    assert "estado" in result
    assert "grao" in result
    assert result["estado"].aceito
    assert result["grao"].aceito


def test_avalia_batch_ollama_quebrado_aceita_por_default(monkeypatch):
    # se ollama da erro, deve aceitar tudo pra nao travar pipeline
    class FakeClient:
        def __init__(self, host=None):
            pass
        def generate(self, **kwargs):
            raise ConnectionError("ollama caiu")

    monkeypatch.setattr("ollama.Client", FakeClient)

    campos = {"estado": _campo("RO")}
    result = critic.avalia_batch(campos, TRANSC)

    assert result["estado"].aceito  # ollama offline -> aceita
    assert "indispon" in result["estado"].razao.lower()


def test_avalia_batch_json_quebrado_aceita_por_default(monkeypatch):
    # se ollama cuspir json que nao parseia, aceita pra nao travar
    class FakeClient:
        def __init__(self, host=None):
            pass
        def generate(self, **kwargs):
            return {"response": "isso nao eh json nenhum, so texto solto"}

    monkeypatch.setattr("ollama.Client", FakeClient)

    campos = {"estado": _campo("RO")}
    result = critic.avalia_batch(campos, TRANSC)

    assert result["estado"].aceito


def test_avalia_batch_tipo_invalido_vira_none(monkeypatch):
    # se o llm inventar tipo tipo "valor_fora_gazetteer" a gente ignora
    # e vira None (nao pode rejeitar por isso)
    resp_json = '{"estado": {"aceito": false, "razao": "sla", "tipo_rejeicao": "valor_fora_gazetteer"}}'

    class FakeClient:
        def __init__(self, host=None):
            pass
        def generate(self, **kwargs):
            return {"response": resp_json}

    monkeypatch.setattr("ollama.Client", FakeClient)

    result = critic.avalia_batch({"estado": _campo("RO")}, TRANSC)
    # tipo_rejeicao invalido vira None
    assert result["estado"].tipo_rejeicao is None
