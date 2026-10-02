.PHONY: help install dev up down seed demo test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -e ".[dev]"

dev: ## Install with dev dependencies
	pip install -e ".[dev]"

up: ## Start all services via Docker Compose
	docker compose up -d

down: ## Stop all services
	docker compose down

seed: ## Generate mock data and seed database + Milvus
	python scripts/generate_mock_data.py
	python scripts/seed_database.py
	python scripts/seed_vector_store.py

demo: ## Run end-to-end demo
	python scripts/run_demo.py

test: ## Run tests
	pytest tests/ -v

lint: ## Run linter
	ruff check src/ tests/

clean: ## Clean generated files
	rm -rf data/mock/*.json data/reference/*.json __pycache__ .pytest_cache .ruff_cache
