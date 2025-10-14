# ═══════════════════════════════════════════════════════════════
# Gene Curator - Comprehensive Development Makefile
# ═══════════════════════════════════════════════════════════════
#
# This Makefile provides 50+ commands for development, testing,
# and production workflows. Supports hybrid mode (DB in Docker,
# API/Frontend local) for fast iteration.
#
# Quick Start:
#   make help          # Show all commands
#   make hybrid-up     # Start hybrid dev mode (RECOMMENDED)
#   make status        # Show system status
#
# ═══════════════════════════════════════════════════════════════

.PHONY: help
.DEFAULT_GOAL := help

# ───────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────

# Load environment variables from .env.dev
include .env.dev
export

# Docker Compose files (using integrated 'docker compose' command)
DOCKER_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev
DOCKER_COMPOSE_PROD := docker compose -f docker-compose.yml

# Container names (from .env.dev)
POSTGRES_CONTAINER := gene_curator_postgres
BACKEND_CONTAINER := gene_curator_backend
FRONTEND_CONTAINER := gene_curator_frontend

# Directories
BACKUP_DIR := backups
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ═══════════════════════════════════════════════════════════════
# HELP SYSTEM
# ═══════════════════════════════════════════════════════════════

help: ## Show this help message
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Gene Curator - Development Commands                    ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 HYBRID DEVELOPMENT (Recommended for fast iteration):"
	@echo "  make hybrid-up       - Start DB in Docker + instructions for local API/Frontend"
	@echo "  make hybrid-down     - Stop all hybrid mode services"
	@echo "  make backend         - Start backend API locally (port $(BACKEND_PORT))"
	@echo "  make frontend        - Start frontend dev server locally (port $(VITE_DEV_PORT))"
	@echo "  make services-up     - Start only database services in Docker"
	@echo "  make services-down   - Stop only database services"
	@echo ""
	@echo "🐳 FULL DOCKER DEVELOPMENT:"
	@echo "  make dev             - Start all services in Docker (ports: API=$(BACKEND_PORT), UI=$(FRONTEND_PORT), DB=$(POSTGRES_PORT))"
	@echo "  make dev-build       - Build and start development environment"
	@echo "  make dev-down        - Stop all Docker services"
	@echo "  make dev-restart     - Restart all Docker services"
	@echo "  make dev-logs        - Show Docker logs (all services)"
	@echo "  make dev-logs-api    - Show backend API logs only"
	@echo "  make dev-logs-ui     - Show frontend logs only"
	@echo "  make dev-logs-db     - Show database logs only"
	@echo ""
	@echo "🗄️  DATABASE MANAGEMENT:"
	@echo "  make db-init         - Initialize database with seed data"
	@echo "  make db-reset        - Complete database reset (structure + data)"
	@echo "  make db-clean        - Remove all data (keep structure)"
	@echo "  make db-shell        - Open PostgreSQL shell"
	@echo "  make db-backup-full  - Create full database backup"
	@echo "  make db-backup-schema - Create schema-only backup"
	@echo "  make db-restore      - Restore database from backup"
	@echo "  make db-migrate      - Run database migrations"
	@echo ""
	@echo "📊 MONITORING & STATUS:"
	@echo "  make status          - Show comprehensive system status"
	@echo "  make health          - Health checks for all services"
	@echo "  make version         - Show component versions"
	@echo "  make ps              - Show running containers"
	@echo "  make top             - Show container resource usage"
	@echo ""
	@echo "🧪 TESTING:"
	@echo "  make test            - Run all backend tests"
	@echo "  make test-unit       - Run unit tests only (fast)"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make test-failed     - Re-run failed tests"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo "  make test-frontend   - Run frontend tests"
	@echo ""
	@echo "🔧 CODE QUALITY:"
	@echo "  make lint            - Lint backend code (ruff, mypy, bandit)"
	@echo "  make lint-check      - Check backend code quality (no auto-fix, for CI/CD)"
	@echo "  make lint-frontend   - Lint frontend code (ESLint + auto-fix)"
	@echo "  make lint-frontend-check - Check frontend code quality (no auto-fix, for CI/CD)"
	@echo "  make lint-all        - Lint all code (backend + frontend)"
	@echo "  make lint-all-check  - Check all code quality without auto-fix (for CI/CD)"
	@echo "  make format          - Format backend code (ruff)"
	@echo "  make format-frontend - Format frontend code (Prettier)"
	@echo "  make format-all      - Format all code (backend + frontend)"
	@echo "  make check           - Run all backend quality checks (lint + test)"
	@echo "  make check-all       - Run all quality checks (backend + frontend)"
	@echo ""
	@echo "🛠️  UTILITIES:"
	@echo "  make backend-shell   - Open bash shell in backend container"
	@echo "  make frontend-shell  - Open bash shell in frontend container"
	@echo "  make clean           - Clean up Docker resources"
	@echo "  make clean-backend   - Clean Python cache files (__pycache__, .pyc, etc.)"
	@echo "  make clean-all       - Stop everything and clean all data"
	@echo "  make install-backend - Install backend dependencies"
	@echo "  make install-frontend - Install frontend dependencies"
	@echo "  make install-all     - Install all dependencies"
	@echo ""
	@echo "📝 DOCUMENTATION:"
	@echo "  make docs            - Show API documentation URL"
	@echo "  make api-docs        - Open API docs in browser"
	@echo ""
	@echo "ℹ️  For detailed help on any command, check the Makefile source."
	@echo ""

