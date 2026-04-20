from src.texto import sem_acento, normaliza


def test_sem_acento_remove_acentos():
    assert sem_acento("tucunaré") == "tucunare"
    assert sem_acento("São Paulo") == "Sao Paulo"
    assert sem_acento("Rondônia") == "Rondonia"


def test_sem_acento_mantem_letras_normais():
    assert sem_acento("pacu") == "pacu"


def test_sem_acento_vazio_e_none():
    assert sem_acento("") == ""
    assert sem_acento(None) == ""


def test_normaliza_aplica_tudo():
    assert normaliza("  São Paulo  ") == "sao paulo"
    assert normaliza("RIO MADEIRA") == "rio madeira"


def test_normaliza_nao_crasha_com_num():
    assert normaliza(42) == "42"
    assert normaliza(None) == "none"
