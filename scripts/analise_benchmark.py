#!/usr/bin/env python3
# script de analise detalhada do benchmark
# roda depois de src.benchmark pra ver divergencias e possiveis alucinacoes

import json
import sys
from pathlib import Path

try:
    from rapidfuzz import fuzz
except ImportError:
    print("precisa do rapidfuzz: pip install rapidfuzz")
    sys.exit(1)


def extrai_vid(p: Path) -> str | None:
    stem = p.stem
    if "_extracao_" in stem:
        return stem.split("_extracao_")[0]
    return None


def main():
    results = Path("data/results")
    if not results.exists():
        print(f"pasta {results} nao existe, roda o benchmark primeiro")
        return

    # descobre quais suffixes tem
    suffixes = set()
    for p in results.glob("*_extracao_*.json"):
        s = p.stem.split("_extracao_")[1]
        suffixes.add(s)

    if len(suffixes) < 2:
        print("precisa de no minimo 2 modelos pra comparar, roda o benchmark")
        return

    suffixes = sorted(suffixes)
    print(f"modelos encontrados: {suffixes}")

    # video_ids em comum a todos os modelos
    comuns = None
    for s in suffixes:
        ids = {extrai_vid(p) for p in results.glob(f"*_extracao_{s}.json") if extrai_vid(p)}
        comuns = ids if comuns is None else comuns & ids
    comuns = sorted(comuns)
    print(f"{len(comuns)} videos processados por todos\n")

    # conta divergencias em campos geograficos
    campos_geo = ["estado", "municipio", "rio", "bacia"]
    div: dict[str, int] = {s: 0 for s in suffixes}
    for vid in comuns:
        campos_por_modelo = {}
        for s in suffixes:
            p = results / f"{vid}_extracao_{s}.json"
            campos_por_modelo[s] = json.loads(p.read_text(encoding="utf-8"))["campos"]
        for nome in campos_geo:
            vals = {s: campos_por_modelo[s].get(nome, {}).get("valor") for s in suffixes}
            nao_vazios = [s for s, v in vals.items() if v]
            if len(nao_vazios) == 1 and len(suffixes) >= 3:
                # modelo preenche mas os outros 2+ nao -> suspeito
                div[nao_vazios[0]] += 1

    print("divergencias em campos geograficos (modelo preenche mas >=2 outros NAO):")
    for s, n in div.items():
        print(f"  {s}: {n}")

    # conta evidencias que nao alinham com transcricao
    print("\nevidencias que NAO alinham com a transcricao (smith-waterman < 80):")
    for s in suffixes:
        desalinhadas = 0
        total_checadas = 0
        exemplos = []
        for vid in comuns:
            p = results / f"{vid}_extracao_{s}.json"
            tp = Path(f"data/transcriptions/{vid}.json")
            if not tp.exists():
                continue
            transc = json.loads(tp.read_text(encoding="utf-8"))["texto"].lower()
            campos = json.loads(p.read_text(encoding="utf-8"))["campos"]
            for nome in ["estado", "municipio", "rio", "bacia", "tipo_ceva", "grao"]:
                c = campos.get(nome, {})
                v = c.get("valor")
                ev = c.get("evidencia", "")
                if v and ev:
                    total_checadas += 1
                    score = fuzz.partial_ratio(ev.lower(), transc)
                    if score < 80:
                        desalinhadas += 1
                        if len(exemplos) < 3:
                            exemplos.append((vid[:12], nome, v, ev[:50]))
        pct = 100 * desalinhadas / total_checadas if total_checadas else 0
        print(f"  {s}: {desalinhadas}/{total_checadas} desalinhadas ({pct:.1f}%)")
        for vid, nome, v, ev in exemplos:
            print(f"      {vid} / {nome} = {v!r} (ev = {ev!r})")


if __name__ == "__main__":
    main()
