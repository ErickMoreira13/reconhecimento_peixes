import logging
import os

import pytest

from src import log as logmod


@pytest.fixture(autouse=True)
def _reset_logger():
    # reset entre testes pq o logger eh singleton
    logmod._LOGGER = None
    yield
    logmod._LOGGER = None


def test_get_logger_retorna_mesma_instancia():
    l1 = logmod.get_logger()
    l2 = logmod.get_logger()
    assert l1 is l2


def test_nivel_padrao_eh_warning():
    # sem env, silencia info/debug
    os.environ.pop("PEIXES_LOG", None)
    logmod._LOGGER = None
    lg = logmod.get_logger()
    assert lg.level == logging.WARNING


def test_nivel_custom_via_env(monkeypatch):
    monkeypatch.setenv("PEIXES_LOG", "info")
    logmod._LOGGER = None
    lg = logmod.get_logger()
    assert lg.level == logging.INFO


def test_set_verbose_muda_pra_debug():
    lg = logmod.get_logger()
    logmod.set_verbose(True)
    assert lg.level == logging.DEBUG
    logmod.set_verbose(False)
    assert lg.level == logging.WARNING


def test_env_invalido_cai_em_warning(monkeypatch):
    monkeypatch.setenv("PEIXES_LOG", "sla")
    logmod._LOGGER = None
    lg = logmod.get_logger()
    assert lg.level == logging.WARNING
