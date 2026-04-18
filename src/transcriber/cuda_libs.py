import ctypes
import os
import site
from pathlib import Path


# hack pro faster-whisper achar as libs cuda (cublas/cudnn) que vem instaladas
# via pip nos pacotes nvidia-*
#
# sem isso da "libcublas.so.12 not found" mesmo com as libs no venv, pq
# as libs nao estao no LD_LIBRARY_PATH padrao do sistema.
#
# CUIDADO: tem que FILTRAR bem quais .so pre-carregar.
# nunca pre-carregar libnvblas.so pq ela fica ativa pra todo numpy/scipy do
# processo e causa "cublasXtSgemm failed" em qualquer operacao blas, ate
# segfault em alguns casos.


_ja_rodou = False


# so essas sao carregadas. o resto (principalmente libnvblas) fica de fora
LIBS_OK = (
    "libcublas.so",
    "libcublasLt.so",
    "libcudart.so",
    "libcudnn.so",
    "libcudnn_cnn.so",
    "libcudnn_ops.so",
    "libcudnn_graph.so",
    "libcudnn_engines_runtime_compiled.so",
    "libcudnn_engines_precompiled.so",
    "libcudnn_heuristic.so",
    "libcudnn_adv.so",
)


def _eh_lib_permitida(nome: str) -> bool:
    # nvblas NUNCA, nem em sonho
    if "nvblas" in nome:
        return False
    return any(nome.startswith(ok) for ok in LIBS_OK)


def pre_carrega_libs_cuda():
    global _ja_rodou
    if _ja_rodou:
        return
    _ja_rodou = True

    # se o user nao tem gpu, sai logo
    if os.getenv("WHISPER_DEVICE") == "cpu":
        return

    # procura as libs nvidia-* instaladas no site-packages do venv
    candidatos: list[Path] = []
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        nv = Path(sp) / "nvidia"
        if nv.exists():
            for lib_dir in nv.glob("*/lib"):
                candidatos.append(lib_dir)

    if not candidatos:
        return

    # preload com filtro, so libs que interessam pro faster-whisper
    # ordem: cublas/cudart primeiro, cudnn depois
    ordem_preferida = ["cublas", "cudart", "cudnn"]
    pastas_ordenadas = sorted(candidatos, key=lambda p: next(
        (i for i, n in enumerate(ordem_preferida) if n in str(p)), 99
    ))

    for lib_dir in pastas_ordenadas:
        for so in sorted(lib_dir.glob("*.so*")):
            if not _eh_lib_permitida(so.name):
                continue
            try:
                ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                # se uma nao abriu nao tem problema, outras podem resolver
                pass
