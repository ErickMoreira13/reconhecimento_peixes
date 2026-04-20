import json
from pathlib import Path

from rapidfuzz import fuzz

from src.texto import normaliza as _normaliza


# verificacao deterministica: dado o valor que o llm retornou, confere se
# ele esta no gazetteer. se nao esta, seta fora_do_gazetteer=true.
#
# o llm nao eh confiavel pra marcar essa flag (tende a sempre dizer false).
# a gente usa essa checagem como ground truth.


DICTS_DIR = Path(__file__).parent.parent / "dicts"


_peixes_cache: set[str] | None = None
_bacias_cache: set[str] | None = None
_ufs_cache: set[str] | None = None


def _carrega_peixes() -> set[str]:
    global _peixes_cache
    if _peixes_cache is None:
        d = json.loads((DICTS_DIR / "peixes_conhecidos.json").read_text(encoding="utf-8"))
        _peixes_cache = {_normaliza(n) for n in d.get("nomes_comuns_peixes", [])}
    return _peixes_cache


def _carrega_bacias() -> set[str]:
    global _bacias_cache
    if _bacias_cache is None:
        d = json.loads((DICTS_DIR / "bacias_conhecidas.json").read_text(encoding="utf-8"))
        _bacias_cache = {_normaliza(n) for n in d.get("basins", [])}
    return _bacias_cache


def _carrega_ufs() -> set[str]:
    global _ufs_cache
    if _ufs_cache is None:
        d = json.loads((DICTS_DIR / "estados.json").read_text(encoding="utf-8"))
        _ufs_cache = {uf["sigla"].upper() for uf in d["ufs"]}
    return _ufs_cache


def _casa_fuzzy(valor: str, gazetteer: set[str], threshold: int = 85) -> bool:
    # match exato primeiro
    v = _normaliza(valor)
    if v in gazetteer:
        return True
    # fuzzy pra pegar variacoes ("tilapia do nilo" vs "Tilápia-do-Nilo")
    for g in gazetteer:
        if fuzz.ratio(v, g) >= threshold:
            return True
    return False


def esta_no_gazetteer(campo: str, valor) -> bool:
    # retorna true se o valor bate com algum gazetteer do projeto
    if valor is None or valor == "" or valor == []:
        return True  # null nao precisa validar

    if campo == "estado":
        return str(valor).upper() in _carrega_ufs()

    if campo == "especies":
        if not isinstance(valor, list):
            return False
        peixes = _carrega_peixes()
        for item in valor:
            nome = item.get("nome") if isinstance(item, dict) else str(item)
            if not _casa_fuzzy(nome, peixes):
                return False
        return True

    if campo == "bacia":
        return _casa_fuzzy(str(valor), _carrega_bacias())

    if campo in ("rio",):
        # rio usa mesmo gazetteer das bacias (que tem rios dentro)
        return _casa_fuzzy(str(valor), _carrega_bacias())

    if campo == "tipo_ceva":
        d = json.loads((DICTS_DIR / "cevas.json").read_text(encoding="utf-8"))
        cats = set(d.get("categorias", {}).keys())
        return str(valor) in cats

    if campo == "grao":
        d = json.loads((DICTS_DIR / "graos.json").read_text(encoding="utf-8"))
        return str(valor).lower() in d.get("graos", {})

    # municipio e observacoes nao tem gazetteer (livres)
    return True  # nao checavel -> assume que ta ok


def aplica_flag_fora_do_gazetteer(campos: dict) -> dict:
    # itera sobre os campos e seta fora_do_gazetteer=true quando o valor
    # retornado pelo llm nao casa com nenhum gazetteer.
    # nao altera o valor em si, so a flag (vocabulario aberto preserva tudo).
    for nome, campo in campos.items():
        if nome in ("municipio", "observacoes"):
            continue  # campos livres, nao checamos
        if hasattr(campo, "fora_do_gazetteer"):
            campo.fora_do_gazetteer = not esta_no_gazetteer(nome, campo.valor)
    return campos