# ═══════════════════════════════════════════════════════════════
# HYBRID DEVELOPMENT MODE (DB in Docker, API/Frontend local)
# ═══════════════════════════════════════════════════════════════
# This is the RECOMMENDED development mode for fastest iteration.
# Changes to code are reflected immediately without Docker rebuild.
# ═══════════════════════════════════════════════════════════════

hybrid-up: services-up ## Start hybrid dev mode (DB in Docker, API/Frontend local)
	@echo ""
	@echo "$(GREEN)✅ Database services running in Docker$(NC)"
	@echo ""
	@echo "$(BLUE)📝 Now start API and Frontend in separate terminals:$(NC)"
	@echo ""
	@echo "$(YELLOW)  Terminal 1 (Backend API):$(NC)"
	@echo "    cd $(BACKEND_DIR) && source .venv/bin/activate"
	@echo "    uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)"
	@echo ""
	@echo "$(YELLOW)  OR use make:$(NC)"
	@echo "    make backend"
	@echo ""
	@echo "$(YELLOW)  Terminal 2 (Frontend):$(NC)"
	@echo "    cd $(FRONTEND_DIR) && npm run dev -- --port $(VITE_DEV_PORT)"
	@echo ""
	@echo "$(YELLOW)  OR use make:$(NC)"
	@echo "    make frontend"
	@echo ""
	@echo "$(BLUE)🌐 Access points:$(NC)"
	@echo "   Frontend (Vite): $(GREEN)http://localhost:$(VITE_DEV_PORT)$(NC)"
	@echo "   Backend API:     $(GREEN)http://localhost:$(BACKEND_PORT)/docs$(NC)"
	@echo "   Database:        $(GREEN)localhost:$(POSTGRES_PORT)$(NC)"
	@echo ""
	@echo "$(BLUE)💡 Tip: Use 'make status' to check service health$(NC)"
	@echo ""

hybrid-down: ## Stop hybrid development environment
	@echo "$(YELLOW)Stopping hybrid development environment...$(NC)"
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -f "vite.*$(VITE_DEV_PORT)" 2>/dev/null || true
	@$(MAKE) services-down
	@echo "$(GREEN)✅ Hybrid environment stopped$(NC)"

services-up: ## Start only database services in Docker
	@echo "$(BLUE)Starting database services...$(NC)"
	@$(DOCKER_COMPOSE) up -d postgres redis
	@echo "$(GREEN)✅ Database services started$(NC)"
	@echo "$(BLUE)Waiting for PostgreSQL to be ready...$(NC)"
	@sleep 5
	@docker exec $(POSTGRES_CONTAINER) pg_isready -U $(POSTGRES_USER) > /dev/null 2>&1 && \
		echo "$(GREEN)✅ PostgreSQL is ready$(NC)" || \
		echo "$(YELLOW)⚠️  PostgreSQL still starting...$(NC)"

