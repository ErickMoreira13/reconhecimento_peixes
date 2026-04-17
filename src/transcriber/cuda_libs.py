import ctypes
import os
import site
import sys
from pathlib import Path


# hack pro faster-whisper achar as libs cuda (cublas/cudnn) que vem instaladas
# via pip nos pacotes nvidia-*
#
# sem isso da "libcublas.so.12 not found" mesmo com as libs no venv, pq
# o libcblas nao ta no LD_LIBRARY_PATH padrao do sistema.
#
# o truque eh usar ctypes pra abrir as .so com RTLD_GLOBAL antes do faster-whisper
# carregar o modelo. ai quando o faster-whisper procurar as libs, elas ja estao
# no namespace global do processo.
#
# chamar uma vez antes de importar WhisperModel


_ja_rodou = False


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

    # ordem importa: cublas depende de cudart, cudnn tem varios modulos internos
    # entao a gente so adiciona TODAS as pastas ao LD_LIBRARY_PATH e preload as .so
    paths_str = ":".join(str(p) for p in candidatos)
    atual = os.environ.get("LD_LIBRARY_PATH", "")
    if paths_str not in atual:
        os.environ["LD_LIBRARY_PATH"] = f"{paths_str}:{atual}".rstrip(":")

    # dlopen com RTLD_GLOBAL pra gerar visibilidade global
    # ordem: cublas/cudart primeiro, cudnn depois
    ordem_preferida = ["cublas", "cudart", "cudnn"]
    pastas_ordenadas = sorted(candidatos, key=lambda p: next(
        (i for i, n in enumerate(ordem_preferida) if n in str(p)), 99
    ))

    for lib_dir in pastas_ordenadas:
        for so in sorted(lib_dir.glob("*.so*")):
            try:
                ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                # se uma nao abriu nao tem problema, outras podem resolver
                pass
