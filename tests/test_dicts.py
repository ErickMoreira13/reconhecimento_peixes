import json
from pathlib import Path

import pytest


DICTS = Path(__file__).parent.parent / "src" / "dicts"


def _load(nome):
    with open(DICTS / nome, encoding="utf-8") as f:
        return json.load(f)


def test_estados_sao_27():
    # estado eh o UNICO enum fechado de verdade
    d = _load("estados.json")
    assert len(d["ufs"]) == 27
    # checa que nao esta mentindo e fala que eh fechado no doc
    assert "fechado" in d["__doc__"].lower() or "nao vai aparecer" in d["__doc__"].lower()


def test_peixes_dict_tem_doc_aberto():
    # o dict de peixes eh EXEMPLO e tem que deixar isso explicito
    d = _load("peixes_conhecidos.json")
    assert "__doc__" in d
    doc = d["__doc__"].lower()
    assert "exemplo" in doc or "nao eh lista fechada" in doc


def test_bacias_dict_tem_doc_aberto():
    d = _load("bacias_conhecidas.json")
    assert "__doc__" in d
    doc = d["__doc__"].lower()
    assert "exemplo" in doc or "nao eh lista fechada" in doc


def test_cevas_dict_tem_doc_aberto():
    d = _load("cevas.json")
    assert "__doc__" in d
    assert "exemplo" in d["__doc__"].lower()


def test_graos_dict_tem_doc_aberto():
    d = _load("graos.json")
    assert "__doc__" in d
    assert "exemplo" in d["__doc__"].lower() or "nao eh lista fechada" in d["__doc__"].lower()


def test_todos_estados_tem_sigla_de_2_chars():
    d = _load("estados.json")
    for uf in d["ufs"]:
        assert len(uf["sigla"]) == 2
        assert uf["sigla"].isupper()
        assert "nome" in uf


@pytest.mark.parametrize("nome", [
    "peixes_conhecidos.json",
    "bacias_conhecidas.json",
    "estados.json",
    "cevas.json",
    "graos.json",
])
def test_todos_json_sao_validos(nome):
    # smoke test, so pra garantir que os json nao quebraram
    d = _load(nome)
    assert isinstance(d, dict)
    assert len(d) > 0