services-down: ## Stop only database services
	@echo "$(YELLOW)Stopping database services...$(NC)"
	@$(DOCKER_COMPOSE) stop postgres redis
	@echo "$(GREEN)✅ Database services stopped$(NC)"

backend: ## Start backend API locally (hybrid mode)
	@echo "$(BLUE)Starting backend API on port $(BACKEND_PORT)...$(NC)"
	@echo "$(YELLOW)Database URL: $(DATABASE_URL)$(NC)"
	@cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

frontend: ## Start frontend dev server locally (hybrid mode)
	@echo "$(BLUE)Starting frontend dev server on port $(VITE_DEV_PORT)...$(NC)"
	@echo "$(YELLOW)API URL: $(VITE_API_BASE_URL)$(NC)"
	@cd $(FRONTEND_DIR) && npm run dev -- --host 0.0.0.0 --port $(VITE_DEV_PORT)

# ═══════════════════════════════════════════════════════════════
# FULL DOCKER DEVELOPMENT
# ═══════════════════════════════════════════════════════════════

dev: ## Start all services in Docker
	@echo "$(BLUE)Starting Gene Curator development environment...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "$(GREEN)✅ Development environment started!$(NC)"
	@echo ""
	@echo "$(BLUE)🌐 Access points:$(NC)"
	@echo "   Frontend:  $(GREEN)http://localhost:$(FRONTEND_PORT)$(NC)"
	@echo "   Backend:   $(GREEN)http://localhost:$(BACKEND_PORT)/docs$(NC)"
	@echo "   Database:  $(GREEN)localhost:$(POSTGRES_PORT)$(NC)"
	@echo ""
	@echo "$(BLUE)💡 Useful commands:$(NC)"
	@echo "   make status      - Show system status"
	@echo "   make dev-logs    - View logs"
	@echo "   make dev-down    - Stop services"
	@echo ""

dev-build: ## Build and start development environment
	@echo "$(BLUE)Building and starting development environment...$(NC)"
	@$(DOCKER_COMPOSE) up -d --build
	@echo "$(GREEN)✅ Development environment built and started!$(NC)"

dev-down: ## Stop all Docker services
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Development environment stopped$(NC)"

dev-restart: ## Restart all Docker services
	@$(MAKE) dev-down
	@$(MAKE) dev

dev-logs: ## Show Docker logs (all services)
	@$(DOCKER_COMPOSE) logs -f

dev-logs-api: ## Show backend API logs only
	@$(DOCKER_COMPOSE) logs -f backend

dev-logs-ui: ## Show frontend logs only
	@$(DOCKER_COMPOSE) logs -f frontend

dev-logs-db: ## Show database logs only
	@$(DOCKER_COMPOSE) logs -f postgres

# ═══════════════════════════════════════════════════════════════
# DATABASE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

db-init: ## Initialize database with seed data
	@echo "$(BLUE)Initializing database...$(NC)"
	@docker exec $(POSTGRES_CONTAINER) /bin/bash -c "cd /docker-entrypoint-initdb.d && ./init.sh"
	@echo "$(GREEN)✅ Database initialized$(NC)"

db-reset: ## Complete database reset (structure + data)
	@echo "$(RED)⚠️  WARNING: This will delete ALL data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Resetting database...$(NC)"; \
		$(DOCKER_COMPOSE) down -v; \
		$(DOCKER_COMPOSE) up -d postgres; \
		sleep 10; \
		$(MAKE) db-init; \
		echo "$(GREEN)✅ Database reset complete$(NC)"; \
	else \
		echo "$(YELLOW)Database reset cancelled$(NC)"; \
	fi

db-clean: ## Remove all data (keep structure)
	@echo "$(YELLOW)Cleaning database data...$(NC)"
	@docker exec $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "\
		TRUNCATE TABLE users, genes, precurations, curations, reviews CASCADE; \
	"
	@echo "$(GREEN)✅ Database data cleaned$(NC)"

