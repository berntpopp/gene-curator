.PHONY: help install dev build preview lint format type-check test clean setup
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Gene Curator Frontend - Development Commands"
	@echo "============================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	npm install

dev: ## Start development server
	npm run dev

build: ## Build for production
	npm run build

preview: ## Preview production build
	npm run preview

lint: ## Run all linting checks
	node scripts/lint.js

format: ## Auto-format all code
	node scripts/format.js

lint-only: ## Run ESLint check only  
	npm run lint:check

test: ## Run all tests and linting
	npm run test:lint

clean: ## Clean build artifacts and cache
	rm -rf dist/
	rm -rf node_modules/.cache/
	rm -rf .eslintcache
	rm -rf *.tsbuildinfo

setup: install ## Set up development environment
	@echo "Installing pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		echo "✅ Pre-commit hooks installed"; \
	else \
		echo "⚠️  pre-commit not found. Install with: pip install pre-commit"; \
	fi
	@echo "Development environment ready!"
	@echo "Run 'make lint' to check code quality"
	@echo "Run 'make format' to auto-format code"

update-deps: ## Update dependencies
	npm update
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit autoupdate; \
	fi