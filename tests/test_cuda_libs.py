import os
from unittest.mock import patch

from src.transcriber import cuda_libs


def test_nao_carrega_libnvblas():
    # regra dura: libnvblas NUNCA pode ser pre-carregada (causa segfault)
    assert not cuda_libs._eh_lib_permitida("libnvblas.so.12")
    assert not cuda_libs._eh_lib_permitida("libnvblas.so")
    # ate variacoes sozinhas
    assert not cuda_libs._eh_lib_permitida("nvblas.so")


def test_carrega_cublas_e_cudnn():
    assert cuda_libs._eh_lib_permitida("libcublas.so.12")
    assert cuda_libs._eh_lib_permitida("libcublasLt.so.12")
    assert cuda_libs._eh_lib_permitida("libcudnn.so.9")
    assert cuda_libs._eh_lib_permitida("libcudnn_cnn.so.9")


def test_nao_carrega_libs_desconhecidas():
    # filtro de whitelist: so as q estao listadas passam
    assert not cuda_libs._eh_lib_permitida("libfoo.so")
    assert not cuda_libs._eh_lib_permitida("librandom.so.1")


def test_cpu_nao_preload(monkeypatch):
    # se WHISPER_DEVICE=cpu, nao deve tentar carregar as libs cuda
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")
    # reseta o state interno
    monkeypatch.setattr(cuda_libs, "_ja_rodou", False)
    # nao deve levantar nada
    cuda_libs.pre_carrega_libs_cuda()


def test_preload_eh_idempotente(monkeypatch):
    # chamar varias vezes nao deve causar problema
    monkeypatch.setattr(cuda_libs, "_ja_rodou", False)
    cuda_libs.pre_carrega_libs_cuda()
    cuda_libs.pre_carrega_libs_cuda()
    cuda_libs.pre_carrega_libs_cuda()
    # segundo+ skip por causa do _ja_rodou=True
    assert cuda_libs._ja_rodou is True
