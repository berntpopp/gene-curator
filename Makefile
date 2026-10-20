# Gene Curator - command surface. `make help` lists every target (from the ## comments).
# Local runs and GitHub Actions call the same targets: if `make ci` passes, CI passes.

.DEFAULT_GOAL := help
SHELL := /bin/bash

include .env.dev
export

DC_INFRA := docker compose -f docker-compose.yml --env-file .env.dev
DC_DEV   := docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev
DC_PROD  := docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.dev
POSTGRES_CONTAINER := gene_curator_postgres
BACKUP_DIR := backups
BASE ?= origin/master
# Changed lines must be covered (AGENTS.md). Global floors live in pyproject.toml / vite.config.js.
DIFF_COVER_MIN ?= 90
# Same as CI: a stale uv.lock is an error, not a silent re-lock
export UV_FROZEN ?= 1

help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

##@ Setup
install: ## Install backend + frontend deps and git hooks
	cd backend && uv sync --extra dev
	cd frontend && npm ci --no-audit --no-fund
	git config core.hooksPath .githooks

##@ Hybrid development (DB in Docker, API/UI local - recommended)
hybrid-up: services-up ## Start Postgres + Redis, then run `make backend` and `make frontend`
	@echo "API: make backend -> http://localhost:$(BACKEND_PORT)/docs | UI: make frontend -> http://localhost:$(VITE_DEV_PORT)"

hybrid-down: ## Stop local API/UI and DB services
	-pkill -f "uvicorn app.main:app"
	-pkill -f "vite.*$(VITE_DEV_PORT)"
	$(MAKE) services-down

services-up: ## Start only Postgres + Redis
	$(DC_INFRA) up -d --wait postgres redis

services-down: ## Stop Postgres + Redis
	$(DC_INFRA) stop postgres redis

backend: ## Run the API locally with reload
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

frontend: ## Run the Vite dev server locally
	cd frontend && npm run dev -- --host 0.0.0.0 --port $(VITE_DEV_PORT)

##@ Full Docker
dev: ## Start all services in Docker
	$(DC_DEV) up -d

dev-build: ## Rebuild and start all services
	$(DC_DEV) up -d --build

dev-down: ## Stop all services
	$(DC_DEV) down

dev-logs: ## Follow logs of all services
	$(DC_DEV) logs -f

prod: ## Start the production stack
	$(DC_PROD) up -d

prod-build: ## Rebuild and start the production stack
	$(DC_PROD) up -d --build

prod-down: ## Stop the production stack
	$(DC_PROD) down

prod-logs: ## Follow production logs
	$(DC_PROD) logs -f

##@ Database
db-reset: ## DESTRUCTIVE: drop the dev volume and rebuild from database/sql
	@read -p "Delete ALL dev data? [y/N] " r; [[ $$r =~ ^[Yy]$$ ]] || exit 1
	$(DC_DEV) down -v
	$(DC_INFRA) up -d --wait postgres

db-migrate: ## Apply one SQL file to the dev DB: make db-migrate FILE=database/sql/027_x.sql
	@test -n "$(FILE)" || { echo "usage: make db-migrate FILE=database/sql/<file>.sql"; exit 1; }
	docker exec -i $(POSTGRES_CONTAINER) psql -v ON_ERROR_STOP=1 -U $(POSTGRES_USER) -d $(POSTGRES_DB) < $(FILE)

db-shell: ## Open psql in the dev DB
	docker exec -it $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-backup: ## Dump the dev DB to backups/
	@mkdir -p $(BACKUP_DIR)
	docker exec $(POSTGRES_CONTAINER) pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) -F c > $(BACKUP_DIR)/backup_$$(date +%Y%m%d_%H%M%S).dump

db-restore: ## Restore a dump: make db-restore FILE=backups/x.dump
	@test -f "$(FILE)" || { echo "usage: make db-restore FILE=backups/<file>.dump"; exit 1; }
	docker exec -i $(POSTGRES_CONTAINER) pg_restore -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c < $(FILE)

##@ Status
status: ## Containers and row counts
	@docker ps --filter "name=gene_curator" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@docker exec $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "SELECT (SELECT COUNT(*) FROM scopes) scopes, (SELECT COUNT(*) FROM genes) genes, (SELECT COUNT(*) FROM curations) curations, (SELECT COUNT(*) FROM users) users;" 2>/dev/null || echo "DB not running"

