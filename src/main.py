import argparse
import csv
import json
import sqlite3
import traceback
from dataclasses import asdict
from pathlib import Path
from datetime import datetime

from src import config
from src.harvester import youtube as yt
from src.transcriber import whisper_turbo as wt
from src.extracao import qwen_extrator, gliner_client
from src.verificador import retry_loop


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
    pra_fazer = wt.pega_pra_transcrever(DB_PATH, limit=args.limit)
    print(f"tem {len(pra_fazer)} audios pra transcrever")

    ok = 0
    falhou = 0
    for i, v in enumerate(pra_fazer, 1):
        aud = Path(v["audio_path"])
        if not aud.exists():
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
            print(f"  deu ruim: {e}")
            traceback.print_exc()
            falhou += 1

    print(f"terminou. transcreveu {ok}, falhou {falhou}")


def _pega_pra_extrair(limit: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT video_id, transcricao_path, url, channel, published_at
        FROM videos WHERE status = 'transcrito' LIMIT ?
    """, (limit,))
    rows = [
        {"video_id": r[0], "transcricao_path": r[1], "url": r[2], "channel": r[3], "published_at": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


def _marca_extraido(video_id: str, resultado_path: Path):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("ALTER TABLE videos ADD COLUMN resultado_path TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE videos ADD COLUMN extraido_em TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        UPDATE videos SET resultado_path=?, status='extraido', extraido_em=?
        WHERE video_id=?
    """, (str(resultado_path), datetime.utcnow().isoformat(), video_id))
    conn.commit()
    conn.close()


def cmd_extrair(args):
    # roda qwen + gliner em cada transcricao
    pra_fazer = _pega_pra_extrair(args.limit)
    print(f"tem {len(pra_fazer)} transcricoes pra extrair")

    ok = 0
    falhou = 0
    for i, v in enumerate(pra_fazer, 1):
        tp = Path(v["transcricao_path"])
        if not tp.exists():
            print(f"transcricao sumiu: {tp}")
            falhou += 1
            continue

        print(f"[{i}/{len(pra_fazer)}] extraindo {v['video_id']}")
        try:
            with open(tp, encoding="utf-8") as f:
                transc = json.load(f)
            texto = transc["texto"]

            campos = qwen_extrator.extrai_campos(texto, gliner_checkpoint=args.gliner_ckpt)

            # salva resultado bruto (pre-verificador)
            out_path = config.RESULTS_DIR / f"{v['video_id']}_extracao.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({
                    "video_id": v["video_id"],
                    "url": v["url"],
                    "canal": v["channel"],
                    "publicado_em": v["published_at"],
                    "campos": {k: asdict(c) for k, c in campos.items()},
                    "verificado": False,
                }, f, ensure_ascii=False, indent=2)

            _marca_extraido(v["video_id"], out_path)
            ok += 1
            print(f"  extraiu, latencia media {sum(c.latencia_ms for c in campos.values()) // len(campos)}ms")
        except Exception as e:
            print(f"  deu ruim: {e}")
            traceback.print_exc()
            falhou += 1

    print(f"terminou. extraiu {ok}, falhou {falhou}")


def _pega_pra_verificar(limit: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT video_id, transcricao_path, resultado_path
        FROM videos WHERE status = 'extraido' LIMIT ?
    """, (limit,))
    rows = [{"video_id": r[0], "transcricao_path": r[1], "resultado_path": r[2]} for r in cur.fetchall()]
    conn.close()
    return rows


def _marca_verificado(video_id: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("ALTER TABLE videos ADD COLUMN verificado_em TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        UPDATE videos SET status='verificado', verificado_em=?
        WHERE video_id=?
    """, (datetime.utcnow().isoformat(), video_id))
    conn.commit()
    conn.close()


