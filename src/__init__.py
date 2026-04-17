import os

# evita warnings do nvblas quando o sistema tem config global apontando pra gpu
# mas o numpy/scipy nao deveria usar (caso do nosso pipeline)
# sem isso da um monte de "NVBLAS cublasXtSgemm failed" no stderr
os.environ.setdefault("NVBLAS_CONFIG_FILE", "/dev/null")

# limita threads blas, senao em maquina sem gpu ele usa todos os cores e fica
# competindo com o whisper/ollama
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
