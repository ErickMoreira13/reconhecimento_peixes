# utilitarios de normalizacao de texto, SSOT.
#
# antes a funcao "tirar acento" estava duplicada em 4 lugares (prompts.py,
# gazetteer_check.py, regras.py x2). um lugar so agora.

import unicodedata


def sem_acento(s: str) -> str:
    # remove acentos. "tucunaré" -> "tucunare". usado pra matching robusto
    # contra transcricoes do whisper que as vezes vem sem acento
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def normaliza(s) -> str:
    # lowercase + strip + sem acento. pra comparar strings livres
    return sem_acento(str(s)).lower().strip()
