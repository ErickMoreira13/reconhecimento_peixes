#!/usr/bin/env python3
# compara duas extracoes (ou uma extracao com o benchmark baseline)
# util pra rodar depois da validacao e ver diff lado a lado

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def carrega_extracoes(results_dir: Path, suffix: str = "") -> dict[str, dict]:
    # retorna {video_id: dict com campos}
    pat = f"*_extracao_{suffix}.json" if suffix else "*_extracao.json"
    out: dict[str, dict] = {}
    for p in results_dir.glob(pat):
        vid = p.stem.split("_extracao")[0]
        out[vid] = json.loads(p.read_text(encoding="utf-8"))
    return out


def cobertura(extracoes: dict[str, dict]) -> dict[str, int]:
    c: Counter = Counter()
    for d in extracoes.values():
        for nome, campo in d.get("campos", {}).items():
            v = campo.get("valor")
            if v not in (None, "", []):
                c[nome] += 1
    return dict(c)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a", required=True, help="primeiro set (sem suffix = resultado atual)")
    p.add_argument("--b", required=True, help="segundo set pra comparar")
    p.add_argument("--results-dir", default="data/results")
    p.add_argument("--out-csv", default=None)
    args = p.parse_args()

    results = Path(args.results_dir)

    ext_a = carrega_extracoes(results, args.a if args.a != "_default_" else "")
    ext_b = carrega_extracoes(results, args.b if args.b != "_default_" else "")

    print(f"set A ({args.a}): {len(ext_a)} videos")
    print(f"set B ({args.b}): {len(ext_b)} videos")

    cob_a = cobertura(ext_a)
    cob_b = cobertura(ext_b)

    print()
    print(f"{'campo':<15} {'A':>10} {'B':>10} {'delta':>10}")
    print("-" * 50)
    campos = sorted(set(cob_a) | set(cob_b))
    linhas = []
    for c in campos:
        a = cob_a.get(c, 0)
        b = cob_b.get(c, 0)
        pct_a = 100 * a / max(len(ext_a), 1)
        pct_b = 100 * b / max(len(ext_b), 1)
        delta = pct_b - pct_a
        sinal = "+" if delta > 0 else ""
        print(f"{c:<15} {a:>4} ({pct_a:3.0f}%) {b:>4} ({pct_b:3.0f}%) {sinal}{delta:>6.1f}pp")
        linhas.append({
            "campo": c,
            "a_count": a, "a_pct": round(pct_a, 1),
            "b_count": b, "b_pct": round(pct_b, 1),
            "delta_pp": round(delta, 1),
        })

    if args.out_csv:
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=linhas[0].keys())
            w.writeheader()
            w.writerows(linhas)
        print(f"\nsalvo em {args.out_csv}")


if __name__ == "__main__":
    main()
