.PHONY: help install lint format type-check security-check test clean dev
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Gene Curator Backend - Development Commands"
	@echo "==========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --extra dev

lint: ## Run all linting checks
	uv run python scripts/lint.py

format: ## Auto-format code
	uv run python scripts/format.py

type-check: ## Run type checking only
	uv run mypy app/

security-check: ## Run security checks only
	uv run bandit -r app/ -f json

test: ## Run tests
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ --cov=app --cov-report=html --cov-report=term

clean: ## Clean build artifacts and cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/

dev: install ## Set up development environment
	pre-commit install
	@echo "Development environment ready!"
	@echo "Run 'make lint' to check code quality"
	@echo "Run 'make format' to auto-format code"

pre-commit: ## Run pre-commit hooks manually
	pre-commit run --all-files

update-deps: ## Update dependencies
	uv lock --upgrade
	pre-commit autoupdate