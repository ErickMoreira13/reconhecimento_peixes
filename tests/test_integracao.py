import json
from dataclasses import asdict

import pytest

from src.schemas import CampoExtraido, Veredito
from src.verificador import regras, retry_loop


TRANSC_REAL = """
fala galera, hoje eu tenho uma ceva incrivel pra voces.
peguei uma garrafa pet, furei e botei farelo de milho dentro.
joguei na beira do rio madeira la em porto velho, rondonia.
peguei um tambaqui de uns 5 kg e 2 tucunares tambem.
de manha bem cedo, agua turva, deu muito peixe.
""".strip()


def test_regras_aceita_extracao_coerente():
    # simula uma extracao que o llm fez bem, todos os campos plausiveis
    campos = {
        "estado": CampoExtraido(valor="RO", confianca=0.9, evidencia="rondonia",
                               modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "municipio": CampoExtraido(valor="Porto Velho", confianca=0.85, evidencia="porto velho",
                                  modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "rio": CampoExtraido(valor="Rio Madeira", confianca=0.9, evidencia="rio madeira",
                            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "bacia": CampoExtraido(valor=None, confianca=0.0, evidencia="",
                              modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "tipo_ceva": CampoExtraido(valor="garrafa_pet_perfurada", confianca=0.95,
                                  evidencia="garrafa pet, furei",
                                  modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "grao": CampoExtraido(valor="milho", confianca=0.9, evidencia="farelo de milho",
                             modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "especies": CampoExtraido(
            valor=[{"nome": "tambaqui", "evidencia": "tambaqui de uns 5 kg"},
                   {"nome": "tucunare", "evidencia": "2 tucunares tambem"}],
            confianca=0.95, evidencia="", modelo_usado="t",
            fora_do_gazetteer=False, latencia_ms=0,
        ),
        "observacoes": CampoExtraido(
            valor="pescaria de manha com ceva de garrafa pet e milho, resultado bom com tambaqui e tucunare",
            confianca=0.8, evidencia="de manha bem cedo",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
    }

    for nome, c in campos.items():
        v = regras.aplica_regras(nome, c, TRANSC_REAL, {})
        assert v.aceito, f"regra rejeitou {nome}: {v.razao}"


def test_regras_rejeita_alucinacao_completa():
    # extrator inventou campo sem base no texto
    campos = {
        "estado": CampoExtraido(
            valor="SP", confianca=0.9,
            evidencia="manha ensolarada linda",  # evidencia irrelevante
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
    }
    v = regras.aplica_regras("estado", campos["estado"], TRANSC_REAL, {})
    assert not v.aceito
    assert v.tipo_rejeicao == "evidencia_nao_alinha"


def test_integracao_verificador_com_mock_critic(monkeypatch):
    # pipeline de verificacao completo com critic mockado
    from src.verificador import critic

    campos = {
        "estado": CampoExtraido(valor="RO", confianca=0.9, evidencia="rondonia",
                               modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "grao": CampoExtraido(valor="milho", confianca=0.9, evidencia="farelo de milho",
                             modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "tipo_ceva": CampoExtraido(valor="garrafa_pet_perfurada", confianca=0.95,
                                  evidencia="garrafa pet",
                                  modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "rio": CampoExtraido(valor=None, confianca=0.0, evidencia="",
                            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "bacia": CampoExtraido(valor=None, confianca=0.0, evidencia="",
                              modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "municipio": CampoExtraido(valor=None, confianca=0.0, evidencia="",
                                  modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0),
        "especies": CampoExtraido(
            valor=[{"nome": "tambaqui", "evidencia": "tambaqui"}],
            confianca=0.9, evidencia="", modelo_usado="t",
            fora_do_gazetteer=False, latencia_ms=0,
        ),
        "observacoes": CampoExtraido(
            valor="pescaria de manha cedo com garrafa pet dando bom resultado com tambaqui",
            confianca=0.8, evidencia="pescaria de manha",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
    }

    # critic aceita tudo
    monkeypatch.setattr(critic, "avalia_batch",
                        lambda campos, transc: {n: Veredito(aceito=True, razao="ok") for n in campos})

    resultado = retry_loop.verifica_todos_os_campos(campos, TRANSC_REAL, {})

    # tudo que foi extraido deve estar aceito
    assert resultado["estado"]["veredito"].aceito
    assert resultado["grao"]["veredito"].aceito
    assert resultado["tipo_ceva"]["veredito"].aceito
    # campos null tb aceitos (nada pra verificar)
    assert resultado["rio"]["veredito"].aceito


def test_json_serializacao_campo_extraido():
    # garante que CampoExtraido pode ser serializado pra json (asdict) e voltar
    c = CampoExtraido(
        valor="teste", confianca=0.5, evidencia="ev",
        modelo_usado="m", fora_do_gazetteer=True, latencia_ms=100,
    )
    d = asdict(c)
    j = json.dumps(d, ensure_ascii=False)
    dd = json.loads(j)
    c2 = CampoExtraido(**dd)
    assert c2.valor == "teste"
    assert c2.fora_do_gazetteer is True
