from src.schemas import CampoExtraido, Veredito


def test_campo_com_valor_string():
    c = CampoExtraido(
        valor="Rio Madeira",
        confianca=0.9,
        evidencia="descendo o Madeira",
        modelo_usado="qwen2.5:7b",
    )
    assert c.valor == "Rio Madeira"
    assert c.fora_do_gazetteer is False
    assert c.latencia_ms == 0


def test_campo_com_valor_lista_especies():
    c = CampoExtraido(
        valor=[{"nome": "tucunare", "evidencia": "peguei um tucunare"}],
        confianca=0.85,
        evidencia="",
        modelo_usado="gliner+qwen",
    )
    assert isinstance(c.valor, list)
    assert c.valor[0]["nome"] == "tucunare"


def test_campo_fora_do_gazetteer():
    # vocabulario aberto: mesmo valor sendo desconhecido do dict deve ser aceito
    c = CampoExtraido(
        valor="mapara",
        confianca=0.7,
        evidencia="peguei uma mapara",
        modelo_usado="qwen2.5:7b",
        fora_do_gazetteer=True,
    )
    assert c.fora_do_gazetteer is True
    assert c.valor == "mapara"  # nao perde o valor


def test_veredito_aceito():
    v = Veredito(aceito=True, razao="passou nas regras")
    assert v.aceito
    assert v.tipo_rejeicao is None


def test_veredito_rejeitado():
    v = Veredito(
        aceito=False,
        razao="evidencia nao alinha",
        tipo_rejeicao="evidencia_nao_alinha",
        sugestao_retry="revisa o trecho da transcricao",
    )
    assert not v.aceito
    assert v.tipo_rejeicao == "evidencia_nao_alinha"


def test_tipo_rejeicao_nao_inclui_fora_gazetteer():
    # regra dura do projeto: fora_do_gazetteer NAO eh motivo pra rejeitar
    # o literal do tipo_rejeicao nao deve aceitar essa string
    # (se alguem adicionar de volta o teste quebra e a pessoa lembra da regra)
    from typing import get_args
    from src.schemas import TipoRejeicao

    tipos_validos = get_args(TipoRejeicao)
    assert "valor_fora_gazetteer" not in tipos_validos
    assert "evidencia_nao_alinha" in tipos_validos
    assert "alucinacao_suspeita" in tipos_validos
