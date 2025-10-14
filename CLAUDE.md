# Gene Curator - Project Instructions for Claude Code

**Purpose**: Methodology-agnostic platform for genetic curation supporting ClinGen, GenCC, and custom approaches through configurable schemas, scope-based organization, and multi-stage workflows.

**Stack**: PostgreSQL 15+ | FastAPI + SQLAlchemy + uv | Vue 3 + Vite + Pinia + Vuetify 3

---

## Quick Start Commands

```bash
# Hybrid Mode (RECOMMENDED - fastest iteration)
make hybrid-up     # Start DB in Docker (PostgreSQL:5454, Redis:6399)
make backend       # Terminal 1: Backend API (localhost:8051)
make frontend      # Terminal 2: Frontend (localhost:5193)
make status        # Check system status

# Full Docker Mode
make dev           # Start all services (API:8051, UI:3051, DB:5454)
make dev-down      # Stop all services

# Database
make db-init       # Initialize with seed data
make db-reset      # Complete reset
make db-shell      # PostgreSQL shell

# Quality
make test          # All backend tests
make lint          # Backend linting (ruff, mypy, bandit)
make lint-frontend # Frontend linting (ESLint + Prettier)
make format-all    # Auto-format all code
make check-all     # Complete quality check

# Direct Commands (for CI/scripts)
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8051
cd backend && uv run pytest --cov=app
cd frontend && npm run dev -- --port 5193
cd frontend && npm run lint
```

---

## Critical Patterns (MUST FOLLOW)

### 1. Non-Standard Ports
**API**: 8051 | **Frontend Docker**: 3051 | **Frontend Vite**: 5193 | **PostgreSQL**: 5454 | **Redis**: 6399

Source of truth: `.env.dev`

### 2. Frontend Setup (REQUIRED)
Create `frontend/.env.local`:
```bash
VITE_API_BASE_URL=http://localhost:8051
VITE_APP_TITLE=Gene Curator (Dev)
VITE_ENVIRONMENT=development
VITE_ENABLE_DEV_LOGIN=true
```
⚠️ Without this, login fails silently (wrong port).

### 3. Schema-Agnostic Design
Everything configurable via `curation_schemas` table (NOT config files):
- Field definitions (12+ types)
- Validation rules (dynamic)
- Scoring algorithms (ClinGen, GenCC, Qualitative engines)
- UI configuration (auto-generated forms)

### 4. Scope-Based Organization
Clinical specialties: kidney-genetics, cardio-genetics, neuro-genetics, etc.
- Many-to-many gene assignments
- Scope-based permissions + RBAC (5 roles)

### 5. Multi-Stage Workflow (5 Stages)
Entry → Precuration → Curation → Review (4-eyes) → Active
- Multiple precurations/curations per gene-scope
- Mandatory peer review before activation
- One active curation per gene-scope

### 6. Pinia Store Pattern
All stores: `fetchItems()`, `fetchItemById(id)`, `createItem(data)`, `updateItem(id, data)`, `deleteItem(id)`

**Stores**: auth, scopes, schemas, validation, workflow, assignments, genes, users, logStore, notifications, disclaimer.

---

## Critical Bugs to Avoid

### 1. SQLAlchemy Boolean Filters
```python
# ✅ CORRECT
query.filter(Model.is_active)
query.filter(~Model.is_active)
query.filter(Model.is_active == True)

# ❌ WRONG - WILL FAIL
query.filter(Model.is_active is True)
query.filter(Model.is_active is False)
```
**Why**: SQLAlchemy overloads `__bool__()`, `is` checks identity not value.

### 2. No Sed for Refactoring
❌ Never use `sed` for code changes (breaks syntax, indentation, multi-line)
✅ Use Edit tool, Task tool, or IDE refactoring

### 3. Linting Before Commits
⚠️ MUST pass with zero errors/warnings:
```bash
make lint lint-frontend format-all
```

---

## Unified Logging System

### Backend
```python
from app.core.logging import get_logger, api_endpoint, timed_operation

logger = get_logger(__name__)  # NOT logging.getLogger()
logger.info("Message", key="value", another_key=123)
logger.error("Error occurred", error=exception)

@api_endpoint()  # Auto-timing
async def my_endpoint(): pass

@timed_operation("complex_calc", warning_threshold_ms=200)
async def calculate(): pass
```

