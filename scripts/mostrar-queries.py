#!/usr/bin/env python3
# lista as queries do harvester loop em tabela legivel no terminal
# chamado pelo `make queries`

import sys
from pathlib import Path

# ajeita path pro script achar src/ quando rodado direto
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import ui_banners
from src.storage import db as storage


def _status_emoji_livre(status: str) -> str:
    # sem emoji (regra do projeto), so texto. label curta pra alinhar
    mapa = {"ativa": "[ativa]", "saturada": "[SATUR]", "desativada": "[off]  "}
    return mapa.get(status, f"[{status[:5]:5s}]")


def main():
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
        st = _status_emoji_livre(r["status"])
        busc = r["total_buscados"] or 0
        novos = r["total_novos"] or 0
        dedup = r["dedup_rate_ultima"] or 0.0
        rej = r["rejeicao_rate_ultima"] or 0.0
        texto = r["texto"][:40]
        linhas.append(f"{st:9s} {busc:5d} {novos:5d} {dedup:6.2f} {rej:5.2f}  {texto}")

    # imprime sem caixa pq a tabela ja eh larga, caixa ficaria enorme
    for ln in linhas:
        print(f"  {ln}")

    print()
    ativas = sum(1 for r in rows if r["status"] == "ativa")
    satur = sum(1 for r in rows if r["status"] == "saturada")
    print(f"  total: {len(rows)}  |  ativas: {ativas}  |  saturadas: {satur}")


if __name__ == "__main__":
    main()
