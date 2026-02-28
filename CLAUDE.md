# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Purpose**: Methodology-agnostic platform for genetic curation supporting ClinGen, GenCC, and custom approaches through configurable schemas, scope-based organization, and multi-stage workflows.

**Stack**: PostgreSQL 15+ | FastAPI + SQLAlchemy 2.0 + uv | Vue 3 + Vite + Pinia + Vuetify 3

---

## Commands

```bash
# Development (hybrid mode - RECOMMENDED)
make hybrid-up     # Start DB in Docker (PostgreSQL:5454, Redis:6399)
make backend       # Terminal 1: Backend API (localhost:8051)
make frontend      # Terminal 2: Frontend (localhost:5193)
make status        # Check system status

# Full Docker mode
make dev           # Start all services (API:8051, UI:3051, DB:5454)
make dev-down      # Stop all services

# Database
make db-init       # Initialize with seed data
make db-reset      # Complete reset
make db-migrate    # Run Alembic migrations
make db-shell      # PostgreSQL shell

# Testing
make test                                              # All backend tests
make test-unit                                         # Unit tests only
make test-frontend                                     # Frontend tests (Vitest)
cd backend && uv run pytest tests/unit/test_auth.py -v               # Single test file
cd backend && uv run pytest tests/unit/test_auth.py::test_login -v   # Single test function
cd backend && uv run pytest -k "test_curation" -v                    # Tests matching pattern
cd backend && uv run pytest --lf -v                                  # Re-run failed tests
cd frontend && npm run test:run -- --reporter=verbose                # Frontend tests (single run)

# Code quality (MUST pass before commits)
make lint            # Backend linting (ruff, mypy, bandit) with auto-fix
make lint-frontend   # Frontend linting (ESLint + auto-fix)
make format-all      # Auto-format all code (backend + frontend)
make ci              # Full CI locally (matches GitHub Actions exactly)
make ci-backend      # Backend CI only
make ci-frontend     # Frontend CI only

# Dependencies
cd backend && uv sync          # Install/sync backend deps
cd frontend && npm install     # Install frontend deps
```

---

## Non-Standard Ports

**API**: 8051 | **Frontend Docker**: 3051 | **Frontend Vite**: 5193 | **PostgreSQL**: 5454 | **Redis**: 6399

Source of truth: `.env.dev`. Default credentials: admin@gene-curator.dev / admin123

**Required**: Create `frontend/.env.local` for local dev:
```bash
VITE_API_BASE_URL=http://localhost:8051
VITE_APP_TITLE=Gene Curator (Dev)
VITE_ENVIRONMENT=development
VITE_ENABLE_DEV_LOGIN=true
```
Without this, login fails silently (frontend defaults to wrong port).

---

## Architecture

### Dual-Role Permission System

This is the most non-obvious architectural decision. There are **two independent role systems**:

1. **Application role** (`users.application_role`): Only `admin` or `user`. Controls platform-level access.
2. **Scope role** (`scope_memberships.scope_role`): `admin`, `curator`, `reviewer`, `viewer`. Controls per-scope permissions.

A "curator" is NOT an application-level role—it's a scope membership role. When creating test users, set `role="user"` on `UserNew`, then `role="curator"` in the `ScopeMembership`.

**Auth dependency chain** in `backend/app/core/deps.py`:
```
get_db → get_current_user → get_current_active_user → get_current_admin_user
```
Typed aliases for scope-gated endpoints: `RequireScopeMember`, `RequireScopeReviewer`, `RequireScopeCurator`, `RequireScopeAdmin`.

**Row-Level Security**: `set_rls_context(db, current_user)` sets `app.current_user_id` on the PostgreSQL session. RLS policies in `database/sql/005_rls_setup.sql`. TOCTOU prevention uses `SELECT FOR SHARE` in scope lookups.

### Schema-Agnostic Design

Everything configurable via `curation_schemas` table (NOT config files):
- Field definitions (12+ types), validation rules, scoring algorithms
- UI configuration (auto-generated forms)
- Workflow pairs link precuration + curation schemas together

### Multi-Stage Workflow

Entry → Precuration → Curation → Review (4-eyes) → Active

Backwards transitions allowed (Review→Curation, Curation→Precuration, etc.). One active curation per gene-scope. `WorkflowEngine` in `backend/app/crud/workflow_engine.py` defines the transition DAG.

### Backend Structure

- **Models**: SQLAlchemy 2.0 style (`Mapped[]`, `mapped_column()`). All PKs are UUIDs. Model classes have `New` suffix (legacy naming: `UserNew`, `CurationNew`, `PrecurationNew`).
- **CRUD**: Generic `CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]` with `get()`, `get_multi()`, `create()`, `update()`, `remove()`. Domain CRUD modules extend this.
- **Scoring**: Abstract `ScoringEngine` base class. Three built-in engines registered via `ScoringEngineRegistry` singleton. Extend by subclassing `ScoringEngine` and calling `scoring_registry.register()`.
- **API routers**: 20 modules in `backend/app/api/v1/endpoints/`, registered in `api.py`. Note: `invitations`, `evidence`, and `gene_summaries` routers have **no prefix** (they define full paths internally).