health: ## Probe API, UI and DB
	@curl -fsS http://localhost:$(BACKEND_PORT)/health && echo || echo "API down"
	@curl -fsS -o /dev/null http://localhost:$(VITE_DEV_PORT) && echo "UI up" || echo "UI down"
	@docker exec $(POSTGRES_CONTAINER) pg_isready -U $(POSTGRES_USER) || true

##@ Fast loop
check: ## Fast pre-push gate: lint, types, size limit, unit tests (no coverage)
	cd backend && uv run ruff check app tests && uv run ruff format --check app tests && uv run mypy app && uv run pytest -q
	cd frontend && npm run lint:check && npm run format:check && npm run typecheck && npx vitest run
	python3 scripts/check_file_size.py

format: ## Auto-fix formatting and lint (backend + frontend)
	cd backend && uv run ruff check --fix app tests && uv run ruff format app tests
	cd frontend && npm run lint && npm run format

test: ## Backend tests (SQLite)
	cd backend && uv run pytest

test-postgres: ## Backend RLS/scope tests on a throwaway Postgres built from database/sql
	scripts/test-postgres.sh -q

test-frontend: ## Frontend unit tests
	cd frontend && npx vitest run

test-e2e: ## Playwright E2E (needs `make hybrid-up`, backend and frontend running)
	cd frontend && npm run test:e2e

##@ CI (GitHub Actions runs exactly these)
ci: ci-backend test-postgres ci-frontend ci-repo diff-cover ## Everything CI runs

ci-backend: api-types-check ## Backend: ruff, mypy, bandit, tests + coverage floor, API types fresh
	cd backend && uv run ruff check app tests && uv run ruff format --check app tests \
		&& uv run mypy app && uv run bandit -q -c .bandit -r app \
		&& uv run pytest -q --cov=app --cov-report=xml --cov-report=term:skip-covered

ci-frontend: ## Frontend: eslint, prettier, vue-tsc, tests + coverage floor, build
	cd frontend && npm run lint:check && npm run format:check && npm run typecheck \
		&& npx vitest run --coverage && npm run build

ci-repo: workflows ## Repo rules: file size limit, workflow lint
	python3 scripts/check_file_size.py

diff-cover: ## Changed lines must be >= $(DIFF_COVER_MIN)% covered (uses whichever coverage reports exist)
	@if [ -f frontend/coverage/lcov.info ]; then sed 's#^SF:#SF:frontend/#' frontend/coverage/lcov.info > frontend/coverage/lcov.repo.info; fi
	uvx diff-cover@9.7.1 $$(ls backend/coverage.xml frontend/coverage/lcov.repo.info 2>/dev/null) \
		--compare-branch=$(BASE) --fail-under=$(DIFF_COVER_MIN)

api-types: ## Regenerate frontend/src/types/api.generated.ts from the backend OpenAPI schema
	cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" 2>/dev/null > ../frontend/openapi.json
	cd frontend && npx --yes openapi-typescript@7.13.0 openapi.json -o src/types/api.generated.ts && rm openapi.json

api-types-check: api-types ## Fail if the generated API types are stale
	git diff --exit-code -- frontend/src/types/api.generated.ts

audit: audit-backend audit-frontend ## Known-vulnerability scan of both lockfiles

audit-backend: ## pip-audit against backend/uv.lock
	cd backend && uv export --frozen --no-hashes --no-emit-project --all-extras \
		| uvx pip-audit@2.10.0 --strict --disable-pip --no-deps -r /dev/stdin

audit-frontend: ## npm audit (high and critical) of shipped dependencies; dev tooling is not shipped
	cd frontend && npm audit --omit=dev --audit-level=high

workflows: ## Lint GitHub workflows (zizmor)
	uvx zizmor@1.31.1 --min-severity medium .github/

##@ Cleanup
clean: ## Remove caches and build output
	find backend -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	rm -rf backend/htmlcov backend/coverage.xml frontend/dist frontend/coverage

clean-all: ## DESTRUCTIVE: stop everything and delete Docker volumes
	@read -p "Delete ALL Docker volumes for this project? [y/N] " r; [[ $$r =~ ^[Yy]$$ ]] || exit 1
	$(DC_DEV) down -v --remove-orphans

.PHONY: help install hybrid-up hybrid-down services-up services-down backend frontend dev dev-build dev-down dev-logs \
	prod prod-build prod-down prod-logs db-reset db-migrate db-shell db-backup db-restore status health \
	check format test test-postgres test-frontend test-e2e ci ci-backend ci-frontend ci-repo diff-cover \
	api-types api-types-check workflows clean clean-all
