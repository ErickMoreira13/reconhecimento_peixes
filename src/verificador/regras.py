import json
import re
from pathlib import Path

from rapidfuzz import fuzz

from src.schemas import CampoExtraido, Veredito, TipoRejeicao
from src.texto import sem_acento


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
    # obs: threshold baixo pq resumos sao de baixa confianca mesmo quando bons.
    # pior caso: resumo borderline vai pro csv (user ve). melhor que perder.
    "observacoes": 0.3,
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

# palavras-chave que DEVEM aparecer na transcricao pra tipo_ceva ser valido
# (fix 1 do sumario-manual: 50% dos videos tinham ceva errada por default)
# ceba eh grafia coloquial de ceva, whisper as vezes transcreve assim
CEVA_KEYWORDS = {"ceva", "seva", "ceba", "cevar", "cevando", "cevador", "cevamos"}

# termos de EQUIPAMENTO de pesca que NAO podem ser tipo_ceva.
# o extrator as vezes confunde: em 3 videos dos 50 anotados, tipo_ceva
# veio como "vara de bambu", "Isquinha Hunter Bait", "Avenado GS" (modelo
# de carretilha). blacklist simples pra rejeitar.
EQUIPAMENTO_BLACKLIST = {
    "vara", "varinha", "carretilha", "molinete", "anzol", "linha",
    "bait", "isca", "isquinha", "hunter", "avenado", "espinhel",
    "rede", "caiaque", "barco",
    # adicionados apos smoke real pegar casos novos:
    "telescopica", "chumbada", "boia", "caiaquinho",
}

# palavras/expressoes genericas que NAO sao especies (fix 4).
# vi 10+ casos nos 50 videos: bonito (adjetivo), paca (exclamacao/mamifero),
# cimprao (giria de companheiro), pai tainha (saudacao), ceba (=ceva mal
# transcrita), escar-viva (=isca viva mal transcrita), peixe grande,
# peixe bonito, piau sul (=variedade, nao peixe especifico)
ESPECIES_STOP_TERMS = {
    # genericos
    "peixe", "peixes", "bicho", "bichos", "especie", "especies",
    "peixao", "peixinho", "peixaria",
    # adjetivos confundidos
    "bonito", "grande", "pequeno", "gigante", "bruto", "bruta",
    # giriais/exclamacoes
    "paca", "cimprao", "ceba", "escar",
    # saudacoes/vocativos
    "pai", "tainha",  # cuidado: tainha eh peixe marinho real. mas "pai tainha"
                     # eh saudacao. a combinacao eh que eh suspeita. filtro
                     # por tokens vai pegar "pai" -> rejeita.
                     # false positive aceitavel ate lista melhor
    "parceiro", "amigo", "galera", "rapaziada", "moleque",
}


def rio_aparece_no_texto(rio: str, transcricao: str) -> bool:
    # fix 2: rio precisa aparecer LITERALMENTE na transcricao.
    # extrator as vezes chuta "Rio Sao Francisco" ou "Rio Araguaia" quando nao
    # sabe — 5 dos 50 videos anotados tinham essa alucinacao.
    #
    # comparacao sem acento e sem prefixo "Rio " pra ser tolerante com variacoes
    # de transcricao (whisper as vezes erra acento)
    if not rio:
        return False

    # normaliza: tira prefixo "Rio ", lowercase, tira acento
    nome_sem_prefixo = re.sub(r"^rio\s+", "", rio.lower().strip())
    nome_norm = sem_acento(nome_sem_prefixo)
    nome_completo_norm = sem_acento(rio.lower().strip())
    texto_norm = sem_acento(transcricao.lower())

    # match literal direto
    if nome_norm in texto_norm:
        return True
    # fuzzy no nome sem prefixo costuma falhar em palavra curta pq o
    # partial_ratio olha string inteira. fuzzy no nome com "rio " dilui
    # o typo e pega casos como "rio iriri" vs "rio iriry"
    if fuzz.partial_ratio(nome_completo_norm, texto_norm) >= 85:
        return True
    return False


