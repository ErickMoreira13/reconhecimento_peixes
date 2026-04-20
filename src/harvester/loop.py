# harvester em loop perpetuo.
#
# fluxo de uma iteracao:
#   1. pega query ativa do sqlite (a com menos total_buscados primeiro)
#   2. busca N videos via youtube api
#   3. mede dedup_rate contra video_ids ja no db
#   4. se dedup_rate >= 0.8 -> marca query como saturada (dedup_alto), pula
#   5. senao, upsert os novos no db, atualiza contadores da query
#   6. sleep curto pra respeitar rate limit, vai pra proxima iteracao
#
# a extracao/verificacao roda em processos separados (make extrair/verificar)
# depois. mas o loop tb pode disparar esses passos se flag --completo.
#
# quando todas as queries saturam, o loop imprime relatorio e sai.

import argparse
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from src.harvester import youtube as yt
from src.harvester import saturacao
from src.log import get_logger
from src.storage import db as storage
from src import ui_banners


_log = get_logger()


PAUSA_ENTRE_BUSCAS_S = 5  # respeitar api
BATCH_POR_QUERY = 50       # quantos videos pedir por busca


def carrega_queries_yaml(path: Path) -> list[str]:
    if yaml is None:
        raise RuntimeError("falta yaml, instala pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("queries", [])


def ids_ja_vistos(db_path: Path | None = None) -> set[str]:
    # carrega todos os video_ids do sqlite pra detectar dedup
    # pra 2000 videos eh rapido, se passar de 100k convem cachear em memoria
    with storage.conectar(db_path) as conn:
        rows = conn.execute("SELECT video_id FROM videos").fetchall()
    return {r[0] for r in rows}


def processa_query(query: str, db_path: Path | None = None) -> dict:
    # retorna dict com {resultados, dedup_rate, novos, saturou, motivo}
    # nao marca a query saturada aqui -- deixa pro caller decidir
    print(f"[loop] buscando '{query}'")
    try:
        resultados = yt.busca_videos(query, max_videos=BATCH_POR_QUERY)
    except Exception as e:
        # youtube as vezes rate-limita ou tem instabilidade, nao mata o loop
        _log.warning("[loop] busca deu erro: %s", e)
        return {"resultados": [], "dedup_rate": 0.0, "novos": 0, "saturou": False, "motivo": None}

    ja = ids_ja_vistos(db_path)
    dedup_rate = saturacao.calcula_dedup_rate(resultados, ja)
    novos = [r for r in resultados if r.get("video_id") not in ja]

    if novos:
        yt.salva_metadata(novos, db_path or storage.DB_PATH)

    # atualiza contadores
    storage.atualiza_query(query, {
        "total_buscados": len(resultados),
        "total_novos": len(novos),
        "dedup_rate_ultima": dedup_rate,
    }, db_path)

    saturou, motivo = saturacao.diagnostica(dedup_rate, rejeicao_rate=0.0)
    return {
        "resultados": resultados,
        "dedup_rate": dedup_rate,
        "novos": len(novos),
        "saturou": saturou,
        "motivo": motivo,
    }


def roda_loop(
    queries_yaml: Path,
    max_iteracoes: int | None = None,
    pausa_s: int = PAUSA_ENTRE_BUSCAS_S,
    db_path: Path | None = None,
):
    print(ui_banners.banner_harvester())
    # carrega queries do yaml pro sqlite (idempotente)
    textos = carrega_queries_yaml(queries_yaml)
    storage.upsert_queries(textos, db_path)
    print(f"[loop] {len(textos)} queries no yaml, storage pronto")

    it = 0
    while True:
        if max_iteracoes is not None and it >= max_iteracoes:
            print(f"[loop] atingiu max_iteracoes={max_iteracoes}, parando")
            break

        q = storage.pega_query_ativa(db_path)
        if q is None:
            print("[loop] nenhuma query ativa sobrou, parando")
            break

        res = processa_query(q, db_path)
        print(f"[loop] '{q}': +{res['novos']} novos, dedup={res['dedup_rate']:.2f}")

        if res["saturou"]:
            print(f"[loop] '{q}' saturou ({res['motivo']}), marcando")
            storage.marca_query_saturada(q, res["motivo"] or "desconhecido", db_path)

        it += 1
        time.sleep(pausa_s)

    # relatorio final
    ativas = storage.lista_queries("ativa", db_path)
    satur = storage.lista_queries("saturada", db_path)
    print(ui_banners.caixa("fim do loop", [
        f"iteracoes:  {it}",
        f"ativas:     {len(ativas)}",
        f"saturadas:  {len(satur)}",
    ]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, default=Path("data/queries.yaml"))
    p.add_argument("--max-iter", type=int, default=None, help="pra teste, roda N vezes e para")
    p.add_argument("--pausa", type=int, default=PAUSA_ENTRE_BUSCAS_S)
    args = p.parse_args()

    roda_loop(args.queries, max_iteracoes=args.max_iter, pausa_s=args.pausa)


if __name__ == "__main__":
    main()
