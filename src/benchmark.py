import argparse
import json
import time
from collections import Counter
from pathlib import Path

from src import config, ui


# benchmark comparativo entre modelos extratores
# ideia: mesma base de transcricoes, varios modelos, mesma metricazinha
#
# nao avalia "qualidade absoluta" (precisaria de gold set humano), so compara
# cobertura, tempo, taxa de fora_do_gazetteer, parse rate e stuff mensuravel


def roda_benchmark(modelo: str, suffix: str, limit: int, gliner_ckpt: str | None = None):
    import subprocess
    # chama o main mesmo, pra reutilizar toda a logica de pegar transcritos e salvar
    args = [
        ".venv/bin/python", "-m", "src.main", "extrair",
        "--limit", str(limit),
        "--modelo", modelo,
        "--suffix", suffix,
    ]
    if gliner_ckpt:
        args.extend(["--gliner-ckpt", gliner_ckpt])

    t0 = time.monotonic()
    r = subprocess.run(args, cwd=str(Path(__file__).parent.parent))
    elapsed = time.monotonic() - t0
    return elapsed, r.returncode


def analisa_suffix(suffix: str) -> dict:
    # le todos os jsons com aquele suffix e gera metricas
    pat = f"*_extracao_{suffix}.json" if suffix else "*_extracao.json"
    arquivos = list(config.RESULTS_DIR.glob(pat))

    if not arquivos:
        return {"erro": f"nenhum arquivo {pat}"}

    # contadores
    total = len(arquivos)
    cobertura: Counter = Counter()
    fora_dict: Counter = Counter()
    latencias: list[int] = []
    valores_unicos: dict[str, set] = {
        "tipo_ceva": set(), "grao": set(), "bacia": set(),
        "rio": set(), "municipio": set(), "estado": set(),
    }
    todas_especies: set = set()
    obs_len: list[int] = []

    # falhas de parse (todos os campos null significa que o llm provavelmente falhou)
    parse_fail = 0

    for arq in arquivos:
        with open(arq, encoding="utf-8") as f:
            d = json.load(f)
        campos = d.get("campos", {})

        # cobertura por campo
        nao_nulos = 0
        for nome, c in campos.items():
            v = c.get("valor")
            if v is None or v == [] or v == "":
                continue
            nao_nulos += 1
            cobertura[nome] += 1
            if c.get("fora_do_gazetteer"):
                fora_dict[nome] += 1

            # valores unicos por campo (pra ver diversidade)
            if nome in valores_unicos and isinstance(v, str):
                valores_unicos[nome].add(v.lower().strip())

            # lista de especies
            if nome == "especies" and isinstance(v, list):
                for e in v:
                    nome_esp = e.get("nome") if isinstance(e, dict) else str(e)
                    if nome_esp:
                        todas_especies.add(nome_esp.lower().strip())

            # length das observacoes
            if nome == "observacoes" and isinstance(v, str):
                obs_len.append(len(v.split()))

        if nao_nulos == 0:
            parse_fail += 1

        # latencia media desse video
        lat_med = sum(c.get("latencia_ms", 0) for c in campos.values()) // max(1, len(campos))
        latencias.append(lat_med)

    return {
        "total_videos": total,
        "cobertura_por_campo": dict(cobertura),
        "fora_do_gazetteer_por_campo": dict(fora_dict),
        "latencia_media_ms": sum(latencias) // max(1, len(latencias)),
        "latencia_p95_ms": sorted(latencias)[int(0.95 * len(latencias))] if latencias else 0,
        "especies_unicas": len(todas_especies),
        "amostra_especies": sorted(todas_especies)[:30],
        "obs_comprimento_medio": sum(obs_len) // max(1, len(obs_len)),
        "obs_max_palavras": max(obs_len) if obs_len else 0,
        "valores_unicos_categoricos": {k: sorted(v) for k, v in valores_unicos.items()},
        "parse_fail_count": parse_fail,
        "parse_fail_pct": round(100 * parse_fail / total, 1) if total else 0,
    }