**Never**: ❌ `logging.getLogger()` ❌ `print()` ❌ `f"Error: {e}"`
**Features**: Request correlation, auto-sanitization, DB persistence (90d), performance tracking

### Frontend
```javascript
// Components (Composition API)
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()
logger.info('Message', { key: 'value' })

// Stores/utilities
import { logService } from '@/services/logService'
logService.info('Message', { key: 'value' })
```

**Never**: ❌ `console.log()` ❌ `console.error()` ❌ `alert()`
**Log Viewer**: `Ctrl+L` / `Cmd+L`

---

## Configuration Management

### Three-Tier System
1. **Constants** (`app/core/constants.py`): Immutable values, HTTP codes
2. **Environment** (`app/core/config.py`): Secrets, DB URLs from `.env`
3. **API Config** (`backend/config/api.yaml`): CORS, rate limits, features

```python
# Constants
from app.core.constants import DEFAULT_PAGE_SIZE, HTTP_200_OK

# API Configuration
from app.core.api_config import get_cors_config, get_pagination_config

# Environment Override
export GENE_CURATOR_API__CORS__ALLOW_ORIGINS='["https://prod.example.com"]'
```

**Never**: ❌ Hardcode magic numbers ❌ Secrets in YAML ❌ Workflow config in YAML (use schema DB)

---

## Key Directories

```
backend/app/
├── api/v1/endpoints/  # API routes (auth, scopes, schemas, workflow, gene_assignments)
├── models/models.py   # SQLAlchemy models
├── schemas/           # Pydantic request/response
├── core/
│   ├── config.py constants.py api_config.py  # Configuration
│   ├── database.py security.py               # DB & auth
│   ├── schema_validator.py                   # Dynamic validation
│   └── logging/                               # Unified logging
├── crud/              # Database operations
└── scoring/           # Engines: clingen, gencc, qualitative, registry

frontend/src/
├── api/               # API client
├── stores/            # Pinia (auth, scopes, schemas, workflow, genes, users, logs)
├── views/             # Pages
├── router/            # Vue Router
├── services/          # logService, scopeService
└── utils/             # logSanitizer, uuidPolyfill

database/sql/          # PostgreSQL schema & seed data
```

---

## Access Points & Credentials

**Development URLs:**
- Frontend (Vite): http://localhost:5193
- Frontend (Docker): http://localhost:3051
- Backend API: http://localhost:8051
- API Docs: http://localhost:8051/docs
- Database: localhost:5454

**Default Credentials:**
- Admin: admin@gene-curator.dev / admin123
- Curator: curator@gene-curator.dev / curator123
- Viewer: viewer@gene-curator.dev / viewer123

---

## Implementation Status

**✅ Implemented:**
- Core infrastructure (PostgreSQL, FastAPI, Vue 3)
- Schema-agnostic foundation (repository, validation)
- Multi-stage workflow (5 stages, 4-eyes principle)
- API (10 modules, 30+ routes)
- Frontend (13 Pinia stores)
- Auth & RBAC (JWT, 5 roles: admin, scope_admin, curator, reviewer, viewer)
- Scoring engines (ClinGen SOP v11, GenCC, Qualitative)
- Unified logging (backend + frontend)
- Configuration management (three-tier)
- Testing suite (unit + integration)

**🔄 Pending:**
- Dynamic UI form generation (frontend)
- Draft auto-save (frontend)

---

## Package Management

**Backend**: `uv` → `cd backend && uv sync`
**Frontend**: `npm` → `cd frontend && npm install`

**Dependencies**: `backend/pyproject.toml`, `frontend/package.json`

---

## Important Files

- `CLAUDE.md` (this file): Development guide for AI
- `README.md`: Project overview
- `CONTRIBUTING.md`: Developer onboarding
- `Makefile`: 50+ commands
- `.env.dev`: Environment config
- `docs/ARCHITECTURE.md`: System architecture
- `docs/archive/INITIAL_PLANNING_VISION.md`: Original vision (archived)
- `backend/config/api.yaml`: API config
- `database/sql/`: Schema definitions

---

**Last Updated**: 2025-10-14
