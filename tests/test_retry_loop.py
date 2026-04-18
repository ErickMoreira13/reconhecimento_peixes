from unittest.mock import patch, MagicMock

import pytest

from src.schemas import CampoExtraido, Veredito
from src.verificador import retry_loop


def _campo(valor, confianca=0.8, evidencia="pescando tucunare"):
    return CampoExtraido(
        valor=valor, confianca=confianca, evidencia=evidencia,
        modelo_usado="test", fora_do_gazetteer=False, latencia_ms=100,
    )


TRANSC = "fala galera hoje vamo pescar tucunare no rio madeira com milho"


def test_todos_aceitos_nao_faz_retry(monkeypatch):
    campos = {
        "estado": _campo(None),
        "grao": _campo("milho", evidencia="com milho"),
        "rio": _campo("Rio Madeira", evidencia="rio madeira"),
        "especies": _campo([{"nome": "tucunare", "evidencia": "pescar tucunare"}]),
        "municipio": _campo(None),
        "bacia": _campo(None),
        "tipo_ceva": _campo(None),
        # 15 palavras, passa da regra de length minimo (10)
        "observacoes": _campo(
            "pesca matinal com tucunare e milho no rio madeira teve bom resultado galera boa",
            evidencia="pescar tucunare",
        ),
    }

    # mock do critic pra aceitar tudo
    from src.verificador import critic
    monkeypatch.setattr(critic, "avalia_batch", lambda campos, transc: {
        nome: Veredito(aceito=True, razao="ok") for nome in campos
    })

    resultado = retry_loop.verifica_todos_os_campos(campos, TRANSC, {})

    assert all(r["veredito"].aceito for r in resultado.values())
    assert all(r["tentativas"] == 0 for r in resultado.values())


def test_campo_rejeitado_tenta_reextrair(monkeypatch):
    campos = {
        "estado": _campo(None),
        "grao": _campo(None),
        "rio": _campo(None),
        "especies": _campo([]),
        "municipio": _campo(None),
        "bacia": _campo(None),
        "tipo_ceva": _campo("ceva_inventada", confianca=0.9, evidencia="nao tem evidencia no texto"),
        "observacoes": _campo(None),
    }

    # critic aceita todos menos tipo_ceva
    from src.verificador import critic
    def fake_avalia_batch(campos, transc):
        out = {}
        for nome in campos:
            if nome == "tipo_ceva":
                out[nome] = Veredito(aceito=False, razao="evidencia nao alinha",
                                     tipo_rejeicao="evidencia_nao_alinha")
            else:
                out[nome] = Veredito(aceito=True, razao="ok")
        return out
    monkeypatch.setattr(critic, "avalia_batch", fake_avalia_batch)

    # mock da re-extracao pra retornar valor "corrigido"
    reextracoes = {"n": 0}
    def fake_reextrai(transc, spans, nome, veredito, tent):
        reextracoes["n"] += 1
        return _campo("ceva_de_chao", confianca=0.9, evidencia="ceva de chao")
    monkeypatch.setattr(retry_loop, "_reextrai_campo", fake_reextrai)

    # critic avalia individual na re-extracao
    monkeypatch.setattr(critic, "avalia", lambda nome, c, t, o: Veredito(aceito=True, razao="ok agora"))

    resultado = retry_loop.verifica_todos_os_campos(campos, TRANSC, {})

    # tipo_ceva deveria ter tentativa > 0 e veredito aceito apos retry
    assert resultado["tipo_ceva"]["tentativas"] >= 1
    assert reextracoes["n"] >= 1


def test_campo_rejeitado_apos_retries_vira_null(monkeypatch):
    campos = {
        "estado": _campo(None),
        "grao": _campo(None),
        "rio": _campo(None),
        "especies": _campo([{"nome": "filapossauro", "evidencia": "sem evidencia"}]),
        "municipio": _campo(None),
        "bacia": _campo(None),
        "tipo_ceva": _campo(None),
        "observacoes": _campo(None),
    }

    from src.verificador import critic
    # critic sempre rejeita (batch recebe dict de campos, avalia recebe nome+campo)
    def reject_batch(campos, transcricao):
        return {nome: Veredito(aceito=False, razao="nao passa", tipo_rejeicao="alucinacao_suspeita")
                for nome in campos}
    def reject_individual(nome, campo, transcricao, outros):
        return Veredito(aceito=False, razao="nao passa", tipo_rejeicao="alucinacao_suspeita")
    monkeypatch.setattr(critic, "avalia_batch", reject_batch)
    monkeypatch.setattr(critic, "avalia", reject_individual)

    # reextracao sempre retorna algo que tb vai ser rejeitado
    monkeypatch.setattr(retry_loop, "_reextrai_campo",
                        lambda *a, **k: _campo([{"nome": "ainda_inventado"}]))

    resultado = retry_loop.verifica_todos_os_campos(campos, TRANSC, {})

    # especies foi zerado (valor = [] ou None apos rejeicao)
    esp = resultado["especies"]["campo"]
    assert esp.valor == [] or esp.valor is None
    # evidencia deve ter flag de rejeicao
    assert "rejeitado" in esp.evidencia.lower() or esp.valor in (None, [])


def test_budget_retries_tem_limite(monkeypatch):
    # garante que o budget nao eh infinito
    assert retry_loop.BUDGET_RETRIES <= 3  # sanity check: nao passar de 3

    campos = {
        "estado": _campo(None), "grao": _campo(None), "rio": _campo(None),
        "especies": _campo([]), "municipio": _campo(None), "bacia": _campo(None),
        "tipo_ceva": _campo("x", confianca=0.9, evidencia="nao alinha"),
        "observacoes": _campo(None),
    }

    from src.verificador import critic
    tentativas_criar = {"n": 0}

    def reject_batch(campos, transc):
        return {nome: Veredito(aceito=True, razao="ok") if nome != "tipo_ceva"
                else Veredito(aceito=False, razao="no", tipo_rejeicao="alucinacao_suspeita")
                for nome in campos}

    def reject_individual(nome, campo, transcricao, outros):
        return Veredito(aceito=False, razao="no", tipo_rejeicao="alucinacao_suspeita")

    monkeypatch.setattr(critic, "avalia_batch", reject_batch)
    monkeypatch.setattr(critic, "avalia", reject_individual)

    def contador(transc, spans, nome, veredito, tent):
        tentativas_criar["n"] += 1
        return _campo("ainda_ruim", evidencia="ainda ruim")

    monkeypatch.setattr(retry_loop, "_reextrai_campo", contador)

    retry_loop.verifica_todos_os_campos(campos, TRANSC, {})

    # nunca deve fazer mais que BUDGET_RETRIES re-extracoes do mesmo campo
    assert tentativas_criar["n"] <= retry_loop.BUDGET_RETRIES
