# ascii art maiores pra banners com o nome do projeto.
# ui_banners.py tem os pequenos (peixe, caixinha, ondinha).
# aqui moram os figlets grandes + cores ansi pra colorir output cli.

# -------- cores ansi --------
# nivel de cor eh cheio de overhead — mantive so o essencial.
# se o terminal nao suporta, ansi vira texto visivel feio. decisao: se
# NO_COLOR estiver setado (padrao de facto), desliga cores.

import os

_NO_COLOR = bool(os.getenv("NO_COLOR"))


def _c(code: str) -> str:
    return "" if _NO_COLOR else f"\033[{code}m"


RESET = _c("0")
BOLD = _c("1")
DIM = _c("2")

# cores principais, mnemonicos
AZUL = _c("34")
AZUL_CLARO = _c("94")
VERDE = _c("32")
VERDE_CLARO = _c("92")
AMARELO = _c("33")
AMARELO_CLARO = _c("93")
CIANO = _c("36")
CIANO_CLARO = _c("96")
MAGENTA = _c("35")
VERMELHO = _c("31")
BRANCO = _c("97")


def colore(texto: str, cor: str) -> str:
    # helper rapido pra colorir uma string e resetar no fim
    return f"{cor}{texto}{RESET}"


# -------- banners grandes --------

# nome do projeto em ascii. feito a mao, estilo block fonte. nao usei
# figlet — figlets "perfeitos" parecem gerados por IA. esse ficou rustico
NOME_PEIXES = r"""
   ____   ____  _
  |  _ \ | ___|(_)_  __ ___ ___
  | |_) ||  _| | \ \/ // _ | __|
  |  __/ | |___| |>  <|  __|__ \
  |_|    |_____|_/_/\_\\___|___/
     reconhecimento_peixes
"""


BANNER_GRANDE = r"""
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      ><(((o>       ~  ~  ~       ><((((((((o>
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     pipeline de mineracao de videos de pescaria
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""


def banner_projeto() -> str:
    # banner completo, colorido, pra abertura do make dos comandos
    return (
        f"{AZUL}{NOME_PEIXES}{RESET}"
        f"{CIANO}{BANNER_GRANDE}{RESET}"
    )


def banner_pipeline(etapa: str) -> str:
    # banner curto pra cada etapa do pipeline (buscar, baixar, etc)
    # etapa colorida em amarelo, resto ciano
    return (
        f"\n{CIANO}~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~{RESET}\n"
        f"   {AMARELO_CLARO}><(((o>{RESET}   "
        f"{BOLD}{BRANCO}{etapa}{RESET}\n"
        f"{CIANO}~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~{RESET}\n"
    )


def marca_ok(texto: str) -> str:
    return colore(f"[ok] {texto}", VERDE_CLARO)


def marca_erro(texto: str) -> str:
    return colore(f"[erro] {texto}", VERMELHO)


def marca_warn(texto: str) -> str:
    return colore(f"[aviso] {texto}", AMARELO_CLARO)


def marca_info(texto: str) -> str:
    return colore(f"[info] {texto}", CIANO_CLARO)
