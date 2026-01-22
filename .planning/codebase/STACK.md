# Technology Stack

**Analysis Date:** 2026-01-22

## Languages

**Primary:**
- Python 3.10+ - Backend API, data services, validation engines
- JavaScript/TypeScript 5.7 - Frontend UI components and state management
- SQL - PostgreSQL database schema and migrations
- YAML - Configuration management (`backend/config/api.yaml`)

**Secondary:**
- Bash - Makefile scripts, Docker entrypoints
- XML - PubMed API response parsing (`defusedxml` for security)

## Runtime

**Environment:**
- Python 3.10, 3.11, 3.12 (supported per `pyproject.toml` classifiers)
- Node.js 18+ (implied by TypeScript 5.7 and npm)
- PostgreSQL 15+ (Alpine Linux 15 in containers)
- Redis 7+ (Alpine Linux, optional caching/session layer)

**Package Manager:**
- Python: `uv` (fast, modern Python package manager)
  - Lockfile: `backend/uv.lock` (present via `uv sync`)
- JavaScript: `npm` (Node Package Manager)
  - Lockfile: `frontend/package-lock.json`

## Frameworks

**Core:**
- FastAPI 0.104.1+ - REST API framework with automatic OpenAPI docs
- SQLAlchemy 2.0.23+ - ORM with async support and modern type safety
- Vue 3.4.21+ - Progressive JavaScript framework for UI
- Vite 7.3.1+ - Next-generation frontend build tool

**API & Validation:**
- Pydantic 2.5+ - Data validation and serialization
- Pydantic-settings 2.1+ - Environment-based configuration
- python-jose 3.3.0+ - JWT token creation/verification
- passlib + bcrypt - Password hashing and verification

**Database:**
- Alembic 1.13+ - Schema migrations and version control
- asyncpg 0.29+ - Async PostgreSQL driver
- psycopg2-binary 2.9.9+ - Synchronous PostgreSQL driver

**State Management (Frontend):**
- Pinia 2.1.7+ - Composable, type-safe state management for Vue
- Vuetify 3.9.3+ - Material Design component library

**Routing:**
- Vue Router 4.3+ - Client-side routing for SPA
- FastAPI routing - Built-in endpoint decorators

**Testing:**
- pytest 7.4.3+ - Python unit/integration test framework
- pytest-asyncio 0.21.1+ - Async test support
- pytest-cov 4.1+ - Coverage reporting
- Vitest 3.2.4+ - Fast Vue unit test framework (Vite-native)
- @playwright/test 1.56+ - E2E browser testing
- @vue/test-utils 2.4.6+ - Vue component testing utilities
- happy-dom 20.1+ - Lightweight DOM implementation for unit tests
- jsdom 27.0+ - Full DOM implementation for integration tests

**Linting & Formatting:**
- ruff 0.1.6+ - Fast Python linter (replaces multiple tools)
- mypy 1.7.1+ - Static type checking for Python
- bandit 1.7.5+ - Security linting
- pip-audit 2.6+ - Dependency vulnerability scanning
- ESLint 8.57+ - JavaScript/Vue linting
- Prettier 3.2.5+ - Code formatting
- @vue/eslint-config-prettier 9.0+ - Vue + Prettier integration

**Build & Development:**
- Uvicorn 0.24+ - ASGI application server (async, reload support)
- Hatchling - Build backend for Python packaging
- esbuild 0.27.2+ - Fast JavaScript bundler (used by Vite)

## Key Dependencies

**Critical:**
- httpx 0.25.2+ - Async HTTP client for external API validation calls (HGNC, PubMed, HPO, MONDO, OMIM)
- redis 5.0.1+ - Python Redis client (optional, caching layer)
- celery 5.3.4+ - Distributed task queue (declared but not actively used in current codebase)
- pandas 2.1.4+ - Data manipulation and CSV/XLSX processing
- openpyxl 3.1.2+ - Excel file parsing
- pyyaml 6.0.1+ - YAML configuration parsing
- defusedxml 0.7.1+ - XML parsing with XXE protection
- python-dateutil 2.8.2+ - Date/time utilities
- python-multipart 0.0.6+ - Form data parsing
- @vueuse/core 14.1+ - Composable utilities collection for Vue
- axios 1.13.2+ - Promise-based HTTP client for frontend
- file-saver 2.0.5+ - Browser file download utilities
- papaparse 5.4.1+ - CSV parsing and generation
- @mdi/font 7.4.47+ - Material Design Icons

**Infrastructure:**
- postgres:15-alpine - PostgreSQL relational database
- redis:7-alpine - In-memory data store for caching
- gene_curator_network (Docker bridge network) - Inter-service communication

## Configuration

**Environment:**
Three-tier configuration system:
1. **Constants** (`backend/app/core/constants.py`) - Immutable application values (defaults, HTTP codes)
2. **Settings** (`backend/app/core/config.py`) - Pydantic environment-based config (DATABASE_URL, SECRET_KEY, REDIS_URL)
3. **API Config** (`backend/config/api.yaml`) - YAML-based API settings (CORS, rate limits, pagination, file uploads, logging retention, timeouts)

**Key Config Files:**
- `.env.dev` - Development environment variables (ports, credentials, database URLs)
- `backend/config/api.yaml` - API-level configuration (CORS, rate limits, timeouts, pagination)
- `frontend/.env.local` - Frontend development overrides (VITE_API_BASE_URL, VITE_ENVIRONMENT)
- `backend/pyproject.toml` - Python project metadata, dependencies, tool configuration
- `frontend/package.json` - Node.js project metadata, dependencies, scripts
- `frontend/vite.config.js` - Vite build and dev server configuration
- `frontend/tsconfig.json` - TypeScript compiler options

**Build:**
- Python: Hatchling build system (wheel output)
- Frontend: Vite (bundles to `dist/` directory)
- Containers: Docker with multi-stage builds (production target)

## Port Configuration (Non-Standard)

**Development:**
- **Backend API**: 8051 (FastAPI + Uvicorn)
- **Frontend (Vite dev)**: 5193 (Vite dev server with HMR)
- **Frontend (Docker)**: 3051 (Nginx in container)
- **PostgreSQL**: 5454 (Hybrid mode, local Docker)
- **Redis**: 6399 (Hybrid mode, local Docker)

**Production (Docker Compose):**
- **Backend**: 8001 (mapped from internal 8000)
- **Frontend**: 3000 (mapped from internal 80)
- **PostgreSQL**: Internal only (5432), no external mapping
- **Redis**: Internal only (6379), no external mapping

*Non-standard ports chosen to avoid conflicts with system services.*

## Platform Requirements

**Development:**
- Python 3.10+ with `uv` package manager
- Node.js 18+ with npm
- Docker & Docker Compose (for hybrid and full-docker modes)
- PostgreSQL client tools (optional, for direct shell access)
- Unix-like environment (Linux, macOS) or WSL2 on Windows

**Production:**
- Docker & Docker Compose
- PostgreSQL 15+ database server
- Redis 7+ server (optional, for caching)
- 2+ CPU cores, 2GB+ RAM (minimum)
- 10GB+ disk space (recommended)

---

*Stack analysis: 2026-01-22*
