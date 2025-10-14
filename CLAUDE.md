# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Gene Curator - Schema-Agnostic Genetic Curation Platform

**Core Concept**: Support any curation methodology (ClinGen, GenCC, institutional) through configurable schemas, scope-based organization, and multi-stage workflows.

**Tech Stack**: PostgreSQL 15+ | FastAPI + SQLAlchemy + uv | Vue 3 + Vite + Pinia + Vuetify 3

---

## Essential Commands

### Development Workflow (Hybrid Mode - RECOMMENDED)
```bash
make hybrid-up     # Start DB in Docker (PostgreSQL:5454, Redis:6399)
make backend       # Terminal 1: Start backend API (localhost:8051)
make frontend      # Terminal 2: Start frontend (localhost:5193)
make status        # Check system status
make help          # Show all 50+ commands
```

**Why Hybrid?** Fastest iteration - code changes reflected instantly, no Docker rebuild needed.

### Full Docker Mode (All Services in Containers)
```bash
make dev           # Start all services (API:8051, UI:3051, DB:5454)
make dev-build     # Rebuild and start
make dev-down      # Stop all services
make dev-logs      # View logs
```

### Database Operations
```bash
make db-init       # Initialize with seed data
make db-reset      # Complete reset (destructive)
make db-shell      # PostgreSQL shell
make db-backup-full # Backup database
```

### Testing & Quality
```bash
make test          # Run all backend tests
make test-unit     # Unit tests only (fast)
make lint          # Lint backend (ruff, mypy, bandit)
make lint-frontend # Lint frontend (ESLint + Prettier)
make format-all    # Auto-format everything
make check-all     # All quality checks (backend + frontend)
```

### Backend Commands (Direct - in backend/)
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8051
uv run pytest                    # Run tests
uv run pytest --cov=app          # With coverage
uv run python scripts/lint.py    # All linting
uv run ruff check                # Ruff only
uv run mypy app                  # Type checking only
```

### Frontend Commands (Direct - in frontend/)
```bash
npm run dev -- --port 5193  # Vite dev server
npm run lint                # ESLint with auto-fix
npm run format              # Prettier formatting
npm run test                # Run tests
```

---

## Critical Architecture Patterns

### 1. Non-Standard Ports (Avoid Conflicts)
Gene Curator uses **non-standard ports** to allow running alongside other projects:
- **Backend API**: 8051 (not 8001/8000)
- **Frontend Docker**: 3051 (not 3001)
- **Frontend Vite**: 5193 (not 5173)
- **PostgreSQL**: 5454 (not 5433/5432)
- **Redis**: 6399 (not 6379)

**Source of Truth**: `.env.dev` - all ports defined there.

### 2. Frontend Environment Setup (CRITICAL)
**⚠️ Frontend REQUIRES `.env.local` file to work correctly**

Create `frontend/.env.local`:
```bash
VITE_API_BASE_URL=http://localhost:8051
VITE_APP_TITLE=Gene Curator (Dev)
VITE_ENVIRONMENT=development
VITE_ENABLE_DEV_LOGIN=true
```

Without this file, login will fail silently because requests go to wrong port (8001 instead of 8051).

### 3. Schema-Agnostic Design
Everything driven by configurable schema definitions stored in `curation_schemas` table:
- **Field Definitions**: What data to collect (12+ field types)
- **Validation Rules**: Dynamic validation at runtime
- **Scoring Algorithms**: Pluggable engines (ClinGen, GenCC, Qualitative)
- **UI Configuration**: Forms generated from schema

**Schema Location**: Database (`curation_schemas` table), NOT config files.

### 4. Scope-Based Organization
Clinical specialties as first-class entities:
- Scopes: kidney-genetics, cardio-genetics, neuro-genetics, etc.
- Gene assignments: Many-to-many with curator assignment
- Access control: Scope-based permissions + RBAC (5 roles)

### 5. Multi-Stage Workflow
```
Entry → Precuration → Curation → Review (4-eyes) → Active
  ↓         ↓            ↓            ↓              ↓
