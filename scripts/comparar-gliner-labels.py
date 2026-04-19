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
import sys
import time
from pathlib import Path

# ajeita path pro script achar src/ quando rodado direto do terminal
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config
from src import ui_banners
from src.extracao import gliner_client
from src.extracao import qwen_extrator


LABELS_2 = ["peixe", "bacia hidrografica"]
LABELS_4 = ["peixe", "bacia hidrografica", "rio", "municipio"]


def lista_transcricoes(limit: int) -> list[Path]:
    tr = config.TRANSCR_DIR
    todas = sorted(tr.glob("*.json"))
    return todas[:limit]


def _roda_robusto(transcrs, labels: list[str], tag: str, parcial_dir: Path) -> list[dict]:
    # envelope de roda_com_labels que pula videos com erro em vez de matar tudo
    # 1 video quebrado nao pode inviabilizar a comparacao em 50 videos
    #
    # save incremental: cada video processado grava um json em parcial_dir/tag/
    # assim se cancelar no meio nao perde tudo, e pode retomar pulando os ja
    # processados
    out_dir = parcial_dir / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    out = []
    for i, t in enumerate(transcrs, 1):
        arquivo_parcial = out_dir / f"{t.stem}.json"

        # se ja tem o json parcial, carrega em vez de reprocessar
        # permite retomar run interrompido sem perder tempo
        if arquivo_parcial.exists():
            try:
                r = json.loads(arquivo_parcial.read_text(encoding="utf-8"))
                out.append(r)
                print(f"    [{i}/{len(transcrs)}] skip (ja tem) {t.stem}")
                continue
            except Exception:
                # json corrompido, reprocessa
                print(f"    [{i}/{len(transcrs)}] parcial corrompido, refazendo {t.stem}")

        try:
            r = roda_com_labels(t, labels)
            # grava na hora pra sobreviver a cancelamento
            arquivo_parcial.write_text(
                json.dumps(r, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            out.append(r)
            print(f"    [{i}/{len(transcrs)}] ok {t.stem}")
        except Exception as e:
            print(f"    [{i}/{len(transcrs)}] FALHOU {t.stem}: {type(e).__name__}: {e}")
            # nao conta esse video no sumario
    return out


def roda_com_labels(transcr_path: Path, labels: list[str]) -> dict:
    # le transcricao, roda extracao completa (gliner + llm) com labels escolhidas
    # nao tem como passar labels diferentes sem mexer no extrai_campos, entao
    # faz monkeypatch do LABELS_PADRAO temporario — feio mas funciona pro teste
    data = json.loads(transcr_path.read_text(encoding="utf-8"))
    texto = data.get("texto", "")

    # backup do estado global
    labels_antes = list(gliner_client.LABELS_PADRAO)
    modelo_cache = gliner_client._modelo
    try:
        gliner_client.LABELS_PADRAO = list(labels)
        # limpa cache do modelo so se as labels mudaram significativamente
        # (gliner reusa o mesmo modelo, labels sao passadas em cada predict)

        t0 = time.time()
        campos = qwen_extrator.extrai_campos(texto)
        elapsed = time.time() - t0
    finally:
        gliner_client.LABELS_PADRAO = labels_antes
        gliner_client._modelo = modelo_cache

    # nao da pra separar latencia gliner vs llm sem instrumentar o extrai_campos
    # entao por enquanto so o total. se precisar desagregar, adicionar hooks depois
    return {
        "video_id": transcr_path.stem,
        "campos": campos,
        "latencia_total_ms": int(elapsed * 1000),
        "latencia_gliner_ms": 0,
        "latencia_llm_ms": int(elapsed * 1000),
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
    parcial = args.out / "parciais"
    print("   ><(((o>  rodada 1: 2 labels (peixe, bacia)")
    r2 = _roda_robusto(transcrs, LABELS_2, "2labels", parcial)
    print("\n   ><((((((((o>  rodada 2: 4 labels (+rio +municipio)")
    r4 = _roda_robusto(transcrs, LABELS_4, "4labels", parcial)

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
