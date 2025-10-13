# Enhancement: Expanded Makefile with Hybrid Mode and Status Commands

**Priority**: Medium
**Complexity**: Low
**Estimated Effort**: 2-3 hours
**Reference**: `kidney-genetics-db/Makefile` (638 lines, 50+ commands)

## Overview

Expand the Gene Curator Makefile from 30 to 50+ commands, adding hybrid development mode, status command with real-time statistics, comprehensive backup system, and production test mode. Improve developer experience with rich Make-based workflow.

## Current State

- Basic Makefile with ~30 commands
- No hybrid development mode (DB in Docker, API/Frontend local)
- No `make status` command for real-time system statistics
- No comprehensive backup/restore commands
- No production test mode with exposed ports

## Proposed Implementation

### New Command Categories

**1. Hybrid Development Mode** (Recommended for developers)

```makefile
# ════════════════════════════════════════════════════════════════════
# HYBRID DEVELOPMENT MODE (DB in Docker, API/Frontend local)
# ════════════════════════════════════════════════════════════════════

hybrid-up: services-up
	@echo "✅ Database is running in Docker"
	@echo ""
	@echo "📝 Now run in separate terminals:"
	@echo "   Terminal 1: make backend"
	@echo "   Terminal 2: make frontend"
	@echo ""
	@echo "🌐 Access points:"
	@echo "   Frontend: http://localhost:5173 (Vite)"
	@echo "   Backend:  http://localhost:8001/docs"
	@echo "   Database: localhost:5454"

hybrid-down:
	@echo "Stopping hybrid development environment..."
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -f "vite.*5173" 2>/dev/null || true
	@$(MAKE) services-down
	@echo "✅ Hybrid environment stopped"

backend:
	@echo "Starting backend API..."
	@cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev
```

**2. Status Command** (Real-time statistics)

```makefile
status:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Gene Curator - System Status                           ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📊 SERVICES:"
	@docker ps --filter "name=gene_curator" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No Docker services running"
	@echo ""
	@echo "🗄️  DATABASE:"
	@docker exec gene_curator_postgres psql -U gene_curator_user -d gene_curator_dev -c "\
		SELECT \
			(SELECT COUNT(*) FROM scopes) as scopes, \
			(SELECT COUNT(*) FROM genes_new) as genes, \
			(SELECT COUNT(*) FROM curations_new) as curations, \
			(SELECT COUNT(*) FROM curation_schemas) as schemas, \
			(SELECT COUNT(*) FROM users_new) as users \
	" 2>/dev/null || echo "Database not accessible"
	@echo ""
	@echo "💾 DISK USAGE:"
	@docker exec gene_curator_postgres du -sh /var/lib/postgresql/data 2>/dev/null || echo "N/A"
	@echo ""
	@echo "📈 CACHE STATUS:"
	@curl -s http://localhost:8001/api/v1/cache/stats 2>/dev/null | grep -o '"hit_rate":[^,]*' || echo "Cache stats not available"
	@echo ""
	@echo "⏱️  UPTIME:"
	@docker ps --filter "name=gene_curator_postgres" --format "{{.Status}}" 2>/dev/null || echo "N/A"
```

**3. Backup & Restore Commands**

```makefile
# Database backups
db-backup-full:
	@echo "Creating full database backup..."
	@mkdir -p backups
	@docker exec gene_curator_postgres pg_dump -U gene_curator_user -d gene_curator_dev -F c -f /tmp/backup_$$(date +%Y%m%d_%H%M%S).dump
	@docker cp gene_curator_postgres:/tmp/backup_$$(date +%Y%m%d_%H%M%S).dump backups/
	@echo "✅ Backup saved to backups/backup_$$(date +%Y%m%d_%H%M%S).dump"

db-backup-schema:
	@echo "Creating schema-only backup..."
	@mkdir -p backups
	@docker exec gene_curator_postgres pg_dump -U gene_curator_user -d gene_curator_dev --schema-only -f /tmp/schema_$$(date +%Y%m%d_%H%M%S).sql
	@docker cp gene_curator_postgres:/tmp/schema_$$(date +%Y%m%d_%H%M%S).sql backups/
	@echo "✅ Schema backup saved to backups/schema_$$(date +%Y%m%d_%H%M%S).sql"

db-restore:
	@echo "⚠️  WARNING: This will overwrite the current database!"
	@read -p "Backup file path: " backup_file; \
	docker cp $$backup_file gene_curator_postgres:/tmp/restore.dump && \
	docker exec gene_curator_postgres pg_restore -U gene_curator_user -d gene_curator_dev -c /tmp/restore.dump
	@echo "✅ Database restored"

db-backup-auto:
	@echo "Setting up automatic daily backups (cron)..."
	@echo "0 2 * * * cd $(PWD) && make db-backup-full" | crontab -
	@echo "✅ Automatic backups enabled (2 AM daily)"
```

