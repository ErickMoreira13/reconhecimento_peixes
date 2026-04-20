# banners em ascii pra deixar o console menos cru
# tudo minusculo, estilo rustico msm. nada de figlet gigante perfeito
#
# se precisar mais, adicionar aqui e reusar em vez de replicar

PEIXE = r"   ><(((o>"
PEIXE_GRANDE = r"  ><((((((((o>"
PEIXE_ESQUERDA = r"<o)))><"    # peixe olhando pra esquerda
PEIXE_CARDUME = r"><(((o>  ><(((o>  ><(((o>"   # tres peixes em cardume

# onda de rio, 3 variacoes pra alternar e parecer menos mecanico
ONDA = "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
ONDAS_ALT = "~~  ~~  ~~  ~~  ~~  ~~  ~~  ~~  ~~  ~~  ~~  ~~"

LINHA = "=" * 52
LINHA_FINA = "-" * 52


def banner_harvester() -> str:
    return f"""
{ONDA}
   ><(((o>       ~  ~  ~     ><(((o>       ~  ~
{ONDA}
   harvester loop - coleta ate saturar
"""


def banner_extrator() -> str:
    return f"""
{ONDAS_ALT}
   extrator: gliner + qwen/llama
{ONDAS_ALT}
"""


def banner_verificador() -> str:
    return f"""
{ONDAS_ALT}
   verificador: regras + critic (llama 3.1)
{ONDAS_ALT}
"""


def banner_gliner_labels() -> str:
    return f"""
{LINHA}
  teste gliner: 2 labels vs 4 labels
  (peixe, bacia) vs (peixe, bacia, rio, municipio)
{LINHA}
"""


def banner_queries() -> str:
    return f"""
{ONDAS_ALT}
  status das queries do harvester
{ONDAS_ALT}
"""


def banner_fim(titulo: str = "pronto") -> str:
    # banner de final generico, usado no fim do loop/script
    return f"\n{LINHA_FINA}\n  {titulo}\n{LINHA_FINA}\n"


def caixa(titulo: str, linhas: list[str]) -> str:
    # desenha uma caixa simples em volta de umas linhas
    # largura minima 50, ou maior se tiver conteudo mais longo
    largura = max(50, max((len(ln) for ln in linhas), default=0), len(titulo)) + 2
    topo = "+" + "-" * largura + "+"
    meio_titulo = f"| {titulo.ljust(largura - 1)}|"
    sep = "|" + "-" * largura + "|"
    corpo = "\n".join(f"| {ln.ljust(largura - 1)}|" for ln in linhas)
    return f"{topo}\n{meio_titulo}\n{sep}\n{corpo}\n{topo}"
