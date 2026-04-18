import os

# limita threads blas, senao em maquina sem gpu ele usa todos os cores e fica
# competindo com o whisper/ollama
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

# IMPORTANTE: NAO setar NVBLAS_CONFIG_FILE aqui.
# se tentar setar pra /dev/null ele ainda tenta inicializar nvblas e crasha.
# o fix real eh no src/transcriber/cuda_libs.py que filtra libnvblas do preload.
