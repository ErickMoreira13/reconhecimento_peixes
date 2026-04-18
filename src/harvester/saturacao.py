# detectores de saturacao pro harvester loop
#
# uma query "satura" quando a gente para de ganhar sinal com ela. dois sinais:
#
# 1. dedup_rate: dos N ultimos resultados da busca, quantos ja tavam no sqlite?
#    se >= 0.8 a query ta esgotada, youtube nao tem mais video novo pra ela
#
# 2. rejeicao_rate: dos campos extraidos no ultimo batch verificado, quantos
#    foram rejeitados pelo verificador? se > 0.7 a query ta trazendo video fora
#    de dominio (pesca no mar, aquario, etc)
#
# esses thresholds sao chutes iniciais. se sair muito falso positivo eu ajusto.


DEDUP_SATURA = 0.8
REJEICAO_SATURA = 0.7


def calcula_dedup_rate(resultados_busca: list[dict], ja_vistos: set[str]) -> float:
    # resultados_busca eh a lista que veio do youtube (cada um com video_id)
    # ja_vistos eh set de video_ids q existem no sqlite antes dessa busca
    # retorna float 0-1
    if not resultados_busca:
        return 0.0
    n = len(resultados_busca)
    repetidos = sum(1 for r in resultados_busca if r.get("video_id") in ja_vistos)
    return repetidos / n


def esta_saturada_por_dedup(dedup_rate: float) -> bool:
    return dedup_rate >= DEDUP_SATURA


def calcula_rejeicao_rate(verificacoes: list[dict]) -> float:
    # verificacoes eh lista de dicts do verificador, cada um com {campo: veredito}
    # onde veredito tem chave 'aceito' bool
    # conta total de campos e quantos rejeitados
    # retorna 0.0 se lista vazia
    total = 0
    rejeitados = 0
    for v in verificacoes:
        if not isinstance(v, dict):
            continue
        for _campo, veredito in v.items():
            if not isinstance(veredito, dict):
                continue
            total += 1
            if not veredito.get("aceito", True):
                rejeitados += 1
    if total == 0:
        return 0.0
    return rejeitados / total


def esta_saturada_por_rejeicao(rejeicao_rate: float) -> bool:
    return rejeicao_rate > REJEICAO_SATURA


def diagnostica(dedup_rate: float, rejeicao_rate: float) -> tuple[bool, str | None]:
    # retorna (saturou, motivo). motivo None se nao saturou
    if esta_saturada_por_dedup(dedup_rate):
        return True, "dedup_alto"
    if esta_saturada_por_rejeicao(rejeicao_rate):
        return True, "rejeicao_alta"
    return False, None
