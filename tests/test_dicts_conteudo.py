import json
from pathlib import Path


DICTS = Path(__file__).parent.parent / "src" / "dicts"


def _load(nome):
    with open(DICTS / nome, encoding="utf-8") as f:
        return json.load(f)


def test_peixes_tem_peixes_super_comuns_br():
    # pescaria brasileira nao tem sentido sem esses.
    # se alguem acidentalmente apagar, o teste quebra
    d = _load("peixes_conhecidos.json")
    nomes_lower = {n.lower() for n in d["nomes_comuns_peixes"]}

    essenciais = ["tambaqui", "tucunaré", "pacu", "traíra", "tilápia",
                  "pirarucu", "dourado", "surubim", "cará", "corvina"]
    for e in essenciais:
        assert any(e in n for n in nomes_lower), f"faltou {e} no dict de peixes"


def test_estados_tem_as_27_ufs():
    d = _load("estados.json")
    siglas = {uf["sigla"] for uf in d["ufs"]}
    ufs_reais = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
                 "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
                 "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
    assert siglas == ufs_reais


def test_cevas_categorias_tem_variacoes():
    d = _load("cevas.json")
    for cat, vars_ in d["categorias"].items():
        assert len(vars_) >= 2, f"categoria {cat} com menos de 2 variacoes"


def test_graos_tem_soja_e_milho():
    # sao os graos mais importantes pra pesca com ceva
    d = _load("graos.json")
    assert "soja" in d["graos"]
    assert "milho" in d["graos"]


def test_bacias_tem_principais():
    d = _load("bacias_conhecidas.json")
    bacias_lower = {b.lower() for b in d["basins"]}
    # a amazonica nem precisa aparecer direto, os rios tributarios ja cobrem
    # ex: "rio madeira" -> bacia amazonica. entao so checa ter bastante nome
    assert len(bacias_lower) >= 50, "dict de bacias mt curto"


def test_nomes_peixes_nao_duplica():
    d = _load("peixes_conhecidos.json")
    nomes = d["nomes_comuns_peixes"]
    # pode ter duplicatas por acentuacao/capitalizacao, mas case-sensitive
    # nao deve
    assert len(nomes) == len(set(nomes)), "tem peixe duplicado case-sensitive"


def test_ufs_siglas_unicas():
    d = _load("estados.json")
    siglas = [uf["sigla"] for uf in d["ufs"]]
    assert len(siglas) == len(set(siglas))
