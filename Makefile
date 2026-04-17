# atalhos pro pipeline. tudo assume que o venv ta em .venv/

PY := .venv/bin/python

.PHONY: help setup check models status buscar baixar transcrever extrair verificar exportar limpar reset

help:
	@echo "comandos disponiveis:"
	@echo "  make setup       - bootstrap completo (venv, deps, modelos, .env)"
	@echo "  make check       - verifica pre-requisitos (python, ffmpeg, ollama, gpu)"
	@echo "  make models      - baixa os modelos ollama (qwen, llama, gemma)"
	@echo "  make status      - mostra quantos videos estao em cada etapa"
	@echo ""
	@echo "pipeline (roda em sequencia, cada um depende do anterior):"
	@echo "  make buscar Q='pesca com ceva' N=50    - acha videos no youtube"
	@echo "  make baixar N=50                         - baixa audio dos pendentes"
	@echo "  make transcrever N=50                    - whisper nos baixados"
	@echo "  make extrair N=50                        - gliner + qwen nos transcritos"
	@echo "  make verificar N=50                      - regras + llama critic nos extraidos"
	@echo "  make exportar                            - gera csv final da planilha"
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

buscar:
	@$(PY) -m src.main buscar --queries $(Q) --max-por-query $(N)

baixar:
	@$(PY) -m src.main baixar --limit $(N)

transcrever:
	@$(PY) -m src.main transcrever --limit $(N)

extrair:
	@$(PY) -m src.main extrair --limit $(N)

verificar:
	@$(PY) -m src.main verificar --limit $(N)

exportar:
	@$(PY) -m src.main exportar

# atalhao pra rodar tudo em sequencia com valores default
# util pra um teste rapido com poucos videos
run-tudo:
	@$(PY) -m src.main buscar --queries $(Q) --max-por-query $(N)
	@$(PY) -m src.main baixar --limit $(N)
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
