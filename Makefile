# atalhos pro pipeline. tudo assume que o venv ta em .venv/

PY := .venv/bin/python
PYTEST := .venv/bin/pytest

.PHONY: help setup check models status buscar baixar transcrever extrair verificar exportar dashboard tests limpar reset

help:
	@echo "comandos disponiveis:"
	@echo "  make setup       - bootstrap completo (venv, deps, modelos, .env)"
	@echo "  make check       - verifica pre-requisitos (python, ffmpeg, ollama, gpu)"
	@echo "  make models      - baixa os modelos ollama (qwen, llama, gemma)"
	@echo "  make status      - mostra quantos videos estao em cada etapa"
	@echo "  make dashboard   - abre dashboard web em localhost:8000"
	@echo ""
	@echo "pipeline (roda em sequencia, cada um depende do anterior):"
	@echo "  make buscar Q='pesca com ceva' N=50    - acha videos no youtube"
	@echo "  make baixar N=50 W=4                     - baixa audio (W workers paralelos)"
	@echo "  make transcrever N=50                    - whisper nos baixados"
	@echo "  make extrair N=50                        - gliner + qwen nos transcritos"
	@echo "  make verificar N=50                      - regras + llama critic nos extraidos"
	@echo "  make exportar                            - gera csv final da planilha"
	@echo "  make run-tudo    - roda tudo em sequencia"
	@echo ""
	@echo "qualidade / debug:"
	@echo "  make tests       - roda testes unitarios"
	@echo "  make test-fast   - testes sem verbose"
	@echo "  make test-cov    - testes com coverage report"
	@echo "  make lint        - roda ruff"
	@echo "  make analise     - analise detalhada do ultimo benchmark"
	@echo "  make benchmark MODELOS='qwen2.5:7b llama3.1:8b' N=50"
	@echo ""
	@echo "util:"
	@echo "  make limpar      - apaga pastas data/ e db (NAO volta)"
	@echo "  make reset       - apaga venv tb"

setup:
	@bash setup.sh

check:
	@bash scripts/check-env.sh

models:
	@bash scripts/models.sh

status:
	@$(PY) -m src.main status

# parametros padrao, pode sobrescrever com make buscar Q="..." N=100
Q ?= "pesca com ceva"
N ?= 50
W ?= 4

buscar:
	@$(PY) -m src.main buscar --queries $(Q) --max-por-query $(N)

baixar:
	@$(PY) -m src.main baixar --limit $(N) --workers $(W)

transcrever:
	@$(PY) -m src.main transcrever --limit $(N)

extrair:
	@$(PY) -m src.main extrair --limit $(N)

verificar:
	@$(PY) -m src.main verificar --limit $(N)

exportar:
	@$(PY) -m src.main exportar

dashboard:
	@echo "abrindo dashboard em http://localhost:8000 (ctrl+c pra parar)"
	@$(PY) -m uvicorn src.dashboard.server:app --host 0.0.0.0 --port 8000 --reload

tests:
	@$(PYTEST)

test-cov:
	@$(PY) -m pytest tests/ --cov=src --cov-report=term-missing 2>&1 | tail -40

test-fast:
	@$(PYTEST) -q --tb=no

lint:
	@$(PY) -m ruff check src/ tests/ 2>&1 || echo "ruff reportou issues acima"

analise:
	@$(PY) scripts/analise_benchmark.py

benchmark:
	@$(PY) -m src.benchmark --modelos $(MODELOS) --limit $(N)

# atalhao pra rodar tudo em sequencia com valores default
# util pra um teste rapido com poucos videos
run-tudo:
	@$(PY) -m src.main buscar --queries $(Q) --max-por-query $(N)
	@$(PY) -m src.main baixar --limit $(N) --workers $(W)
	@$(PY) -m src.main transcrever --limit $(N)
	@$(PY) -m src.main extrair --limit $(N)
	@$(PY) -m src.main verificar --limit $(N)
	@$(PY) -m src.main exportar

limpar:
	@echo "vai apagar data/ . confirma?"
	@read -p "[s/n] " c; [ "$$c" = "s" ] && rm -rf data/ || echo "cancelado"

reset: limpar
	@echo "tb vai apagar venv. confirma?"
	@read -p "[s/n] " c; [ "$$c" = "s" ] && rm -rf .venv || echo "cancelado"
