#!/usr/bin/env python3
# smoke test do retry de schema errado.
# roda o extrator em N transcricoes ja existentes, mostra quantos
# videos dispararam retry, quantos deram bom, quantos falharam.
#
# uso: .venv/bin/python scripts/testar-retry-schema.py --limit 10

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config, ui_banners
from src.extracao import qwen_extrator


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--out", type=Path, default=Path("docs/teste-retry-schema"))
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    print(ui_banners.caixa("smoke test: retry de schema errado", [
        f"modelo extrator: {config.MODEL_EXTRATOR}",
        f"videos a processar: {args.limit}",
        f"salvando resultados em: {args.out}",
    ]))

    transcrs = sorted(config.TRANSCR_DIR.glob("*.json"))[:args.limit]
    if not transcrs:
        print("sem transcricoes, rode make transcrever primeiro")
        return

    qwen_extrator.reset_stats_retry()
    t_inicio = time.time()

    for i, t in enumerate(transcrs, 1):
        try:
            data = json.loads(t.read_text(encoding="utf-8"))
            texto = data.get("texto", "")
            print(f"\n   ><(((o>  [{i}/{len(transcrs)}] {t.stem} ({len(texto.split())} palavras)")
            t0 = time.time()
            campos = qwen_extrator.extrai_campos(texto)
            elapsed = time.time() - t0
            # salva resultado parcial pra revisao
            out_json = {
                "video_id": t.stem,
                "latencia_s": round(elapsed, 2),
                "campos": {k: asdict(v) for k, v in campos.items()},
            }
            (args.out / f"{t.stem}.json").write_text(
                json.dumps(out_json, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"      FALHOU: {type(e).__name__}: {e}")

    stats = qwen_extrator.get_stats_retry()
    elapsed_total = time.time() - t_inicio
    n = len(transcrs)

    print()
    linhas = [
        f"videos processados:    {n}",
        f"tempo total:           {elapsed_total:.1f}s  (media {elapsed_total/n:.1f}s/video)",
        "",
        f"videos com retry:      {stats['videos_com_retry']}  ({stats['videos_com_retry']/n*100:.0f}%)",
        f"retries ok (novo):     {stats['retries_ok']}",
        f"retries falhos (1o):   {stats['retries_falhos']}",
    ]
    print(ui_banners.caixa("resultado do smoke test", linhas))

    # salva sumario em arquivo
    (args.out / "_sumario.json").write_text(
        json.dumps({
            "n": n,
            "elapsed_s": round(elapsed_total, 1),
            "stats_retry": stats,
            "modelo": config.MODEL_EXTRATOR,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"sumario salvo em {args.out}/_sumario.json")


if __name__ == "__main__":
    main()
