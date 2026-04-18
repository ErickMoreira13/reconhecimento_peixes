import json
import re
from pathlib import Path

from rapidfuzz import fuzz

from src.schemas import CampoExtraido, Veredito, TipoRejeicao


# camada 1 do verificador: regras deterministicas (gratas, ~10ms)
# so gasta o llm critic se passar daqui
#
# IMPORTANTE: essas regras NAO rejeitam por "valor fora do gazetteer"
# vocabulario aberto, dict eh hint e nao filtro.
# se nao casa com dict, marca fora_do_gazetteer=true mas o valor vai pro resultado


# thresholds chutados baseado em alguns testes rapidos
# ajustar depois se der mt falso negativo
THRESHOLD_CONF = {
    "estado": 0.7,
    "municipio": 0.5,
    "rio": 0.5,
    "bacia": 0.5,
    "tipo_ceva": 0.6,
    "grao": 0.7,
    "especies": 0.5,
    "observacoes": 0.4,
}

ALINHAMENTO_MIN = 0.70  # levenshtein-ratio

# nomes proprios comuns pra nao confundir com peixe/municipio
# lista parcial, expandir se der muito falso positivo
NOMES_PROPRIOS_COMUNS = {
    "joao", "maria", "jose", "carlos", "marcos", "roberto", "fernando",
    "pedro", "ana", "paulo", "andre", "bruno", "rafael", "ricardo",
    "antonio", "francisco", "luis", "luiz", "manoel", "manuel",
    "leonardo", "gabriel", "rodrigo", "thiago", "tiago", "felipe",
    "daniel", "jorge", "marcelo", "eduardo", "adriano", "edson",
}


_estados_cache: set[str] | None = None


def _ufs() -> set[str]:
    global _estados_cache
    if _estados_cache is None:
        p = Path(__file__).parent.parent / "dicts" / "estados.json"
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        _estados_cache = {u["sigla"] for u in d["ufs"]}
    return _estados_cache


def evidencia_alinha(evidencia: str, transcricao: str) -> float:
    # usa rapidfuzz partial_ratio, mais tolerante que ratio normal
    # pq a evidencia pode vir um pouco diferente do texto (pontuacao etc)
    if not evidencia:
        return 0.0
    return fuzz.partial_ratio(evidencia.lower(), transcricao.lower()) / 100.0


def _eh_nome_proprio(valor: str) -> bool:
    # detecta se o valor eh nome proprio comum brasileiro
    # util pro campo especies pra evitar "joao" virar peixe
    if not valor:
        return False
    tokens = re.findall(r"\w+", valor.lower())
    for t in tokens:
        if t in NOMES_PROPRIOS_COMUNS:
            return True
    return False


def _passa_smith_waterman(campo: CampoExtraido, transcricao: str) -> tuple[bool, TipoRejeicao | None]:
    if not campo.evidencia:
        return True, None  # sem evidencia, deixa passar (pode ser null legitimo)
    score = evidencia_alinha(campo.evidencia, transcricao)
    if score < ALINHAMENTO_MIN:
        return False, "evidencia_nao_alinha"
    return True, None


def _passa_confianca(nome_campo: str, campo: CampoExtraido) -> tuple[bool, TipoRejeicao | None]:
    if campo.valor is None:
        return True, None
    lim = THRESHOLD_CONF.get(nome_campo, 0.5)
    if campo.confianca < lim:
        return False, "confianca_baixa"
    return True, None


def _passa_pos_filter(nome_campo: str, campo: CampoExtraido) -> tuple[bool, TipoRejeicao | None]:
    # so roda pra campos onde nome proprio eh risco
    if nome_campo not in ("especies", "rio", "municipio"):
        return True, None
    if campo.valor is None:
        return True, None

    # especies eh lista, checar cada item
    if nome_campo == "especies" and isinstance(campo.valor, list):
        for e in campo.valor:
            nome = e.get("nome", "") if isinstance(e, dict) else str(e)
            if _eh_nome_proprio(nome):
                return False, "nome_proprio_confundido"
        return True, None

    if isinstance(campo.valor, str) and _eh_nome_proprio(campo.valor):
        return False, "nome_proprio_confundido"
    return True, None


def _passa_enum_estado(campo: CampoExtraido) -> tuple[bool, TipoRejeicao | None]:
    # estado eh o UNICO enum fechado verdadeiro
    if campo.valor is None:
        return True, None
    if isinstance(campo.valor, str) and campo.valor.upper() not in _ufs():
        return False, "contexto_irrelevante"
    return True, None


def _passa_cross_field(nome_campo: str, campo: CampoExtraido, outros: dict[str, CampoExtraido]) -> tuple[bool, TipoRejeicao | None]:
    # por enquanto so checa estado vs municipio (mais simples)
    # pra fazer bacia x UF direito precisa de tabela bacia->UFs, fica pra depois
    # quando tiver tabela ibge completa volto aqui
    return True, None


def _passa_length_obs(nome_campo: str, campo: CampoExtraido) -> tuple[bool, TipoRejeicao | None]:
    if nome_campo != "observacoes" or campo.valor is None:
        return True, None
    if not isinstance(campo.valor, str):
        return True, None
    n_palavras = len(campo.valor.split())
    if n_palavras < 10:
        # mt curto, provavel alucinacao
        return False, "contexto_irrelevante"
    # limite superior de 80 ta no prompt mas nao eh falha grave se passar um pouco
    return True, None


def aplica_regras(
    nome_campo: str,
    campo: CampoExtraido,
    transcricao: str,
    outros: dict[str, CampoExtraido],
) -> Veredito:
    # roda todas as regras em ordem, primeira que falhar define o veredito
    # ordem importa: as mais baratas primeiro

    ordem = [
        _passa_confianca,
        lambda nc, c, t, o: _passa_smith_waterman(c, t),
        _passa_pos_filter,
        lambda nc, c, t, o: _passa_enum_estado(c) if nc == "estado" else (True, None),
        _passa_cross_field,
        _passa_length_obs,
    ]

    for regra in ordem:
        try:
            ok, tipo = regra(nome_campo, campo, transcricao, outros) if regra is _passa_cross_field else (
                regra(nome_campo, campo) if regra in (_passa_confianca, _passa_pos_filter, _passa_length_obs)
                else regra(nome_campo, campo, transcricao, outros)
            )
        except TypeError:
            # algumas regras nao recebem todos os args, trata generico
            ok, tipo = True, None

        if not ok:
            return Veredito(
                aceito=False,
                razao=f"regra falhou em {nome_campo}: {tipo}",
                sugestao_retry="revise a evidencia e o valor baseado no que ta no texto",
                confianca_critica=0.9,
                tipo_rejeicao=tipo,
            )

    # passou em todas as regras
    return Veredito(
        aceito=True,
        razao="ok nas regras deterministicas",
        sugestao_retry=None,
        confianca_critica=0.8,
        tipo_rejeicao=None,
    )