_estados_cache: set[str] | None = None
_bacias_cache: list[dict] | None = None


def _ufs() -> set[str]:
    global _estados_cache
    if _estados_cache is None:
        p = Path(__file__).parent.parent / "dicts" / "estados.json"
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        _estados_cache = {u["sigla"] for u in d["ufs"]}
    return _estados_cache


def _bacias() -> list[dict]:
    # lista de dicts {nome, aliases, rios_principais}
    global _bacias_cache
    if _bacias_cache is None:
        p = Path(__file__).parent.parent / "dicts" / "bacias_principais.json"
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        _bacias_cache = d["bacias"]
    return _bacias_cache


def bacia_reconhecida(valor: str) -> bool:
    # fix 7: checa se o valor extraido bate com alguma bacia conhecida.
    # matching em 3 niveis:
    # 1. nome principal ou alias (fuzzy >= 85%)
    # 2. "bacia do X" onde X eh nome de bacia
    # 3. rio principal (ex: "Sao Francisco" extraido bate bacia Sao Francisco)
    if not valor:
        return False

    def _norm(s: str) -> str:
        # remove prefixos de bacia/rio e normaliza acento/case
        s = s.lower().strip()
        s = re.sub(r"^(bacia\s+(do\s+|da\s+|dos\s+|das\s+)?)", "", s)
        s = re.sub(r"^rio\s+", "", s)
        return sem_acento(s)

    v = _norm(valor)
    for b in _bacias():
        nome_norm = _norm(b["nome"])
        if v == nome_norm or fuzz.ratio(v, nome_norm) >= 85:
            return True
        for alias in b.get("aliases", []):
            if v == _norm(alias) or fuzz.ratio(v, _norm(alias)) >= 85:
                return True
        # rio principal — se extraiu nome de rio como bacia, pode ser esse
        for rio in b.get("rios_principais", []):
            if v == _norm(rio) or fuzz.ratio(v, _norm(rio)) >= 90:
                return True
    return False


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


# todas as regras seguem a mesma assinatura pra simplificar aplica_regras.
# args que nao sao usados ficam como `_` ou nome descritivo ignorado.
# retorna (aceita, tipo_rejeicao). aceita=True => passou na regra.

_Assinatura = tuple[bool, "TipoRejeicao | None"]


def _passa_smith_waterman(
    _nome: str, campo: CampoExtraido, transcricao: str, _outros: dict
) -> _Assinatura:
    if not campo.evidencia:
        return True, None  # sem evidencia, deixa passar (pode ser null legitimo)
    score = evidencia_alinha(campo.evidencia, transcricao)
    if score < ALINHAMENTO_MIN:
        return False, "evidencia_nao_alinha"
    return True, None


