import pytest

from src.schemas import CampoExtraido
from src.extracao.gazetteer_check import (
    esta_no_gazetteer, aplica_flag_fora_do_gazetteer, _normaliza,
)


def test_normaliza_remove_acento_e_baixa():
    assert _normaliza("Tucunaré") == "tucunare"
    assert _normaliza("BAHIA") == "bahia"
    assert _normaliza("  espaco  ") == "espaco"


def test_estado_uf_valido():
    assert esta_no_gazetteer("estado", "RO") is True
    assert esta_no_gazetteer("estado", "SP") is True


def test_estado_uf_invalido():
    assert esta_no_gazetteer("estado", "XX") is False
    assert esta_no_gazetteer("estado", "BRA") is False


def test_estado_null_passa():
    assert esta_no_gazetteer("estado", None) is True


def test_especies_conhecidas_ficam_dentro():
    esp = [{"nome": "tucunare"}, {"nome": "tilapia"}]
    assert esta_no_gazetteer("especies", esp) is True


def test_especies_gazetteer_tem_acento_nao_atrapalha():
    # whisper cuspe sem acento, dict tem com acento
    esp = [{"nome": "tucunare"}, {"nome": "traira"}]
    assert esta_no_gazetteer("especies", esp) is True


def test_especies_inventada_fica_fora():
    # "filapossauro" eh o caso classico de alucinacao que a gente viu
    esp = [{"nome": "filapossauro"}]
    assert esta_no_gazetteer("especies", esp) is False


def test_grao_conhecido():
    assert esta_no_gazetteer("grao", "milho") is True
    assert esta_no_gazetteer("grao", "soja") is True


def test_grao_desconhecido():
    assert esta_no_gazetteer("grao", "amendoim") is False


def test_tipo_ceva_categoria_valida():
    assert esta_no_gazetteer("tipo_ceva", "garrafa_pet_perfurada") is True
    assert esta_no_gazetteer("tipo_ceva", "ceva_de_chao") is True


def test_tipo_ceva_livre_fica_fora():
    # se o modelo cuspir texto livre (nao categoria canonica), fica fora
    assert esta_no_gazetteer("tipo_ceva", "gororoba do joao") is False


def test_observacoes_campo_livre_sempre_passa():
    # observacoes eh texto livre, nao checamos
    assert esta_no_gazetteer("observacoes", "qualquer texto aqui") is True


def test_municipio_campo_livre_sempre_passa():
    # municipio eh string livre (5570 no ibge, nao colocamos no dict)
    assert esta_no_gazetteer("municipio", "Porto Velho") is True


def test_aplica_flag_marca_especies_inventadas():
    campos = {
        "especies": CampoExtraido(
            valor=[{"nome": "filapossauro", "evidencia": ""}],
            confianca=0.9, evidencia="", modelo_usado="t",
            fora_do_gazetteer=False,  # llm disse false
            latencia_ms=0,
        ),
        "grao": CampoExtraido(
            valor="amendoim", confianca=0.9, evidencia="",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
        "estado": CampoExtraido(
            valor="RO", confianca=0.9, evidencia="",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
    }
    aplica_flag_fora_do_gazetteer(campos)
    assert campos["especies"].fora_do_gazetteer is True  # filapossauro fora
    assert campos["grao"].fora_do_gazetteer is True       # amendoim fora
    assert campos["estado"].fora_do_gazetteer is False    # RO dentro


def test_aplica_flag_pula_campos_livres():
    campos = {
        "observacoes": CampoExtraido(
            valor="pescaria boa", confianca=0.7, evidencia="",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
        "municipio": CampoExtraido(
            valor="Cáceres", confianca=0.8, evidencia="",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
    }
    aplica_flag_fora_do_gazetteer(campos)
    # campos livres mantem false
    assert campos["observacoes"].fora_do_gazetteer is False
    assert campos["municipio"].fora_do_gazetteer is False


def test_aplica_flag_null_mantem_false():
    # valor null nao precisa validar
    campos = {
        "estado": CampoExtraido(
            valor=None, confianca=0.0, evidencia="",
            modelo_usado="t", fora_do_gazetteer=False, latencia_ms=0,
        ),
    }
    aplica_flag_fora_do_gazetteer(campos)
    assert campos["estado"].fora_do_gazetteer is False
