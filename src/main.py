import argparse
import csv
import json
import traceback
from dataclasses import asdict
from pathlib import Path
from src.utils.tempo import agora_iso, agora_compact

from src import ascii_art, config, ui
from src.harvester import youtube as yt
from src.transcriber import whisper_turbo as wt
from src.extracao import qwen_extrator, gliner_client
from src.schemas import CAMPOS_PIPELINE
from src.verificador import retry_loop
from src.storage import db as storage


DB_PATH = storage.DB_PATH


def cmd_buscar(args):
    print(ascii_art.banner_pipeline("buscar videos no youtube"))
    todos = []
    with ui.progresso(len(args.queries), "queries") as (prog, task):
        for q in args.queries:
            ui.info(f"buscando '{q}' ate {args.max_por_query} videos...")
            vids = yt.busca_videos(q, max_videos=args.max_por_query, ultimos_anos=args.ultimos_anos)
            ui.ok(f"  -> {len(vids)} videos achados")
            todos.extend(vids)
            prog.advance(task)

    if not todos:
        ui.aviso("nao achou nada, encerra")
        return

    yt.salva_metadata(todos, DB_PATH)
    ui.ok(f"total: {len(todos)} videos salvos no db")


def cmd_baixar(args):
    print(ascii_art.banner_pipeline("baixar audio dos videos"))
    pendentes = yt.pega_pendentes(DB_PATH, limit=args.limit)
    ui.info(f"tem {len(pendentes)} videos pra baixar")
    if not pendentes:
        return

    ok_count = 0
    falhou = 0

    if args.workers > 1:
        # paralelo inline: marca cada video NO DB assim que termina, nao espera
        # batch inteiro. se o processo morre no meio (timeout etc), o que ja
        # baixou ta persistido em vez de virar audio orfao
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ui.progresso(len(pendentes), "baixando (paralelo)") as (prog, task):
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {
                    pool.submit(yt.baixa_audio, v["url"], config.RAW_AUDIO_DIR): v
                    for v in pendentes
                }
                for fut in as_completed(futures):
                    v = futures[fut]
                    try:
                        audio = fut.result()
                    except Exception:
                        audio = None
                    if audio:
                        yt.marca_baixado(v["video_id"], audio, DB_PATH)
                        ok_count += 1
                    else:
                        yt.marca_falhou(v["video_id"], DB_PATH)
                        falhou += 1
                    prog.advance(task)
    else:
        # sequencial
        with ui.progresso(len(pendentes), "baixando") as (prog, task):
            for v in pendentes:
                audio = yt.baixa_audio(v["url"], config.RAW_AUDIO_DIR)
                if audio:
                    yt.marca_baixado(v["video_id"], audio, DB_PATH)
                    ok_count += 1
                else:
                    yt.marca_falhou(v["video_id"], DB_PATH)
                    falhou += 1
                prog.advance(task)

    ui.ok(f"baixou {ok_count}, falhou {falhou}")


def cmd_transcrever(args):
    print(ascii_art.banner_pipeline("transcrever audio (whisper)"))
    pra_fazer = wt.pega_pra_transcrever(DB_PATH, limit=args.limit)
    ui.info(f"tem {len(pra_fazer)} audios pra transcrever")
    if not pra_fazer:
        return

    ok_count = 0
    falhou = 0
    with ui.progresso(len(pra_fazer), "whisper") as (prog, task):
        for v in pra_fazer:
            aud = Path(v["audio_path"])
            if not aud.exists():
                ui.aviso(f"audio sumiu: {aud}")
                falhou += 1
                prog.advance(task)
                continue

            # audio gigante (10h+) trava o batch no whisper e estoura timeout
            # perdendo os outros 49 do ciclo. melhor pular. 150MB em opus 128k
            # eh ~2.5h de audio, ja e muito pra um video de pescaria normal
            tam_mb = aud.stat().st_size / 1024 / 1024
            if tam_mb > 150:
                prog.console.log(f"[yellow]pulando {v['video_id']}: audio muito grande ({tam_mb:.0f}MB)")
                yt.marca_falhou(v["video_id"], DB_PATH)
                try:
                    aud.unlink()
                except Exception:
                    pass
                falhou += 1
                prog.advance(task)
                continue

            try:
                resultado = wt.transcreve(aud)
                out = wt.salva_transcricao(v["video_id"], resultado, config.TRANSCR_DIR)
                wt.marca_transcrito(v["video_id"], out, DB_PATH)
                ok_count += 1
                prog.console.log(f"[green]ok[/] {v['video_id']} ({resultado['duracao_seg']}s)")
                # libera disco: audio so serve pro whisper. apos transcrever nao
                # precisa mais. transcricao fica no json. economiza ~17MB/video.
                # flag --keep-audio mantem se quiser re-transcrever depois
                if not getattr(args, "keep_audio", False):
                    try:
                        aud.unlink()
                    except Exception:
                        pass
            except Exception as e:
                prog.console.log(f"[red]deu ruim[/] {v['video_id']}: {e}")
                falhou += 1
            prog.advance(task)

    ui.ok(f"transcreveu {ok_count}, falhou {falhou}")