db-shell: ## Open PostgreSQL shell
	@echo "$(BLUE)Opening PostgreSQL shell...$(NC)"
	@docker exec -it $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-backup-full: ## Create full database backup
	@echo "$(BLUE)Creating full database backup...$(NC)"
	@mkdir -p $(BACKUP_DIR)
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker exec $(POSTGRES_CONTAINER) pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) -F c > $(BACKUP_DIR)/backup_$$timestamp.dump; \
	echo "$(GREEN)✅ Backup saved to $(BACKUP_DIR)/backup_$$timestamp.dump$(NC)"

db-backup-schema: ## Create schema-only backup
	@echo "$(BLUE)Creating schema-only backup...$(NC)"
	@mkdir -p $(BACKUP_DIR)
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker exec $(POSTGRES_CONTAINER) pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) --schema-only > $(BACKUP_DIR)/schema_$$timestamp.sql; \
	echo "$(GREEN)✅ Schema backup saved to $(BACKUP_DIR)/schema_$$timestamp.sql$(NC)"

db-restore: ## Restore database from backup
	@echo "$(RED)⚠️  WARNING: This will overwrite the current database!$(NC)"
	@read -p "Backup file path: " backup_file; \
	if [ -f "$$backup_file" ]; then \
		echo "$(YELLOW)Restoring from $$backup_file...$(NC)"; \
		cat $$backup_file | docker exec -i $(POSTGRES_CONTAINER) pg_restore -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c; \
		echo "$(GREEN)✅ Database restored$(NC)"; \
	else \
		echo "$(RED)❌ File not found: $$backup_file$(NC)"; \
	fi

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@cd $(BACKEND_DIR) && uv run alembic upgrade head
	@echo "$(GREEN)✅ Migrations complete$(NC)"

# ═══════════════════════════════════════════════════════════════
# MONITORING & STATUS
# ═══════════════════════════════════════════════════════════════

status: ## Show comprehensive system status
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Gene Curator - System Status                           ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "$(BLUE)📊 DOCKER SERVICES:$(NC)"
	@docker ps --filter "name=gene_curator" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "$(YELLOW)No Docker services running$(NC)"
	@echo ""
	@echo "$(BLUE)🗄️  DATABASE STATISTICS:$(NC)"
	@docker exec $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "\
		SELECT \
			(SELECT COUNT(*) FROM scopes) as scopes, \
			(SELECT COUNT(*) FROM genes) as genes, \
			(SELECT COUNT(*) FROM curations) as curations, \
			(SELECT COUNT(*) FROM precurations) as precurations, \
			(SELECT COUNT(*) FROM curation_schemas) as schemas, \
			(SELECT COUNT(*) FROM users) as users; \
	" 2>/dev/null || echo "$(RED)❌ Database not accessible$(NC)"
	@echo ""
	@echo "$(BLUE)💾 DISK USAGE:$(NC)"
	@docker exec $(POSTGRES_CONTAINER) du -sh /var/lib/postgresql/data 2>/dev/null || echo "$(YELLOW)N/A$(NC)"
	@echo ""
	@echo "$(BLUE)⏱️  CONTAINER UPTIME:$(NC)"
	@docker ps --filter "name=$(POSTGRES_CONTAINER)" --format "PostgreSQL: {{.Status}}" 2>/dev/null || echo "$(RED)❌ PostgreSQL not running$(NC)"
	@docker ps --filter "name=$(BACKEND_CONTAINER)" --format "Backend:    {{.Status}}" 2>/dev/null || echo "$(YELLOW)Backend not running in Docker (may be running locally)$(NC)"
	@docker ps --filter "name=$(FRONTEND_CONTAINER)" --format "Frontend:   {{.Status}}" 2>/dev/null || echo "$(YELLOW)Frontend not running in Docker (may be running locally)$(NC)"
	@echo ""

