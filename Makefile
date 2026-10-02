.PHONY: help install bootstrap demo web test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (no model downloads)
	pip install -e ".[dev]"

bootstrap: ## Generate data, create DB, seed, build indexes, add demo candidates
	python -m src bootstrap

demo: ## Run one evaluation and print the decision card
	python -m src demo

web: ## Start the web UI (http://127.0.0.1:8000)
	python -m src web

test: ## Run tests
	pytest -q

lint: ## Run linter
	ruff check src/ tests/ scripts/

clean: ## Remove generated data, database, and caches
	rm -f kriterion.db data/mock/*.json data/reference/*.json
	rm -rf __pycache__ .pytest_cache .ruff_cache
