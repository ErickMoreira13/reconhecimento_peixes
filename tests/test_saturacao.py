from src.harvester import saturacao


def test_dedup_rate_vazio():
    # sem resultados, rate = 0
    assert saturacao.calcula_dedup_rate([], set()) == 0.0


def test_dedup_rate_todos_novos():
    resultados = [{"video_id": "a"}, {"video_id": "b"}, {"video_id": "c"}]
    ja_vistos: set = set()
    assert saturacao.calcula_dedup_rate(resultados, ja_vistos) == 0.0


def test_dedup_rate_todos_repetidos():
    resultados = [{"video_id": "a"}, {"video_id": "b"}]
    ja_vistos = {"a", "b"}
    assert saturacao.calcula_dedup_rate(resultados, ja_vistos) == 1.0


def test_dedup_rate_parcial():
    # 2 repetidos de 4 total = 0.5
    resultados = [{"video_id": str(i)} for i in range(4)]
    ja_vistos = {"0", "1"}
    assert saturacao.calcula_dedup_rate(resultados, ja_vistos) == 0.5


def test_esta_saturada_por_dedup_threshold():
    # threshold 0.8
    assert saturacao.esta_saturada_por_dedup(0.8) is True
    assert saturacao.esta_saturada_por_dedup(0.9) is True
    assert saturacao.esta_saturada_por_dedup(0.79) is False
    assert saturacao.esta_saturada_por_dedup(0.0) is False


def test_rejeicao_rate_vazio():
    assert saturacao.calcula_rejeicao_rate([]) == 0.0


def test_rejeicao_rate_conta_por_campo():
    # cada verificacao eh um dict {campo: veredito{aceito: bool}}
    verificacoes = [
        {"rio": {"aceito": False}, "estado": {"aceito": True}},
        {"rio": {"aceito": False}, "especies": {"aceito": True}},
    ]
    # 2 rejeitados de 4 = 0.5
    assert saturacao.calcula_rejeicao_rate(verificacoes) == 0.5


def test_rejeicao_rate_ignora_non_dict():
    # robustez: se veredito vier mal formatado, ignora em vez de crashar
    verificacoes = [
        {"rio": {"aceito": False}},
        "isso_nao_eh_dict",  # ignora
        {"estado": "string_tb_ignora"},
    ]
    # so 1 campo valido, rejeitado
    assert saturacao.calcula_rejeicao_rate(verificacoes) == 1.0


def test_diagnostica_dedup_alto_tem_prioridade():
    # se dedup + rejeicao ambos altos, reporta dedup primeiro
    sat, motivo = saturacao.diagnostica(dedup_rate=0.9, rejeicao_rate=0.9)
    assert sat is True
    assert motivo == "dedup_alto"


def test_diagnostica_so_rejeicao_alta():
    sat, motivo = saturacao.diagnostica(dedup_rate=0.2, rejeicao_rate=0.8)
    assert sat is True
    assert motivo == "rejeicao_alta"


def test_diagnostica_nenhum_saturou():
    sat, motivo = saturacao.diagnostica(dedup_rate=0.3, rejeicao_rate=0.4)
    assert sat is False
    assert motivo is None