Draft    Multiple     Multiple    Mandatory      One per
State    per Gene     per Gene    Peer Review    Gene-Scope
```

**4-Eyes Principle**: Independent reviewer required before activation.

### 6. Store Pattern (Pinia - Frontend)
All stores follow consistent API:
```javascript
fetchItems()              // Fetch all
fetchItemById(id)         // Fetch single
createItem(data)          // Create
updateItem(id, data)      // Update
deleteItem(id)            // Delete
```

**Stores**: auth, scopes, schemas, validation, workflow, assignments, genes, users.

---

## Critical Bugs to Avoid (ALWAYS FOLLOW)

### 1. SQLAlchemy Boolean Filters
**⚠️ NEVER use Python identity operators with SQLAlchemy columns**

```python
# ✅ CORRECT (Pythonic)
query.filter(Model.is_active)
query.filter(~Model.is_active)  # negation
query.filter(Model.is_active == True)

# ❌ WRONG (Python identity check)
query.filter(Model.is_active is True)   # WILL FAIL
query.filter(Model.is_active is False)  # WILL FAIL
```

**Why**: SQLAlchemy columns overload `__bool__()`. Python `is` checks object identity, not value.

### 2. Never Use Sed for Code Refactoring
**⚠️ NEVER use `sed` command for code refactoring**

Why sed fails:
- Line-based, doesn't understand syntax
- Can't handle multi-line expressions
- Places comments in wrong locations
- Breaks indentation and structure

**✅ Use Instead**: PyCharm/VSCode refactoring, Edit tool, or Task tool.

### 3. Always Run Linting Before Commits
**⚠️ Linting MUST pass before committing (zero errors, zero warnings)**

```bash
make lint              # Backend
make lint-frontend     # Frontend
make format-all        # Auto-format all
```

---

## Unified Logging System (ALWAYS USE)

### Backend Logging
```python
from app.core.logging import get_logger

logger = get_logger(__name__)  # NOT logging.getLogger()

# Auto-detects async/sync context
logger.info("Message", key="value", another_key=123)
logger.error("Error occurred", error=exception, context="value")
```

**NEVER Use**:
- ❌ `logging.getLogger()` - Always use `get_logger()`
- ❌ `print()` - Always use logger
- ❌ Manual context building - Context automatic via middleware
- ❌ `f"Error: {e}"` - Use `error=e` parameter

**Performance Monitoring**:
```python
from app.core.logging import timed_operation, api_endpoint

@api_endpoint()  # Automatic endpoint timing
async def my_endpoint(): pass

@timed_operation("complex_calc", warning_threshold_ms=200)
async def calculate(): pass
```

**Features**:
- Request correlation (all logs include same `request_id`)
- Automatic sanitization (tokens, passwords, emails, variants)
- Database persistence (`system_logs` table, 90-day retention)
- Performance tracking (duration_ms in logs)

### Frontend Logging
```javascript
// In components (Options API)
this.$logger.info('Message', { key: 'value' })
this.$logger.error('Error occurred', { error: error.message })

// In components (Composition API)
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()
logger.info('Message', { key: 'value' })

// In stores and utilities
import { logService } from '@/services/logService'
logService.info('Message', { key: 'value' })
```

**NEVER Use**: ❌ `console.log()`, `console.error()`, `alert()` - Always use logger

**Features**:
- Request correlation (matches backend via `X-Request-ID` header)
- Automatic sanitization (tokens, emails, genetic variants)
- Browser compatibility (UUID polyfill for Safari < 15.4)
- Memory management (auto-trim to max entries)

**Log Viewer**: Press `Ctrl+L` (Windows/Linux) or `Cmd+L` (Mac) to toggle in-browser log viewer.

---

## Configuration Management (ALWAYS USE)

### Three-Tier Architecture
1. **Constants** (`app/core/constants.py`): Immutable application-wide values
2. **Environment Settings** (`app/core/config.py`): Environment-specific from `.env`
3. **API Configuration** (`backend/config/api.yaml`): Deployment-specific

### Using Constants
```python
from app.core.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
)

@router.get("/items")
def list_items(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
):
    return JSONResponse(status_code=HTTP_200_OK, content=data)
```

### Using API Configuration
```python
from app.core.api_config import (
    get_cors_config,
    get_pagination_config,
    get_logging_config,
)

cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.allow_origins,
)
```

### Environment Variable Overrides
```bash
# Override YAML values with env vars
export GENE_CURATOR_API__CORS__ALLOW_ORIGINS='["https://prod.example.com"]'
export GENE_CURATOR_API__PAGINATION__DEFAULT_PAGE_SIZE=100
export GENE_CURATOR_API__FEATURES__ENABLE_RATE_LIMITING=true
```

**When to Use Each**:
- **Constants**: Magic numbers, HTTP codes, never-changing values
- **Environment Settings**: Secrets, database URLs, core config
- **API Configuration**: CORS origins, rate limits, feature flags

**DON'T**: ❌ Hardcode magic numbers, ❌ Store secrets in YAML, ❌ Put workflow config in YAML (use schema repository)

---

## Key Directories

```
/backend/app
  /api/v1/endpoints/      # API route handlers
    auth.py              # Authentication & JWT
    scopes.py            # Scope management
    schemas.py           # Schema repository
    schema_validation.py # Dynamic validation
    gene_assignments.py  # Gene assignment system
    workflow.py          # Multi-stage workflow
  /models/models.py      # SQLAlchemy models
  /schemas/              # Pydantic request/response
  /core/
    config.py            # Application configuration
    database.py          # Database connection
    security.py          # JWT & auth utilities
    schema_validator.py  # Dynamic validation engine
    constants.py         # Application constants
    api_config.py        # API configuration loader
    logging/             # Unified logging system
  /crud/                 # Database CRUD operations
  /scoring/              # Pluggable scoring engines
    registry.py          # Engine registry
    clingen.py           # ClinGen SOP v11
    gencc.py             # GenCC classification
    qualitative.py       # Qualitative assessment

/frontend/src
  /api/                  # API client & axios
  /stores/               # Pinia state management
  /views/                # Page-level components
  /router/               # Vue Router configuration
  /services/
    logService.js        # Logging service
    scopeService.js      # Scope utilities
  /utils/
    logSanitizer.js      # Privacy protection
    uuidPolyfill.js      # Browser compatibility

/database/sql            # PostgreSQL schema
  001_schema_foundation.sql # Core tables & enums
  002_schema_triggers.sql   # Triggers & constraints
  003_schema_views.sql      # Views & queries
  004_seed_data.sql         # Sample data
```

---

## Access Points

### Development Environment
- **Frontend (Vite)**: http://localhost:5193
- **Frontend (Docker)**: http://localhost:3051
- **Backend API**: http://localhost:8051
- **API Docs (Swagger)**: http://localhost:8051/docs
- **API Docs (ReDoc)**: http://localhost:8051/redoc
- **Database**: localhost:5454
- **Default Credentials**: admin@gene-curator.dev / admin123

---

## Implementation Status

**✅ Complete**:
- Core infrastructure (PostgreSQL, FastAPI, Vue 3)
- Schema-agnostic foundation (schema repository, dynamic validation)
- Multi-stage workflow engine (5 stages, 4-eyes principle)
- API implementation (10 endpoint modules, 30+ routes)
- Frontend integration (9 Pinia stores, API integration)
- Authentication & RBAC (JWT, 5 roles)
- Pluggable scoring engines (ClinGen, GenCC, Qualitative)
- Unified logging system (backend + frontend)
- Configuration management (three-tier system)
- Code quality (linting, formatting, type checking)
- Testing suite (unit + integration tests)

**🔄 Ongoing**:
- Dynamic UI form generation (backend ready, frontend pending)
- Draft auto-save functionality (backend ready, frontend pending)
- Production deployment documentation

---

## Package Management

- **Backend**: `uv` (modern, fast Python package manager)
- **Frontend**: `npm` (standard Node.js package manager)
- **Backend Dependencies**: Defined in `backend/pyproject.toml`
- **Frontend Dependencies**: Defined in `frontend/package.json`

**Backend Install**: `cd backend && uv sync`
**Frontend Install**: `cd frontend && npm install`

---

## Important Files

- `README.md`: Project overview & quick start
- `PLAN.md`: Complete architecture vision
- `Makefile`: 50+ development commands
- `.env.dev`: Development environment configuration
- `backend/pyproject.toml`: Python dependencies & tool config
- `frontend/package.json`: Frontend dependencies & scripts
- `backend/config/api.yaml`: API configuration
- `database/sql/`: PostgreSQL schema definitions

---

## Development Default Credentials

- **Admin**: admin@gene-curator.dev / admin123
- **Curator**: curator@gene-curator.dev / curator123
- **Viewer**: viewer@gene-curator.dev / viewer123

---

**Gene Curator** - Methodology-agnostic platform for genetic curation across all clinical specialties.