health: ## Health checks for all services
	@echo "$(BLUE)🏥 Health Checks:$(NC)"
	@echo ""
	@echo "$(YELLOW)Backend API:$(NC)"
	@curl -s http://localhost:$(BACKEND_PORT)/health 2>/dev/null | jq '.' || echo "$(RED)❌ Not responding (URL: http://localhost:$(BACKEND_PORT)/health)$(NC)"
	@echo ""
	@echo "$(YELLOW)Frontend:$(NC)"
	@curl -s http://localhost:$(FRONTEND_PORT) > /dev/null 2>&1 && echo "$(GREEN)✅ Running$(NC)" || \
		curl -s http://localhost:$(VITE_DEV_PORT) > /dev/null 2>&1 && echo "$(GREEN)✅ Running (Vite dev)$(NC)" || \
		echo "$(RED)❌ Not running$(NC)"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@docker exec $(POSTGRES_CONTAINER) pg_isready -U $(POSTGRES_USER) > /dev/null 2>&1 && echo "$(GREEN)✅ Ready$(NC)" || echo "$(RED)❌ Not ready$(NC)"
	@echo ""

version: ## Show component versions
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Gene Curator - Component Versions                      ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "$(BLUE)🐍 Python:$(NC)"
	@python3 --version 2>/dev/null || echo "$(YELLOW)Not installed$(NC)"
	@echo ""
	@echo "$(BLUE)📦 UV:$(NC)"
	@uv --version 2>/dev/null || echo "$(YELLOW)Not installed$(NC)"
	@echo ""
	@echo "$(BLUE)🟢 Node.js:$(NC)"
	@node --version 2>/dev/null || echo "$(YELLOW)Not installed$(NC)"
	@echo ""
	@echo "$(BLUE)📦 npm:$(NC)"
	@npm --version 2>/dev/null || echo "$(YELLOW)Not installed$(NC)"
	@echo ""
	@echo "$(BLUE)🐳 Docker:$(NC)"
	@docker --version 2>/dev/null || echo "$(YELLOW)Not installed$(NC)"
	@echo ""
	@echo "$(BLUE)🐳 Docker Compose:$(NC)"
	@docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo "$(YELLOW)Not installed$(NC)"
	@echo ""
	@echo "$(BLUE)🐘 PostgreSQL:$(NC)"
	@docker exec $(POSTGRES_CONTAINER) psql --version 2>/dev/null || echo "$(YELLOW)Not running$(NC)"
	@echo ""

ps: ## Show running containers
	@docker ps --filter "name=gene_curator"

top: ## Show container resource usage
	@echo "$(BLUE)📊 Container Resource Usage:$(NC)"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
		$(POSTGRES_CONTAINER) $(BACKEND_CONTAINER) $(FRONTEND_CONTAINER) 2>/dev/null || \
		echo "$(YELLOW)No containers running$(NC)"

# ═══════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════

test: ## Run all backend tests
	@echo "$(BLUE)Running all tests...$(NC)"
	@cd $(BACKEND_DIR) && uv run pytest

test-unit: ## Run unit tests only (fast)
	@echo "$(BLUE)Running unit tests...$(NC)"
	@cd $(BACKEND_DIR) && uv run pytest tests/unit -v

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	@cd $(BACKEND_DIR) && uv run pytest tests/integration -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	@cd $(BACKEND_DIR) && uv run pytest --cov=app --cov-report=html --cov-report=term
	@echo ""
	@echo "$(GREEN)📊 Coverage report: $(BACKEND_DIR)/htmlcov/index.html$(NC)"

test-failed: ## Re-run failed tests
	@echo "$(BLUE)Re-running failed tests...$(NC)"
	@cd $(BACKEND_DIR) && uv run pytest --lf -v

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	@cd $(BACKEND_DIR) && uv run pytest-watch

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd $(FRONTEND_DIR) && npm run test

# ═══════════════════════════════════════════════════════════════
# CODE QUALITY
# ═══════════════════════════════════════════════════════════════

lint: ## Lint backend code (ruff, mypy, bandit)
	@echo "$(BLUE)Linting backend code...$(NC)"
	@cd $(BACKEND_DIR) && uv run python scripts/lint.py

lint-check: ## Lint backend without auto-fix (for CI/CD)
	@echo "$(BLUE)Checking backend code quality (no auto-fix)...$(NC)"
	@cd $(BACKEND_DIR) && uv run ruff check app/ && \
		uv run ruff format --check app/ && \
		uv run mypy app/ && \
		uv run bandit -r app/ -f json
	@echo "$(GREEN)✅ All checks passed!$(NC)"

lint-frontend: ## Lint frontend code (ESLint)
	@echo "$(BLUE)Linting frontend code...$(NC)"
	@cd $(FRONTEND_DIR) && npm run lint

