#!/usr/bin/env python3
# compara rodadas com gliner 2 labels vs 4 labels
# roda em cima das transcricoes ja existentes, chama o extrator com cada config
# e salva resultado + tempo em pastas separadas. depois so diffar.
#
# uso: .venv/bin/python scripts/comparar-gliner-labels.py --limit 20
# sai 2 arquivos csv em docs/ com cobertura e latencia

import argparse
import csv
import json
import time
from pathlib import Path

from src import config
from src import ui_banners
from src.extracao import gliner_client
from src.extracao.qwen_extrator import extrai_todos_campos
from src.extracao.prompts import monta_prompt_extrator


LABELS_2 = ["peixe", "bacia hidrografica"]
LABELS_4 = ["peixe", "bacia hidrografica", "rio", "municipio"]


def lista_transcricoes(limit: int) -> list[Path]:
    tr = config.TRANSCR_DIR
    todas = sorted(tr.glob("*.json"))
    return todas[:limit]


def roda_com_labels(transcr_path: Path, labels: list[str]) -> dict:
    # le transcricao, roda gliner com labels escolhidas, roda extrator, retorna
    # dict com {campos, latencia_total_ms, latencia_gliner_ms, latencia_llm_ms}
    data = json.loads(transcr_path.read_text(encoding="utf-8"))
    texto = data.get("texto", "")

    t0 = time.time()
    spans = gliner_client.extrai_por_label(texto, labels=labels)
    t_gliner = time.time() - t0

    t1 = time.time()
    # o prompt sempre pede 8 campos, gliner so injeta hints diferentes
    prompt = monta_prompt_extrator(texto, spans)
    campos = extrai_todos_campos(texto, spans)
    t_llm = time.time() - t1

    return {
        "video_id": transcr_path.stem,
        "campos": campos,
        "latencia_total_ms": int((t_gliner + t_llm) * 1000),
        "latencia_gliner_ms": int(t_gliner * 1000),
        "latencia_llm_ms": int(t_llm * 1000),
    }


def tem_valor(c) -> bool:
    # campo extraido eh objeto com .valor ou dict
    if c is None:
        return False
    if hasattr(c, "valor"):
        v = c.valor
    elif isinstance(c, dict):
        v = c.get("valor")
    else:
        v = c
    return v not in (None, "", [])


def resume(rodadas: list[dict], tag: str) -> dict:
    # agrega cobertura por campo e latencia media
    n = len(rodadas)
    if not n:
        return {}
    cobertura: dict[str, int] = {}
    lat_total = 0
    lat_gliner = 0
    lat_llm = 0
    for r in rodadas:
        for nome, campo in (r.get("campos") or {}).items():
            if tem_valor(campo):
                cobertura[nome] = cobertura.get(nome, 0) + 1
        lat_total += r["latencia_total_ms"]
        lat_gliner += r["latencia_gliner_ms"]
        lat_llm += r["latencia_llm_ms"]
    return {
        "tag": tag,
        "n": n,
        "cobertura": cobertura,
        "lat_total_ms_media": lat_total // n,
        "lat_gliner_ms_media": lat_gliner // n,
        "lat_llm_ms_media": lat_llm // n,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10, help="quantos videos testar")
    p.add_argument("--out", type=Path, default=Path("docs/comparacao-gliner-labels"))
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    print(ui_banners.banner_gliner_labels())

    transcrs = lista_transcricoes(args.limit)
    if not transcrs:
        print("sem transcricoes na pasta, rode make transcrever primeiro")
        return

    print(f"rodando em {len(transcrs)} transcricoes\n")
    print("   ><(((o>  rodada 1: 2 labels (peixe, bacia)")
    r2 = [roda_com_labels(t, LABELS_2) for t in transcrs]
    print("\n   ><((((((((o>  rodada 2: 4 labels (+rio +municipio)")
    r4 = [roda_com_labels(t, LABELS_4) for t in transcrs]

    s2 = resume(r2, "2-labels")
    s4 = resume(r4, "4-labels")

    # salva cru em json pra inspecionar depois
    (args.out / "raw_2labels.json").write_text(json.dumps(r2, ensure_ascii=False, indent=2, default=str))
    (args.out / "raw_4labels.json").write_text(json.dumps(r4, ensure_ascii=False, indent=2, default=str))

    # csv comparativo
    campos = sorted(set(s2.get("cobertura", {})) | set(s4.get("cobertura", {})))
    csv_path = args.out / "comparacao.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["campo", "cobertura_2labels", "cobertura_4labels", "delta_pp"])
        for c in campos:
            c2 = s2["cobertura"].get(c, 0)
            c4 = s4["cobertura"].get(c, 0)
            pp = (c4 - c2) / s2["n"] * 100 if s2["n"] else 0
            w.writerow([c, c2, c4, f"{pp:+.1f}"])
        w.writerow([])
        w.writerow(["latencia_media_total_ms", s2["lat_total_ms_media"], s4["lat_total_ms_media"],
                    f"{(s4['lat_total_ms_media'] - s2['lat_total_ms_media']) / s2['lat_total_ms_media'] * 100:+.1f}%"])
        w.writerow(["latencia_gliner_ms", s2["lat_gliner_ms_media"], s4["lat_gliner_ms_media"], ""])
        w.writerow(["latencia_llm_ms", s2["lat_llm_ms_media"], s4["lat_llm_ms_media"], ""])

    print(f"\ncomparacao salva em {csv_path}\n")
    linhas = []
    linhas.append(f"{'campo':15s} {'2lab':>5s} {'4lab':>5s} {'delta':>6s}")
    linhas.append("-" * 40)
    for c in campos:
        c2 = s2["cobertura"].get(c, 0)
        c4 = s4["cobertura"].get(c, 0)
        linhas.append(f"{c:15s} {c2:5d} {c4:5d} {c4 - c2:+6d}")
    linhas.append("")
    linhas.append(f"lat total media: {s2['lat_total_ms_media']}ms -> {s4['lat_total_ms_media']}ms")
    print(ui_banners.caixa("sumario cobertura + latencia", linhas))


if __name__ == "__main__":
    main()