**4. Production Test Mode** (Test production images locally)

```makefile
prod-test-up:
	@echo "Starting production mode with exposed ports (TEST)..."
	@docker-compose -f docker-compose.prod.test.yml up -d
	@echo "⏳ Waiting for services..."
	@sleep 10
	@echo ""
	@echo "🌐 Test Mode Access Points:"
	@echo "   Frontend: http://localhost:8080"
	@echo "   Backend:  http://localhost:8001/docs"
	@echo "   Database: localhost:5454"
	@$(MAKE) prod-test-health

prod-test-health:
	@echo "🏥 Health Check:"
	@curl -s http://localhost:8001/health | jq '.' 2>/dev/null || echo "Backend not responding"

prod-test-down:
	@docker-compose -f docker-compose.prod.test.yml down
	@echo "✅ Test mode stopped"

prod-test-logs:
	@docker-compose -f docker-compose.prod.test.yml logs -f
```

**5. Database View Management**

```makefile
db-refresh-views:
	@echo "Refreshing all database views..."
	@docker exec gene_curator_postgres psql -U gene_curator_user -d gene_curator_dev -c "\
		-- Drop and recreate views in dependency order \
		DROP VIEW IF EXISTS active_curations_view CASCADE; \
		CREATE VIEW active_curations_view AS ...; \
		DROP VIEW IF EXISTS curation_summary_view CASCADE; \
		CREATE VIEW curation_summary_view AS ...; \
	" 2>/dev/null || echo "View refresh failed"
	@echo "✅ Views refreshed"

db-show-view-deps:
	@echo "📊 View Dependency Hierarchy:"
	@docker exec gene_curator_postgres psql -U gene_curator_user -d gene_curator_dev -c "\
		SELECT schemaname, viewname \
		FROM pg_views \
		WHERE schemaname = 'public' \
		ORDER BY viewname; \
	"

db-verify-complete:
	@echo "🔍 Verifying complete schema (tables + views)..."
	@docker exec gene_curator_postgres psql -U gene_curator_user -d gene_curator_dev -c "\
		SELECT \
			(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public') as tables, \
			(SELECT COUNT(*) FROM information_schema.views WHERE table_schema='public') as views; \
	"
```

**6. Testing Commands** (Organized by type)

```makefile
test:
	@echo "Running all tests..."
	@cd backend && uv run pytest

test-unit:
	@echo "Running unit tests..."
	@cd backend && uv run pytest tests/unit -v

test-integration:
	@echo "Running integration tests..."
	@cd backend && uv run pytest tests/integration -v

test-critical:
	@echo "Running critical tests (pre-deployment)..."
	@cd backend && uv run pytest -m critical -v

test-coverage:
	@echo "Running tests with coverage..."
	@cd backend && uv run pytest --cov=app --cov-report=html
	@echo "📊 Coverage report: backend/htmlcov/index.html"

test-failed:
	@echo "Re-running failed tests..."
	@cd backend && uv run pytest --lf -v
```

**7. Version & Health Commands**

```makefile
version:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Gene Curator - Component Versions                      ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🐍 Python:"
	@python --version
	@echo ""
	@echo "📦 UV:"
	@uv --version 2>/dev/null || echo "Not installed"
	@echo ""
	@echo "🟢 Node.js:"
	@node --version
	@echo ""
	@echo "📦 npm:"
	@npm --version
	@echo ""
	@echo "🐳 Docker:"
	@docker --version
	@echo ""
	@echo "🐘 PostgreSQL:"
	@docker exec gene_curator_postgres psql --version 2>/dev/null || echo "Not running"

health:
	@echo "🏥 Health Checks:"
	@echo ""
	@echo "Backend API:"
	@curl -s http://localhost:8001/health | jq '.' || echo "❌ Not responding"
	@echo ""
	@echo "Frontend:"
	@curl -s http://localhost:3001 > /dev/null && echo "✅ Running" || echo "❌ Not running"
	@echo ""
	@echo "Database:"
	@docker exec gene_curator_postgres pg_isready -U gene_curator_user && echo "✅ Ready" || echo "❌ Not ready"
```

