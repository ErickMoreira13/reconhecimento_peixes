import os
from unittest.mock import patch

from src import config


def test_config_lista_keys_do_env():
    # config lê YOUTUBE_API_KEYS separadas por virgula
    # conftest.py seta com "fake_key_1,fake_key_2"
    assert len(config.YOUTUBE_API_KEYS) >= 1


def test_config_tem_modelos_default():
    assert config.MODEL_EXTRATOR
    assert config.MODEL_VERIFICADOR
    assert config.WHISPER_MODEL


def test_checa_keys_levanta_quando_vazio(monkeypatch):
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", [])
    import pytest
    with pytest.raises(RuntimeError, match="cade as YOUTUBE_API_KEYS"):
        config.checa_keys()


def test_checa_keys_ok_quando_tem(monkeypatch, capsys):
    monkeypatch.setattr(config, "YOUTUBE_API_KEYS", ["k1", "k2"])
    config.checa_keys()
    saida = capsys.readouterr().out
    assert "2 keys" in saida


def test_data_dir_eh_path():
    from pathlib import Path
    assert isinstance(config.DATA_DIR, Path)
    assert isinstance(config.RAW_AUDIO_DIR, Path)
    assert isinstance(config.TRANSCR_DIR, Path)
    assert isinstance(config.RESULTS_DIR, Path)
