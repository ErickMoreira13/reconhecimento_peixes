#!/usr/bin/env python3
# lista as queries do harvester loop em tabela legivel no terminal
# chamado pelo `make queries`

import argparse
import sys
from pathlib import Path

# ajeita path pro script achar src/ quando rodado direto
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import ascii_art, ui_banners
from src.storage import db as storage


def _status_label(status: str) -> str:
    # label curta + colorida por status, ajuda ver de relance
    mapa = {
        "ativa": ascii_art.colore("[ativa]", ascii_art.VERDE_CLARO),
        "saturada": ascii_art.colore("[SATUR]", ascii_art.AMARELO_CLARO),
        "desativada": ascii_art.colore("[off]  ", ascii_art.DIM),
    }
    return mapa.get(status, f"[{status[:5]:5s}]")


def main():
    # argparse so pro --help funcionar. nao tem flag real, so info
    argparse.ArgumentParser(
        description="lista queries do harvester loop com status colorido"
    ).parse_args()

    rows = storage.lista_queries()
    print(ui_banners.banner_queries())

    if not rows:
        print("  (nenhuma query no db ainda)")
        return

    # cabecalho + linhas
    linhas = []
    linhas.append(f"{'status':9s} {'busc':>5s} {'novos':>5s} {'dedup':>6s} {'rej':>5s}  texto")
    linhas.append("-" * 72)
    for r in rows:
        st = _status_label(r["status"])
        busc = r["total_buscados"] or 0
        novos = r["total_novos"] or 0
        dedup = r["dedup_rate_ultima"] or 0.0
        rej = r["rejeicao_rate_ultima"] or 0.0
        texto = r["texto"][:40]
        # st tem codigo ansi que conta como len, entao padding nao fica perfeito
        # mas visualmente ok no terminal. sem alinhamento perfeito por design
        linhas.append(f"{st} {busc:5d} {novos:5d} {dedup:6.2f} {rej:5.2f}  {texto}")

    # imprime sem caixa pq a tabela ja eh larga, caixa ficaria enorme
    for ln in linhas:
        print(f"  {ln}")

    print()
    ativas = sum(1 for r in rows if r["status"] == "ativa")
    satur = sum(1 for r in rows if r["status"] == "saturada")
    total_txt = ascii_art.colore(f"total: {len(rows)}", ascii_art.CIANO_CLARO)
    ativas_txt = ascii_art.colore(f"ativas: {ativas}", ascii_art.VERDE_CLARO)
    satur_txt = ascii_art.colore(f"saturadas: {satur}", ascii_art.AMARELO_CLARO)
    print(f"  {total_txt}  |  {ativas_txt}  |  {satur_txt}")


if __name__ == "__main__":
    main()