**Configuration three-tier system**:
1. `app/core/constants.py` — Immutable values, HTTP codes, pagination limits
2. `app/core/config.py` — Pydantic Settings from `.env` (secrets, DB URL)
3. `backend/config/api.yaml` — CORS, rate limits, features. Env override: `GENE_CURATOR_API__CORS__ALLOW_ORIGINS`

### Frontend Structure

- **API client** (`src/api/client.js`): Axios with `baseURL=${VITE_API_BASE_URL}/api/v1`. Auto token refresh on 401 (single retry with `_retry` flag). Request correlation IDs via UUID.
- **Router** (`src/router/index.js`): All routes lazy-loaded. Route `meta` drives auth (`requiresAuth`, `requiredRoles`), guest redirects (`requiresGuest`), and navbar generation (`showInMainMenu`, `showInDropdown`, `order`).
- **Stores**: All `useXxxStore` in `src/stores/`. Newer stores use Composition API (`defineStore('name', () => {})`), older ones use Options API. Standard methods: `fetchItems()`, `fetchItemById(id)`, `createItem(data)`, `updateItem(id, data)`, `deleteItem(id)`.
- **Composables**: 17 in `src/composables/`. Key: `usePermissions`, `useScopePermissions`, `useValidation`, `useScoring`, `useOptimisticLocking`, `useFormRecovery`.

`main.js` plugin order matters: pinia first → loggerPlugin → router → vuetify.

### Testing Architecture

Backend tests use **in-memory SQLite** (not PostgreSQL) via `backend/app/models/db_types.py` compatibility layer (`compatible_uuid()`, `compatible_jsonb()`, etc.). This enables fast test isolation while production uses PostgreSQL.

`conftest.py` provides: `db_session` (fresh tables per test), `client` (FastAPI TestClient with dependency overrides), pre-built users with scope memberships, JWT tokens with `sub=uuid`, and httpx mocks for external APIs (HGNC, PubMed, HPO).

Frontend uses Vitest + Vue Test Utils + happy-dom. E2E via Playwright.

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`) uses **path filtering**: backend CI only runs when `backend/**` changes, frontend CI only when `frontend/**` changes. Cancel-in-progress for same ref. Never uses `continue-on-error`.

---

## Critical Bugs to Avoid

### SQLAlchemy Boolean Filters
```python
# CORRECT
query.filter(Model.is_active)
query.filter(~Model.is_active)
query.filter(Model.is_active == True)

# WRONG - WILL FAIL (checks identity, not value)
query.filter(Model.is_active is True)
query.filter(Model.is_active is False)
```

### ScopeMembership Pending Check
`ScopeMembership.accepted_at` is NULL for pending invitations, non-NULL for active members. `require_scope_role()` checks `accepted_at.isnot(None)` to exclude pending invitations.

### Never Skip Failing Tests
Never use `continue-on-error: true` in CI, `.skip()`/`xit()`, or comment out tests. Fix them.

---

## Logging

### Backend
```python
from app.core.logging import get_logger, api_endpoint, timed_operation

logger = get_logger(__name__)  # NOT logging.getLogger()
logger.info("Message", key="value", another_key=123)

@api_endpoint()  # Auto-timing
async def my_endpoint(): pass
```
Never: `logging.getLogger()`, `print()`, `f"Error: {e}"`

### Frontend
```javascript
import { useLogger } from '@/composables/useLogger'  // components
import { logService } from '@/services/logService'    // stores/utilities
```
Never: `console.log()`, `console.error()`, `alert()`. Log viewer: `Ctrl+L` / `Cmd+L`.

---

## Key Directories

```
backend/app/
├── api/v1/endpoints/     # 20 API route modules
├── models/models.py      # All SQLAlchemy models (New suffix convention)
├── models/db_types.py    # PostgreSQL/SQLite compatible column types
├── schemas/              # Pydantic request/response schemas
├── core/
│   ├── config.py         # Pydantic Settings (env-based)
│   ├── constants.py      # Immutable values
│   ├── api_config.py     # YAML-based API config
│   ├── database.py       # Sync + async engines, get_db()
│   ├── security.py       # PyJWT auth, bcrypt
│   ├── deps.py           # Auth dependencies, RLS context, typed aliases
│   ├── enums.py          # ApplicationRole, ScopeRole with permission methods
│   ├── schema_validator.py  # Dynamic schema validation engine
│   └── logging/          # Unified logging (7 modules)
├── crud/                 # CRUDBase + domain CRUD + workflow engine
├── scoring/              # ScoringEngine ABC + registry + clingen/gencc/qualitative
└── services/             # Scope permissions, validation, ontology, publications

frontend/src/
├── api/client.js         # Axios instance (token refresh, correlation IDs)
├── api/                  # 13 API modules (authAPI, scopesAPI, etc.)
├── stores/               # 17 Pinia stores
├── composables/          # 17 composables (permissions, validation, scoring)
├── views/                # Pages (lazy-loaded via router)
├── router/index.js       # Meta-driven auth + navigation generation
└── services/             # logService, scopeService

database/sql/             # 25 migration files (001-025), seed data in 004
```

---

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Backend**: ruff + mypy + bandit. Python 3.12. Dependencies in `backend/pyproject.toml`.
- **Frontend**: ESLint + Prettier. Node 20. Dependencies in `frontend/package.json`.
- **Branches**: `feature/description` or `fix/description`
- **docs/** = existing system documentation; **plan/** = future work planning and tracking

---

**Last Updated**: 2026-02-28