### Enhanced Help Command

```makefile
help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Gene Curator - Development Commands                    ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 HYBRID DEVELOPMENT (Recommended):"
	@echo "  make hybrid-up       - Start DB in Docker + run API/Frontend locally"
	@echo "  make hybrid-down     - Stop all hybrid mode services"
	@echo "  make backend         - Start backend API locally"
	@echo "  make frontend        - Start frontend dev server locally"
	@echo ""
	@echo "🐳 FULL DOCKER DEVELOPMENT:"
	@echo "  make dev-up          - Start all services in Docker"
	@echo "  make dev-down        - Stop all Docker services"
	@echo "  make dev-logs        - Show Docker logs"
	@echo ""
	@echo "🗄️  DATABASE MANAGEMENT:"
	@echo "  make db-reset        - Complete database reset (structure + data)"
	@echo "  make db-clean        - Remove all data (keep structure)"
	@echo "  make db-backup-full  - Create full database backup"
	@echo "  make db-restore      - Restore from backup"
	@echo "  make db-refresh-views- Recreate all database views"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make status          - Show system status and statistics"
	@echo "  make health          - Health checks for all services"
	@echo "  make version         - Show component versions"
	@echo ""
	@echo "🧪 TESTING:"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only (fast)"
	@echo "  make test-critical   - Run critical tests (pre-deployment)"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo ""
	@echo "🚢 PRODUCTION:"
	@echo "  make prod-test-up    - Start production test mode"
	@echo "  make prod-test-health- Test mode health check"
	@echo "  make prod-test-down  - Stop test mode"
	@echo ""
	@echo "🔧 UTILITIES:"
	@echo "  make lint            - Lint backend code"
	@echo "  make clean-all       - Stop everything and clean data"
```

## Implementation Steps

1. **Backup existing Makefile**
   ```bash
   cp Makefile Makefile.backup
   ```

2. **Add new command sections** (one at a time)
   - Start with hybrid-up/hybrid-down (highest value)
   - Add status command with database queries
   - Add backup/restore commands
   - Add production test mode
   - Add view management commands

3. **Test each new command**
   ```bash
   make hybrid-up
   make status
   make db-backup-full
   make prod-test-up
   ```

4. **Update CLAUDE.md**
   ```markdown
   ## Development Commands

   **IMPORTANT: Always use make commands for development.**

   ### Quick Start
   ```bash
   make hybrid-up  # Recommended: DB in Docker, API/Frontend local
   make backend    # Terminal 1
   make frontend   # Terminal 2
   make status     # Check system statistics
   ```
   ```

5. **Add docker-compose.prod.test.yml** (if not exists)
   ```yaml
   # Production mode with exposed ports for testing
   services:
     backend:
       ports:
         - "8001:8000"
     frontend:
       ports:
         - "8080:80"
     db:
       ports:
         - "5454:5432"
   ```

## Benefits

- **Developer Experience**: Hybrid mode = faster iteration (no Docker rebuild)
- **Observability**: `make status` shows real-time statistics
- **Safety**: Comprehensive backup/restore commands
- **Testing**: Production test mode validates images before deployment
- **Consistency**: Single source of truth for all development operations

## References

- kidney-genetics-db Makefile: 638 lines, 50+ commands
- Hybrid mode: Most commonly used by developers (fastest iteration)
- Status command: Real-time statistics without SQL knowledge

## Acceptance Criteria

- [ ] Makefile expanded from ~30 to 50+ commands
- [ ] `make hybrid-up/hybrid-down` working (DB in Docker, local API/Frontend)
- [ ] `make status` shows real-time statistics (scopes, genes, curations, cache hit rate)
- [ ] `make db-backup-full` and `make db-restore` working
- [ ] `make prod-test-up` starts production mode with exposed ports
- [ ] `make db-refresh-views` and `make db-verify-complete` working
- [ ] `make test-unit/test-critical/test-coverage` commands added
- [ ] `make version` and `make health` commands working
- [ ] Enhanced `make help` with categorized commands
- [ ] CLAUDE.md updated with Make workflow instructions
- [ ] All new commands tested and documented