def _pega_pra_extrair(limit: int) -> list[dict]:
    return storage.pega_por_status(
        "transcrito", limit,
        ["video_id", "transcricao_path", "url", "channel", "published_at"],
    )


def _marca_extraido(video_id: str, resultado_path: Path):
    storage.atualiza(video_id, {
        "resultado_path": str(resultado_path),
        "status": "extraido",
        "extraido_em": agora_iso(),
    })


def cmd_extrair(args):
    print(ascii_art.banner_pipeline("extrair campos (gliner + qwen)"))
    pra_fazer = _pega_pra_extrair(args.limit)
    ui.info(f"tem {len(pra_fazer)} transcricoes pra extrair")
    if not pra_fazer:
        return

    ok_count = 0
    falhou = 0
    with ui.progresso(len(pra_fazer), "extraindo") as (prog, task):
        for v in pra_fazer:
            tp = Path(v["transcricao_path"])
            if not tp.exists():
                ui.aviso(f"transcricao sumiu: {tp}")
                falhou += 1
                prog.advance(task)
                continue

            try:
                with open(tp, encoding="utf-8") as f:
                    transc = json.load(f)
                texto = transc["texto"]

                campos = qwen_extrator.extrai_campos(
                    texto,
                    gliner_checkpoint=args.gliner_ckpt,
                    modelo=args.modelo,
                )

                suffix = f"_{args.suffix}" if args.suffix else ""
                out_path = config.RESULTS_DIR / f"{v['video_id']}_extracao{suffix}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "video_id": v["video_id"],
                        "url": v["url"],
                        "canal": v["channel"],
                        "publicado_em": v["published_at"],
                        "campos": {k: asdict(c) for k, c in campos.items()},
                        "verificado": False,
                    }, f, ensure_ascii=False, indent=2)

                # so marca como extraido quando nao tem suffix (benchmark nao muda status do db)
                if not args.suffix:
                    _marca_extraido(v["video_id"], out_path)
                ok_count += 1
                lat_med = sum(c.latencia_ms for c in campos.values()) // len(campos)
                prog.console.log(f"[green]ok[/] {v['video_id']} (lat med {lat_med}ms)")
            except Exception as e:
                prog.console.log(f"[red]deu ruim[/] {v['video_id']}: {e}")
                falhou += 1
            prog.advance(task)

    ui.ok(f"extraiu {ok_count}, falhou {falhou}")


def _pega_pra_verificar(limit: int) -> list[dict]:
    return storage.pega_por_status(
        "extraido", limit,
        ["video_id", "transcricao_path", "resultado_path"],
    )


def _marca_verificado(video_id: str):
    storage.atualiza(video_id, {
        "status": "verificado",
        "verificado_em": agora_iso(),
    })