def cmd_verificar(args):
    # passa os campos pelo verificador (regras + critic)
    from src.schemas import CampoExtraido

    pra_fazer = _pega_pra_verificar(args.limit)
    print(f"tem {len(pra_fazer)} extracoes pra verificar")

    ok = 0
    for i, v in enumerate(pra_fazer, 1):
        tp = Path(v["transcricao_path"])
        rp = Path(v["resultado_path"])
        if not tp.exists() or not rp.exists():
            print(f"arquivo sumiu: {tp} ou {rp}")
            continue

        print(f"[{i}/{len(pra_fazer)}] verificando {v['video_id']}")

        with open(tp, encoding="utf-8") as f:
            transc = json.load(f)
        with open(rp, encoding="utf-8") as f:
            extracao = json.load(f)

        # reconstroi CampoExtraido
        campos = {
            nome: CampoExtraido(**dados)
            for nome, dados in extracao["campos"].items()
        }

        # passa pelo loop de verificacao
        spans = gliner_client.extrai_por_label(transc["texto"], checkpoint_path=args.gliner_ckpt)
        resultado_verif = retry_loop.verifica_todos_os_campos(campos, transc["texto"], spans)

        # atualiza o arquivo de extracao com os vereditos
        extracao["verificado"] = True
        extracao["campos"] = {
            nome: asdict(info["campo"]) for nome, info in resultado_verif.items()
        }
        extracao["vereditos"] = {
            nome: {
                "aceito": info["veredito"].aceito,
                "razao": info["veredito"].razao,
                "tipo_rejeicao": info["veredito"].tipo_rejeicao,
                "tentativas": info["tentativas"],
            }
            for nome, info in resultado_verif.items()
        }

        with open(rp, "w", encoding="utf-8") as f:
            json.dump(extracao, f, ensure_ascii=False, indent=2)

        _marca_verificado(v["video_id"])
        ok += 1
        # resumo curto
        rejeitados = [n for n, i in resultado_verif.items() if not i["veredito"].aceito]
        if rejeitados:
            print(f"  rejeitados apos retries: {rejeitados}")

    print(f"terminou. verificou {ok}")


def cmd_exportar(args):
    # gera csv com os dados finais, pronto pra planilha
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT video_id, url, channel, published_at, resultado_path
        FROM videos WHERE status IN ('extraido', 'verificado')
    """)
    linhas = cur.fetchall()
    conn.close()

    out_csv = config.RESULTS_DIR / f"planilha_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"

    cols = [
        "plataforma", "autor", "link", "data_publicacao",
        "estado", "municipio", "rio", "bacia",
        "tipo_ceva", "grao", "especies", "observacoes",
        "verificado", "flags_fora_do_gazetteer",
    ]

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)

        for video_id, url, canal, pub_at, rp in linhas:
            if not rp or not Path(rp).exists():
                continue

            with open(rp, encoding="utf-8") as fh:
                d = json.load(fh)

            campos = d.get("campos", {})
            flags_fora = [
                nome for nome, c in campos.items()
                if c.get("fora_do_gazetteer")
            ]

            # especies como texto separado por ;
            especies_raw = campos.get("especies", {}).get("valor", []) or []
            if isinstance(especies_raw, list):
                especies_txt = "; ".join(
                    (e.get("nome") if isinstance(e, dict) else str(e))
                    for e in especies_raw
                )
            else:
                especies_txt = str(especies_raw)

            w.writerow([
                "YouTube",
                canal or "",
                url,
                (pub_at or "")[:7],  # so YYYY-MM
                campos.get("estado", {}).get("valor") or "",
                campos.get("municipio", {}).get("valor") or "",
                campos.get("rio", {}).get("valor") or "",
                campos.get("bacia", {}).get("valor") or "",
                campos.get("tipo_ceva", {}).get("valor") or "",
                campos.get("grao", {}).get("valor") or "",
                especies_txt,
                campos.get("observacoes", {}).get("valor") or "",
                "sim" if d.get("verificado") else "nao",
                ",".join(flags_fora),
            ])

    print(f"salvo em {out_csv}")


def cmd_status(args):
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

    bp = sub.add_parser("buscar")
    bp.add_argument("--queries", nargs="+", default=["pesca com ceva", "pescaria ceva"])
    bp.add_argument("--max-por-query", type=int, default=50)
    bp.add_argument("--ultimos-anos", type=int, default=10)
    bp.set_defaults(func=cmd_buscar)

    dp = sub.add_parser("baixar")
    dp.add_argument("--limit", type=int, default=50)
    dp.set_defaults(func=cmd_baixar)

    tp = sub.add_parser("transcrever")
    tp.add_argument("--limit", type=int, default=50)
    tp.set_defaults(func=cmd_transcrever)

    ep = sub.add_parser("extrair")
    ep.add_argument("--limit", type=int, default=50)
    ep.add_argument("--gliner-ckpt", default=None, help="caminho pro fine-tuned, deixa em branco pra zero-shot")
    ep.set_defaults(func=cmd_extrair)

    vp = sub.add_parser("verificar")
    vp.add_argument("--limit", type=int, default=50)
    vp.add_argument("--gliner-ckpt", default=None)
    vp.set_defaults(func=cmd_verificar)

    xp = sub.add_parser("exportar")
    xp.set_defaults(func=cmd_exportar)

    sp = sub.add_parser("status")
    sp.set_defaults(func=cmd_status)

    args = p.parse_args()

    if args.cmd in ("buscar",):
        config.checa_keys()

    args.func(args)


if __name__ == "__main__":
    main()