def imprime_relatorio(resultados: dict[str, dict]):
    # tabela lado a lado dos modelos
    console = ui.console()
    from rich.table import Table

    modelos = list(resultados.keys())

    # tabela 1: resumo geral
    t1 = Table(title="benchmark — resumo geral", show_header=True)
    t1.add_column("metrica")
    for m in modelos:
        t1.add_column(m, justify="right")

    t1.add_row("total videos", *[str(resultados[m].get("total_videos", "-")) for m in modelos])
    t1.add_row("latencia media (s)", *[f"{resultados[m].get('latencia_media_ms', 0)/1000:.1f}" for m in modelos])
    t1.add_row("latencia p95 (s)", *[f"{resultados[m].get('latencia_p95_ms', 0)/1000:.1f}" for m in modelos])
    t1.add_row("parse fail %", *[f"{resultados[m].get('parse_fail_pct', 0)}%" for m in modelos])
    t1.add_row("especies unicas", *[str(resultados[m].get("especies_unicas", 0)) for m in modelos])
    t1.add_row("obs compr medio (palavras)", *[str(resultados[m].get("obs_comprimento_medio", 0)) for m in modelos])
    t1.add_row("obs max palavras", *[str(resultados[m].get("obs_max_palavras", 0)) for m in modelos])
    console.print(t1)

    # tabela 2: cobertura por campo
    t2 = Table(title="cobertura (videos com valor nao-nulo)", show_header=True)
    t2.add_column("campo")
    for m in modelos:
        t2.add_column(m, justify="right")

    todos_campos = set()
    for m in modelos:
        todos_campos.update(resultados[m].get("cobertura_por_campo", {}).keys())

    for campo in sorted(todos_campos):
        linha = [campo]
        for m in modelos:
            cob = resultados[m].get("cobertura_por_campo", {}).get(campo, 0)
            tot = resultados[m].get("total_videos", 1)
            pct = 100 * cob / max(1, tot)
            linha.append(f"{cob}/{tot} ({pct:.0f}%)")
        t2.add_row(*linha)

    console.print(t2)

    # tabela 3: termos fora do gazetteer (vocabulario novo descoberto)
    t3 = Table(title="fora do gazetteer — vocabulario novo", show_header=True)
    t3.add_column("campo")
    for m in modelos:
        t3.add_column(m, justify="right")

    for campo in sorted(todos_campos):
        linha = [campo]
        for m in modelos:
            fora = resultados[m].get("fora_do_gazetteer_por_campo", {}).get(campo, 0)
            linha.append(str(fora))
        t3.add_row(*linha)

    console.print(t3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modelos", nargs="+", required=True, help="modelos ollama pra comparar")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--gliner-ckpt", default=None)
    p.add_argument("--so-analise", action="store_true", help="pula execucao, so le os resultados salvos")
    args = p.parse_args()

    resultados: dict[str, dict] = {}

    for modelo in args.modelos:
        suffix = modelo.replace(":", "_").replace("/", "_")
        ui.titulo(f"benchmark: {modelo}")

        if not args.so_analise:
            ui.info(f"rodando extracao com {modelo}...")
            elapsed, rc = roda_benchmark(modelo, suffix, args.limit, args.gliner_ckpt)
            if rc != 0:
                ui.erro(f"  deu ruim no {modelo} (rc={rc}), pulando analise")
                continue
            ui.ok(f"  terminou em {elapsed:.0f}s wall-clock")

        ui.info(f"analisando resultados de {modelo}...")
        resultados[modelo] = analisa_suffix(suffix)

    # imprime comparativo
    ui.titulo("comparativo")
    imprime_relatorio(resultados)

    # salva relatorio em json
    out = config.RESULTS_DIR / f"benchmark_{int(time.time())}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=list)
    ui.ok(f"relatorio salvo em {out}")


if __name__ == "__main__":
    main()