lint-frontend-check: ## Lint frontend without auto-fix (for CI/CD)
	@echo "$(BLUE)Checking frontend code quality (no auto-fix)...$(NC)"
	@cd $(FRONTEND_DIR) && npm run lint:check && npm run format:check
	@echo "$(GREEN)✅ All checks passed!$(NC)"

lint-all: lint lint-frontend ## Lint all code (backend + frontend)

lint-all-check: lint-check lint-frontend-check ## Check all code quality without auto-fix (for CI/CD)

format: ## Format backend code
	@echo "$(BLUE)Formatting backend code...$(NC)"
	@cd $(BACKEND_DIR) && uv run python scripts/format.py

format-frontend: ## Format frontend code (Prettier)
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	@cd $(FRONTEND_DIR) && npm run format

format-all: format format-frontend ## Format all code (backend + frontend)

check: lint test ## Run all quality checks (lint + test)

check-all: lint-all test test-frontend ## Run all quality checks (backend + frontend)

# ═══════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════

backend-shell: ## Open bash shell in backend container
	@docker exec -it $(BACKEND_CONTAINER) /bin/bash

frontend-shell: ## Open bash shell in frontend container
	@docker exec -it $(FRONTEND_CONTAINER) /bin/bash

clean: ## Clean up Docker resources
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	@$(DOCKER_COMPOSE) down --remove-orphans
	@docker system prune -f
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-backend: ## Clean Python cache files (__pycache__, .pyc, etc.)
	@echo "$(BLUE)Cleaning backend cache files...$(NC)"
	@echo "  Removing Python cache directories..."
	@find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type f -name "*.pyc" -delete 2>/dev/null || true
	@find $(BACKEND_DIR) -type f -name "*.pyo" -delete 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "  Removing .cache directory..."
	@rm -rf $(BACKEND_DIR)/.cache 2>/dev/null || true
	@echo "  Removing pytest cache..."
	@rm -rf $(BACKEND_DIR)/.pytest_cache 2>/dev/null || true
	@echo "  Removing ruff cache..."
	@rm -rf $(BACKEND_DIR)/.ruff_cache 2>/dev/null || true
	@echo "  Removing mypy cache..."
	@rm -rf $(BACKEND_DIR)/.mypy_cache 2>/dev/null || true
	@echo "$(GREEN)✅ Backend cache cleaned!$(NC)"

clean-all: ## Stop everything and clean all data
	@echo "$(RED)⚠️  WARNING: This will delete ALL Docker volumes and data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Cleaning everything...$(NC)"; \
		$(DOCKER_COMPOSE) down -v --remove-orphans; \
		docker system prune -af --volumes; \
		echo "$(GREEN)✅ All Docker resources cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

install-backend: ## Install backend dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@cd $(BACKEND_DIR) && uv sync
	@echo "$(GREEN)✅ Backend dependencies installed$(NC)"

install-frontend: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@cd $(FRONTEND_DIR) && npm install
	@echo "$(GREEN)✅ Frontend dependencies installed$(NC)"

install-all: install-backend install-frontend ## Install all dependencies

# ═══════════════════════════════════════════════════════════════
# DOCUMENTATION
# ═══════════════════════════════════════════════════════════════

docs: ## Show API documentation URL
	@echo "$(BLUE)📚 API Documentation:$(NC)"
	@echo "   Swagger UI: $(GREEN)http://localhost:$(BACKEND_PORT)/docs$(NC)"
	@echo "   ReDoc:      $(GREEN)http://localhost:$(BACKEND_PORT)/redoc$(NC)"

api-docs: ## Open API docs in browser
	@echo "$(BLUE)Opening API documentation...$(NC)"
	@python3 -m webbrowser http://localhost:$(BACKEND_PORT)/docs 2>/dev/null || \
		xdg-open http://localhost:$(BACKEND_PORT)/docs 2>/dev/null || \
		open http://localhost:$(BACKEND_PORT)/docs 2>/dev/null || \
		echo "$(YELLOW)Please open http://localhost:$(BACKEND_PORT)/docs in your browser$(NC)"
