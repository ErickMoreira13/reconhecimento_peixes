import argparse
import traceback
from pathlib import Path

from src import config
from src.harvester import youtube as yt
from src.transcriber import whisper_turbo as wt


DB_PATH = config.DATA_DIR / "videos.db"


def cmd_buscar(args):
    # junta todas as queries num so db, nao precisa separar
    todos = []
    for q in args.queries:
        print(f"buscando '{q}' ate {args.max_por_query} videos...")
        vids = yt.busca_videos(q, max_videos=args.max_por_query, ultimos_anos=args.ultimos_anos)
        print(f"  -> {len(vids)} videos achados")
        todos.extend(vids)

    if not todos:
        print("nao achou nada, encerra")
        return

    yt.salva_metadata(todos, DB_PATH)
    print(f"total: {len(todos)} videos salvos no db")


def cmd_baixar(args):
    # baixa os que estao como 'pendente' no db
    pendentes = yt.pega_pendentes(DB_PATH, limit=args.limit)
    print(f"tem {len(pendentes)} videos pra baixar")

    ok = 0
    falhou = 0
    for i, v in enumerate(pendentes, 1):
        print(f"[{i}/{len(pendentes)}] {v['video_id']}")
        audio = yt.baixa_audio(v["url"], config.RAW_AUDIO_DIR)
        if audio:
            yt.marca_baixado(v["video_id"], audio, DB_PATH)
            ok += 1
        else:
            yt.marca_falhou(v["video_id"], DB_PATH)
            falhou += 1

    print(f"terminou. baixou {ok}, falhou {falhou}")


def cmd_transcrever(args):
    # transcreve os que estao como 'baixado'
    pra_fazer = wt.pega_pra_transcrever(DB_PATH, limit=args.limit)
    print(f"tem {len(pra_fazer)} audios pra transcrever")

    ok = 0
    falhou = 0
    for i, v in enumerate(pra_fazer, 1):
        aud = Path(v["audio_path"])
        if not aud.exists():
            # alguem apagou o audio, marca falhou
            print(f"audio sumiu: {aud}")
            falhou += 1
            continue

        print(f"[{i}/{len(pra_fazer)}] {v['video_id']} ({aud.name})")
        try:
            resultado = wt.transcreve(aud)
            out = wt.salva_transcricao(v["video_id"], resultado, config.TRANSCR_DIR)
            wt.marca_transcrito(v["video_id"], out, DB_PATH)
            ok += 1
            print(f"  ok, {resultado['duracao_seg']}s de audio, {len(resultado['segmentos'])} segmentos")
        except Exception as e:
            # nao para o loop se um video falha
            print(f"  deu ruim: {e}")
            traceback.print_exc()
            falhou += 1

    print(f"terminou. transcreveu {ok}, falhou {falhou}")


def cmd_status(args):
    # resumo rapido do que tem no db
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM videos GROUP BY status")
    rows = cur.fetchall()
    conn.close()

    print("status do pipeline:")
    for st, n in rows:
        print(f"  {st}: {n}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    # buscar
    bp = sub.add_parser("buscar", help="busca videos no youtube e salva metadata")
    bp.add_argument("--queries", nargs="+", default=["pesca com ceva", "pescaria ceva"])
    bp.add_argument("--max-por-query", type=int, default=50)
    bp.add_argument("--ultimos-anos", type=int, default=10)
    bp.set_defaults(func=cmd_buscar)

    # baixar
    dp = sub.add_parser("baixar", help="baixa audio dos videos pendentes")
    dp.add_argument("--limit", type=int, default=50)
    dp.set_defaults(func=cmd_baixar)

    # transcrever
    tp = sub.add_parser("transcrever", help="transcreve os audios baixados")
    tp.add_argument("--limit", type=int, default=50)
    tp.set_defaults(func=cmd_transcrever)

    # status
    sp = sub.add_parser("status", help="mostra contagem por status")
    sp.set_defaults(func=cmd_status)

    args = p.parse_args()

    # checa as keys antes de qualquer coisa que use api
    if args.cmd in ("buscar",):
        config.checa_keys()

    args.func(args)


if __name__ == "__main__":
    main()