def _passa_confianca(
    nome_campo: str, campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
    if campo.valor is None:
        return True, None
    lim = THRESHOLD_CONF.get(nome_campo, 0.5)
    if campo.confianca < lim:
        return False, "confianca_baixa"
    return True, None


def _passa_pos_filter(
    nome_campo: str, campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
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


def _passa_enum_estado(
    nome_campo: str, campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
    # estado eh o UNICO enum fechado verdadeiro
    if nome_campo != "estado":
        return True, None  # nao aplica pra outros campos
    if campo.valor is None:
        return True, None
    if isinstance(campo.valor, str) and campo.valor.upper() not in _ufs():
        return False, "contexto_irrelevante"
    return True, None


def _passa_cross_field(
    _nome: str, _campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
    # por enquanto so checa estado vs municipio (mais simples)
    # pra fazer bacia x UF direito precisa de tabela bacia->UFs, fica pra depois
    # quando tiver tabela ibge completa volto aqui
    return True, None


def _eh_especie_generica(nome: str) -> bool:
    # fix 4: detecta especies que sao na verdade palavras genericas/girai
    if not nome:
        return False
    tokens = re.findall(r"\w+", nome.lower())
    for t in tokens:
        if t in ESPECIES_STOP_TERMS:
            return True
    return False


def _passa_especies_stop_terms(
    nome_campo: str, campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
    # rejeita especies genericas. lista tipo [{"nome": "peixe grande"}] todas
    # ou so algumas?
    # politica atual: se QUALQUER item da lista for generico, rejeita o campo
    # inteiro. melhor aceitar menos do que deixar lixo passar.
    if nome_campo != "especies" or campo.valor is None:
        return True, None
    if not isinstance(campo.valor, list):
        return True, None
    for e in campo.valor:
        nome = e.get("nome", "") if isinstance(e, dict) else str(e)
        if _eh_especie_generica(nome):
            return False, "contexto_irrelevante"
    return True, None


def _passa_tipo_ceva_blacklist(
    nome_campo: str, campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
    # fix 3: rejeita tipo_ceva com termo de equipamento.
    # "vara de bambu", "carretilha avenado", "hunter bait" sao coisas de
    # EQUIPAMENTO de pesca, nao ceva. extrator confunde em textos grandes
    if nome_campo != "tipo_ceva" or campo.valor is None:
        return True, None
    if not isinstance(campo.valor, str):
        return True, None
    tokens = re.findall(r"\w+", campo.valor.lower())
    for t in tokens:
        if t in EQUIPAMENTO_BLACKLIST:
            return False, "contexto_irrelevante"
    return True, None


def _passa_rio_aparece(
    nome_campo: str, campo: CampoExtraido, transcricao: str, _outros: dict
) -> _Assinatura:
    # fix 2: rio deve aparecer LITERALMENTE (ou fuzzy) no texto
    if nome_campo != "rio" or campo.valor is None:
        return True, None
    if not isinstance(campo.valor, str):
        return True, None
    if not rio_aparece_no_texto(campo.valor, transcricao):
        return False, "alucinacao_suspeita"
    return True, None


def _passa_ceva_keywords(
    nome_campo: str, campo: CampoExtraido, transcricao: str, _outros: dict
) -> _Assinatura:
    # tipo_ceva so eh valido se o texto mencionar ceva/seva/ceba/cevar/cevador
    # pescaria com so isca viva/artificial nao tem ceva, extrator chuta essa
    # campo e enche com "ceva_solta_na_agua" default
    if nome_campo != "tipo_ceva" or campo.valor is None:
        return True, None
    texto_norm = transcricao.lower()
    for kw in CEVA_KEYWORDS:
        if kw in texto_norm:
            return True, None
    return False, "evidencia_nao_alinha"


def _passa_length_obs(
    nome_campo: str, campo: CampoExtraido, _transcricao: str, _outros: dict
) -> _Assinatura:
    if nome_campo != "observacoes" or campo.valor is None:
        return True, None
    if not isinstance(campo.valor, str):
        return True, None
    n_palavras = len(campo.valor.split())
    # minimo baixado de 10 pra 6 pra salvar resumos curtos mas legitimos
    # tipo "pesca de manha com ceva de milho rendeu tucunare"
    if n_palavras < 6:
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

    # todas as regras agora tem a mesma assinatura, entao a lista eh uniforme
    # e o loop nao precisa de gambiarra de try/except ou lambdas adaptadoras.
    # ordem importa: mais baratas primeiro, depois as especificas por campo.
    ordem = [
        _passa_confianca,
        _passa_smith_waterman,
        _passa_pos_filter,
        _passa_enum_estado,
        _passa_cross_field,
        _passa_length_obs,
        _passa_ceva_keywords,
        # _passa_rio_aparece REMOVIDA: bloqueava canonizacao legitima tipo
        # "velho chico"->"Rio Sao Francisco". smith_waterman + critic llm
        # dao conta melhor do caso. funcao rio_aparece_no_texto() segue
        # no modulo pra quem quiser usar como feature (flag) no futuro
        _passa_tipo_ceva_blacklist,
        _passa_especies_stop_terms,
    ]

    for regra in ordem:
        ok, tipo = regra(nome_campo, campo, transcricao, outros)
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
