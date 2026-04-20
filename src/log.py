# logger super simples.
#
# a ideia nao eh substituir 100% dos prints — alguns prints sao mensagem
# pro user (make status, make queries) e devem continuar via print. aqui
# eh pra mensagens de PIPELINE: progresso de download, erro de baixar
# video x, retry de schema, etc.
#
# por padrao o log esta DESLIGADO (nivel WARNING) pra nao poluir o terminal.
# passa --verbose no cli pra ver tudo.

import logging
import os
import sys


_LOGGER: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    lg = logging.getLogger("peixes")
    lg.setLevel(_nivel_padrao())
    # formato simples — sem timestamp iso, sem cor. estilo dos prints do projeto
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("%(message)s"))
    lg.addHandler(h)
    lg.propagate = False
    _LOGGER = lg
    return lg


def _nivel_padrao() -> int:
    # PEIXES_LOG=info|debug|warn liga o log. sem env, fica silencioso
    v = os.getenv("PEIXES_LOG", "warn").lower()
    return {"debug": logging.DEBUG, "info": logging.INFO,
            "warn": logging.WARNING, "error": logging.ERROR}.get(v, logging.WARNING)


def set_verbose(on: bool):
    lg = get_logger()
    lg.setLevel(logging.DEBUG if on else _nivel_padrao())