def cmd_verificar(args):
    print(ascii_art.banner_pipeline("verificar extracoes (regras + critic)"))
    from src.schemas import CampoExtraido

    pra_fazer = _pega_pra_verificar(args.limit)
    ui.info(f"tem {len(pra_fazer)} extracoes pra verificar")
    if not pra_fazer:
        return

    ok_count = 0
    with ui.progresso(len(pra_fazer), "verificando") as (prog, task):
        for v in pra_fazer:
            tp = Path(v["transcricao_path"])
            rp = Path(v["resultado_path"])
            if not tp.exists() or not rp.exists():
                ui.aviso(f"arquivo sumiu: {tp} ou {rp}")
                prog.advance(task)
                continue

            with open(tp, encoding="utf-8") as f:
                transc = json.load(f)
            with open(rp, encoding="utf-8") as f:
                extracao = json.load(f)

            campos = {
                nome: CampoExtraido(**dados)
                for nome, dados in extracao["campos"].items()
            }

            spans = gliner_client.extrai_por_label(transc["texto"], checkpoint_path=args.gliner_ckpt)
            resultado_verif = retry_loop.verifica_todos_os_campos(campos, transc["texto"], spans)

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
            ok_count += 1

            rejeitados = [n for n, i in resultado_verif.items() if not i["veredito"].aceito]
            if rejeitados:
                prog.console.log(f"[yellow]{v['video_id']}[/] rejeitados pos-retry: {rejeitados}")
            else:
                prog.console.log(f"[green]ok[/] {v['video_id']}")
            prog.advance(task)

    ui.ok(f"verificou {ok_count}")


def cmd_exportar(args):
    print(ascii_art.banner_pipeline("exportar csv final"))
    with storage.conectar() as conn:
        linhas = conn.execute("""
            SELECT video_id, url, channel, published_at, resultado_path
            FROM videos WHERE status IN ('extraido', 'verificado')
        """).fetchall()

    if not linhas:
        ui.aviso("nao tem nada pra exportar, roda extrair/verificar antes")
        return

    out_csv = config.RESULTS_DIR / f"planilha_{agora_compact()}.csv"

    # header = metadata do video + 8 campos extraidos (SSOT em schemas) + flags
    cols = (
        ["plataforma", "autor", "link", "data_publicacao"]
        + list(CAMPOS_PIPELINE)
        + ["verificado", "flags_fora_do_gazetteer"]
    )

    escritos = 0
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
                (pub_at or "")[:7],
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
            escritos += 1

    ui.ok(f"salvo em {out_csv} ({escritos} linhas)")


def cmd_status(args):
    print(ascii_art.banner_projeto())
    rows = storage.contagem_por_status()
    if not rows:
        ui.aviso("db vazio, ainda nao rodou 'buscar'")
        return
    ui.tabela_status(rows)


def cmd_reconciliar(args):
    # fix pra videos orfaos: db diz uma coisa mas os arquivos em disco dizem outra
    ui.titulo("reconciliando status do db com arquivos em disco")
    mudancas = storage.reconcilia_status(config.RESULTS_DIR)
    if mudancas["marcados_extraido"]:
        ui.ok(f"{mudancas['marcados_extraido']} videos: status -> extraido (tinham arquivo mas status antigo)")
    if mudancas["voltados_transcrito"]:
        ui.aviso(f"{mudancas['voltados_transcrito']} videos: status -> transcrito (arquivo sumiu)")
    if not any(mudancas.values()):
        ui.ok("nada pra reconciliar, db ja ta consistente")


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
    dp.add_argument("--workers", type=int, default=4, help="threads paralelas, default 4")
    dp.set_defaults(func=cmd_baixar)

    tp = sub.add_parser("transcrever")
    tp.add_argument("--limit", type=int, default=50)
    tp.add_argument("--keep-audio", action="store_true",
                    help="nao deleta o .opus apos transcrever (default: deleta pra economizar disco)")
    tp.set_defaults(func=cmd_transcrever)

    ep = sub.add_parser("extrair")
    ep.add_argument("--limit", type=int, default=50)
    ep.add_argument("--gliner-ckpt", default=None)
    ep.add_argument("--modelo", default=None, help="sobrescreve MODEL_EXTRATOR do .env")
    ep.add_argument("--suffix", default="", help="sufixo no nome do json de saida (pra benchmark)")
    ep.set_defaults(func=cmd_extrair)

    vp = sub.add_parser("verificar")
    vp.add_argument("--limit", type=int, default=50)
    vp.add_argument("--gliner-ckpt", default=None)
    vp.set_defaults(func=cmd_verificar)

    xp = sub.add_parser("exportar")
    xp.set_defaults(func=cmd_exportar)

    sp = sub.add_parser("status")
    sp.set_defaults(func=cmd_status)

    rp = sub.add_parser("reconciliar", help="sincroniza status do db com arquivos em disco")
    rp.set_defaults(func=cmd_reconciliar)

    args = p.parse_args()

    if args.cmd in ("buscar",):
        config.checa_keys()

    args.func(args)


if __name__ == "__main__":
    main()
