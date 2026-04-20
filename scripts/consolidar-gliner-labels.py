#!/usr/bin/env python3
# le os parciais salvos pelo comparar-gliner-labels.py e gera sumario.
# util pra ver resultado mesmo se a rodada foi interrompida no meio.
#
# uso: .venv/bin/python scripts/consolidar-gliner-labels.py
#      (le docs/comparacao-gliner-labels/parciais/{2labels,4labels})

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import ascii_art, ui_banners


def carrega_parciais(pasta: Path) -> list[dict]:
    if not pasta.exists():
        return []
    out = []
    for p in sorted(pasta.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"    pulando {p.name}: {e}")
    return out


def tem_valor(c) -> bool:
    if c is None:
        return False
    if isinstance(c, dict):
        v = c.get("valor")
    else:
        v = c
    return v not in (None, "", [])


def agrega(rodadas: list[dict]) -> dict:
    n = len(rodadas)
    if not n:
        return {"n": 0, "cobertura": {}, "lat_total_ms_media": 0}
    cobertura: dict[str, int] = {}
    lat_total = 0
    for r in rodadas:
        for nome, campo in (r.get("campos") or {}).items():
            if tem_valor(campo):
                cobertura[nome] = cobertura.get(nome, 0) + 1
        lat_total += r.get("latencia_total_ms", 0)
    return {"n": n, "cobertura": cobertura, "lat_total_ms_media": lat_total // n}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", type=Path, default=Path("docs/comparacao-gliner-labels/parciais"))
    p.add_argument("--out", type=Path, default=Path("docs/comparacao-gliner-labels"))
    args = p.parse_args()

    print(ascii_art.banner_projeto())
    print(ui_banners.banner_gliner_labels())

    r2 = carrega_parciais(args.dir / "2labels")
    r4 = carrega_parciais(args.dir / "4labels")

    a2 = agrega(r2)
    a4 = agrega(r4)

    print(f"  carregados: 2labels={a2['n']}  4labels={a4['n']}")
    if a2["n"] == 0 and a4["n"] == 0:
        print("  nada parcial ainda, rode comparar-gliner-labels primeiro")
        return

    campos = sorted(set(a2["cobertura"]) | set(a4["cobertura"]))

    # csv
    csv_path = args.out / "comparacao.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["campo", "cobertura_2labels", "cobertura_4labels", "delta_abs"])
        for c in campos:
            c2 = a2["cobertura"].get(c, 0)
            c4 = a4["cobertura"].get(c, 0)
            w.writerow([c, c2, c4, c4 - c2])
        w.writerow([])
        w.writerow(["n_2labels", a2["n"], "n_4labels", a4["n"]])
        w.writerow(["lat_media_2lab_ms", a2["lat_total_ms_media"],
                    "lat_media_4lab_ms", a4["lat_total_ms_media"]])

    print(f"\n  csv salvo em {csv_path}\n")

    # sumario bonito
    linhas = []
    linhas.append(f"{'campo':15s} {'2lab':>5s} {'4lab':>5s} {'delta':>6s}")
    linhas.append("-" * 40)
    for c in campos:
        c2 = a2["cobertura"].get(c, 0)
        c4 = a4["cobertura"].get(c, 0)
        linhas.append(f"{c:15s} {c2:5d} {c4:5d} {c4 - c2:+6d}")
    linhas.append("")
    if a2["n"] and a4["n"]:
        delta_pct = (a4["lat_total_ms_media"] - a2["lat_total_ms_media"]) / a2["lat_total_ms_media"] * 100
        linhas.append(f"lat media: {a2['lat_total_ms_media']}ms -> {a4['lat_total_ms_media']}ms ({delta_pct:+.1f}%)")
        linhas.append(f"amostras:  n2={a2['n']}  n4={a4['n']}")
    print(ui_banners.caixa("sumario dos parciais", linhas))


if __name__ == "__main__":
    main()
