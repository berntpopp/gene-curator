# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Gene Curator Project Overview

Gene Curator is a **schema-agnostic genetic curation platform** supporting any curation methodology (ClinGen, GenCC, institutional) through configurable schemas, scope-based organization, and multi-stage workflows. Built with PostgreSQL, FastAPI, and Vue 3.

### Core Architecture (v2.0.0)
- **Database**: PostgreSQL 15+ with JSONB-based flexible evidence storage
- **Backend**: FastAPI + SQLAlchemy + uv package management
- **Frontend**: Vue 3.5 + Vite + Pinia + Vuetify 3
- **Authentication**: JWT-based with 5-tier RBAC (viewer, curator, reviewer, admin, scope_admin)
- **Workflow**: Multi-stage pipeline (entry → precuration → curation → review → active) with 4-eyes principle
- **Scoring**: Pluggable scoring engines (ClinGen SOP v11, GenCC, Qualitative)

### Key Features
- **Methodology-Agnostic**: Support any curation approach through schema definitions
- **Scope-Based**: Clinical specialty organization (kidney-genetics, cardio-genetics, etc.)
- **Dynamic Validation**: Real-time evidence validation with 12+ field types
- **Multi-Curation**: Multiple curations per gene-scope with active/archived status
- **Quality Assurance**: Mandatory peer review (4-eyes principle) before activation
- **Provenance**: Complete audit trail with SHA-256 record hashing

## Essential Commands

### Quick Start
```bash
# RECOMMENDED: Hybrid Development Mode (DB in Docker, API/Frontend local)
make hybrid-up     # Start PostgreSQL in Docker
make backend       # Terminal 1: Start backend API (port 8051)
make frontend      # Terminal 2: Start frontend (port 5193)
make status        # Check system status
make help          # Show all 50+ commands
```

### Development Modes

**Hybrid Mode (RECOMMENDED for fast iteration)**
```bash
# Fastest development workflow - no Docker rebuild needed
make hybrid-up     # Start DB services only (ports: DB=5454, Redis=6399)
make backend       # Start backend API locally (port 8051)
make frontend      # Start frontend locally (port 5193)
make hybrid-down   # Stop all services

# Access points in hybrid mode:
# - Frontend (Vite):  http://localhost:5193
# - Backend API:      http://localhost:8051/docs
# - Database:         localhost:5454
```

**Full Docker Mode (all services in containers)**
```bash
# All services in Docker
make dev           # Start full stack (backend:8051, frontend:3051, db:5454)
make dev-build     # Rebuild and start
make dev-down      # Stop environment
make dev-logs      # View logs
make dev-restart   # Restart all services
```

### Port Configuration (Non-Standard - No Conflicts)

**⚠️ IMPORTANT: Gene Curator uses NON-STANDARD PORTS to avoid conflicts with other applications.**

All ports are configured in `.env.dev` to avoid conflicts with other applications:
- **Backend API**: 8051 (instead of 8001/8000)
- **Frontend Docker**: 3051 (instead of 3001)
- **Frontend Vite Dev**: 5193 (instead of 5173)
- **PostgreSQL**: 5454 (instead of 5433 standard, or 5453 old dev port)
- **Redis**: 6399 (instead of 6379)

**Why Non-Standard Ports?**
- Allows running Gene Curator alongside other projects (like kidney-genetics-db) without port conflicts
- Consistent development experience across team members
- Easy to identify Gene Curator services by port numbers

**If You See Port Confusion:**
- ✅ **CORRECT PostgreSQL port**: `5454` (current configuration)
- ❌ **OLD port**: `5453` (deprecated, do not use)
- ❌ **STANDARD port**: `5433` (conflicts with other projects)
- 📍 **Source of truth**: Check `.env.dev` for current port configuration

**Database Connection Examples:**
```bash
# Correct - use port 5454
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev

# Correct - DATABASE_URL format
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5454/gene_curator_dev

# Correct - Docker healthcheck
docker exec gene_curator_postgres pg_isready -U dev_user -d gene_curator_dev
```

### Database Management
```bash
make db-init         # Initialize database with seed data
make db-reset        # Complete database reset (destructive)
make db-clean        # Remove all data (keep structure)
make db-shell        # Open PostgreSQL shell
make db-backup-full  # Create full database backup
make db-restore      # Restore from backup
make db-migrate      # Run database migrations
```

### Monitoring & Status
```bash
make status        # Comprehensive system status with database stats
make health        # Health checks for all services
make version       # Show component versions
make ps            # Show running containers
make top           # Container resource usage
```

### Testing & Code Quality
```bash
# Testing
make test              # Run all backend tests
make test-unit         # Unit tests only (fast)
make test-integration  # Integration tests
make test-coverage     # Tests with coverage report
make test-frontend     # Frontend tests

# Code Quality
make lint              # Backend linting (ruff, mypy, bandit)
make lint-frontend     # Frontend linting (ESLint)
make format            # Backend formatting
make format-frontend   # Frontend formatting (Prettier)
make format-all        # Format all code
make check             # Run all quality checks
```

### Utilities
```bash
make backend-shell     # Open bash shell in backend container
make frontend-shell    # Open bash shell in frontend container
make clean             # Clean up Docker resources
make clean-all         # Stop everything and clean all data
make install-backend   # Install backend dependencies
make install-frontend  # Install frontend dependencies
make docs              # Show API documentation URLs
```

### Backend Commands (Direct - in backend/)
```bash
# Development
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8051

# Code Quality
uv run python scripts/lint.py    # All linting checks
uv run python scripts/format.py  # Auto-format
uv run ruff check                # Ruff only
uv run mypy app                  # Type checking only
uv run bandit -r app             # Security analysis only

# Testing
uv run pytest                    # Run tests
uv run pytest --cov=app          # With coverage
```

### Frontend Commands (Direct - in frontend/)
```bash
# Development
npm run dev -- --port 5193  # Vite dev server (non-standard port)
npm run build               # Production build
npm run preview             # Preview production build

# Code Quality
npm run lint       # ESLint with auto-fix
npm run lint:check # ESLint check only
npm run format     # Prettier formatting
npm run format:check # Prettier check only
npm run test:lint  # Comprehensive linting test
```

## API Endpoints

### Core Schema-Agnostic System
```bash
# Health & Auth
GET    /health                                    # Health check
POST   /api/v1/auth/login                         # JWT authentication
POST   /api/v1/auth/refresh                       # Refresh token

# Scope Management (Clinical Specialties)
GET    /api/v1/scopes                             # List all scopes
POST   /api/v1/scopes                             # Create scope
GET    /api/v1/scopes/{scope_id}                  # Get scope
PUT    /api/v1/scopes/{scope_id}                  # Update scope
DELETE /api/v1/scopes/{scope_id}                  # Delete scope
GET    /api/v1/scopes/{scope_id}/statistics       # Scope analytics

# Schema Repository (Methodology Management)
GET    /api/v1/schemas                            # List schemas
POST   /api/v1/schemas                            # Create schema
GET    /api/v1/schemas/{schema_id}                # Get schema
PUT    /api/v1/schemas/{schema_id}                # Update schema
DELETE /api/v1/schemas/{schema_id}                # Delete schema
GET    /api/v1/schemas/{schema_id}/usage-statistics # Usage stats

# Dynamic Validation
POST   /api/v1/validation/validate-evidence       # Validate evidence
POST   /api/v1/validation/validate-schema         # Validate schema
GET    /api/v1/validation/generate-json-schema/{schema_id} # JSON Schema
GET    /api/v1/validation/supported-field-types   # Field types

# Gene Assignment System
GET    /api/v1/gene-assignments                   # List assignments
POST   /api/v1/gene-assignments/bulk              # Bulk assign
GET    /api/v1/gene-assignments/curator/{curator_id}/workload # Workload
PUT    /api/v1/gene-assignments/{assignment_id}/priority # Update priority

# Multi-Stage Workflow
GET    /api/v1/workflow/analytics                 # Analytics
POST   /api/v1/workflow/curation/{curation_id}/transition # Transition
GET    /api/v1/workflow/curation/{curation_id}/available-transitions # Available
GET    /api/v1/workflow/peer-reviewers            # Reviewers

# Gene Management
GET    /api/v1/genes                              # List genes
GET    /api/v1/genes/{gene_id}/assignments        # Gene assignments
GET    /api/v1/genes/{gene_id}/curation-progress  # Progress by scope

# User Management
GET    /api/v1/users                              # List users
POST   /api/v1/users                              # Create user
GET    /api/v1/users/{user_id}                    # Get user
PUT    /api/v1/users/{user_id}                    # Update user
DELETE /api/v1/users/{user_id}                    # Delete user
```

## Architecture Overview

### Technology Stack

**Database (PostgreSQL 15+)**:
- JSONB evidence storage for methodology flexibility
- Scope-based organization with clinical specialties
- Multi-stage workflow support (5 stages)
- Enhanced RBAC with 5 roles
- Complete audit trail with provenance hashing

**Backend (FastAPI + SQLAlchemy)**:
- **Package Management**: uv (modern, fast Python package manager)
- **API**: RESTful with OpenAPI/Swagger documentation
- **Validation**: Dynamic schema validation engine
- **Scoring**: Pluggable engines (ClinGen, GenCC, Qualitative)
- **Security**: JWT authentication, CORS, input validation
- **Type Safety**: Full Pydantic validation + mypy

**Frontend (Vue 3 + Vite)**:
- **Framework**: Vue 3.4.21 with Composition API
- **Build**: Vite 5.2.8 (ESM-based, fast HMR)
- **State**: Pinia 2.1.7 with API integration
- **UI**: Vuetify 3.9.3 (Material Design)
- **Routing**: Vue Router 4.3.0 with auth guards

### Core Architectural Patterns

#### 1. Schema-Driven Architecture
Everything is driven by configurable schema definitions:
- **Field Definitions**: What data to collect
- **Validation Rules**: How to validate data
- **Scoring Algorithms**: How to compute verdicts
- **UI Configuration**: How to render forms
- **Workflow States**: Multi-stage pipeline configuration

#### 2. Scope-Based Organization
Clinical specialties as first-class entities:
- **Scopes**: kidney-genetics, cardio-genetics, neuro-genetics, etc.
- **Gene Assignments**: Many-to-many with curator assignment
- **Access Control**: Scope-based permissions and RBAC
- **Workflow Configuration**: Scope-specific methodology selection

#### 3. Multi-Stage Workflow (5 Stages)
```
Entry → Precuration → Curation → Review (4-eyes) → Active
  ↓         ↓            ↓            ↓              ↓
Draft    Multiple     Multiple    Mandatory      One per
State    per Gene     per Gene    Peer Review    Gene-Scope
```

**Key Features**:
- **Draft Management**: Auto-save, resume work
- **4-Eyes Principle**: Independent reviewer required
- **Active Status**: One active curation per gene-scope
- **Archive Management**: Historical tracking of all versions

#### 4. Store Pattern (Pinia)
All frontend stores follow consistent API patterns:
```javascript
// Standard store functions
fetchItems()                  // Fetch all
fetchItemById(id)             // Fetch single
createItem(data)              // Create
updateItem(id, data)          // Update
deleteItem(id)                // Delete
```

**Existing Stores**:
- `auth.js`: Authentication and JWT management
- `scopes.js`: Scope management
- `schemas.js`: Schema repository
- `validation.js`: Dynamic validation
- `workflow.js`: Workflow state management
- `assignments.js`: Gene-scope assignments
- `genes.js`: Gene management
- `users.js`: User management

### Key Directories

```
/backend/app
  /api/v1/endpoints/      # API route handlers (10 endpoints)
    auth.py              # Authentication & JWT
    scopes.py            # Scope management
    schemas.py           # Schema repository
    schema_validation.py # Dynamic validation
    gene_assignments.py  # Gene assignment system
    workflow.py          # Multi-stage workflow
    genes_new.py         # Gene management
    users.py             # User management
    health.py            # Health checks
  /models/               # SQLAlchemy models
    models.py           # Schema-agnostic database models
  /schemas/              # Pydantic request/response schemas
  /core/                 # Core functionality
    config.py          # Application configuration
    database.py        # Database connection
    security.py        # JWT & auth utilities
    schema_validator.py # Dynamic validation engine
  /crud/                 # Database CRUD operations
    scope.py           # Scope CRUD
    schema_repository.py # Schema CRUD
    gene_assignment.py # Assignment CRUD
    workflow_engine.py # Workflow CRUD
    gene_new.py        # Gene CRUD
    user.py            # User CRUD
  /scoring/              # Pluggable scoring engines
    registry.py        # Engine registry
    base.py            # Abstract base class
    clingen.py         # ClinGen SOP v11 engine
    gencc.py           # GenCC classification
    qualitative.py     # Qualitative assessment

/frontend/src
  /api/                  # API client & axios
  /components/           # Vue components
  /stores/               # Pinia state management (9 stores)
  /views/                # Page-level components
  /router/               # Vue Router configuration
  /types/                # TypeScript definitions
  /composables/          # Vue composition functions

/database/sql            # PostgreSQL schema
  001_schema_foundation.sql # Core tables & enums
  002_schema_triggers.sql   # Triggers & constraints
  003_schema_views.sql      # Views & queries
  004_seed_data.sql         # Sample data
```

### Database Schema (PostgreSQL)

**Core Tables**:
- `scopes`: Clinical specialties (kidney-genetics, cardio-genetics)
- `users_new`: Enhanced users with scope assignments, ORCID
- `curation_schemas`: Repository of methodology definitions
- `workflow_pairs`: Precuration + curation schema combinations
- `genes_new`: HGNC-compliant genes with JSONB details
- `gene_scope_assignments`: Many-to-many gene-scope with curator assignment

**Multi-Stage Workflow Tables**:
- `precurations_new`: Multiple precurations per gene-scope
- `curations_new`: Multiple curations per gene-scope with scoring
- `reviews`: 4-eyes principle review tracking
- `active_curations`: One active curation per gene-scope

**Audit & Tracking**:
- `audit_log_new`: Complete audit trail with scope context
- `schema_selections`: User/institutional schema preferences

**Enums**:
- `user_role_new`: viewer, curator, reviewer, admin, scope_admin
- `workflow_stage`: entry, precuration, curation, review, active
- `review_status`: pending, approved, rejected, needs_revision
- `curation_status`: draft, submitted, in_review, approved, rejected, active, archived
- `schema_type`: precuration, curation, combined

### Environment Setup

**⚠️ CRITICAL: Frontend `.env.local` Required**

The frontend MUST have a `.env.local` file to override the default API URL. Without this file, login will fail silently because requests go to the wrong port.

**Create `frontend/.env.local`**:
```bash
# Backend API URL (REQUIRED - Gene Curator uses non-standard port 8051)
VITE_API_BASE_URL=http://localhost:8051

# Application configuration
VITE_APP_TITLE=Gene Curator (Dev)
VITE_ENVIRONMENT=development
VITE_ENABLE_DEV_LOGIN=true
```

**Why is this required?**
- Default API URL in `client.js` is `http://localhost:8001` (wrong port)
- Gene Curator backend runs on port **8051** (non-standard to avoid conflicts)
- Without `.env.local`, frontend sends requests to port 8001 where nothing is listening
- This causes **silent login failures** (no backend logs, no error messages)

**After creating `.env.local`**:
1. Vite will automatically restart (watch for log message)
2. Refresh your browser (Ctrl+R or Cmd+R)
3. Login buttons should now work correctly

**Troubleshooting**: See `docs/troubleshooting/LOGIN_ISSUES.md` for detailed troubleshooting

---

**Root Level (.env.dev)**:
```bash
# Non-standard ports to avoid conflicts
BACKEND_PORT=8051
FRONTEND_PORT=3051
POSTGRES_PORT=5454
VITE_DEV_PORT=5193
REDIS_PORT=6399

# Database
POSTGRES_DB=gene_curator_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5454/gene_curator_dev

# Backend
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug
SECRET_KEY=dev_secret_key_change_in_production
ALLOWED_ORIGINS=["http://localhost:3051","http://localhost:5193"]

# Frontend
VITE_API_BASE_URL=http://localhost:8051
VITE_APP_TITLE=Gene Curator (Dev)
```

**Backend (.env in backend/)** - For local development:
```bash
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5454/gene_curator_dev
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
LOG_LEVEL=debug
ALLOWED_ORIGINS=["http://localhost:3051", "http://localhost:5193"]
```

**Frontend (.env.local in frontend/)** - For local development:
```bash
VITE_API_BASE_URL=http://localhost:8051
VITE_APP_TITLE=Gene Curator
VITE_ENVIRONMENT=development
```

### Docker Configuration

**Development Environment (Non-Standard Ports)**:
- **Backend API**: http://localhost:8051 (internal port 8000)
- **Frontend Docker**: http://localhost:3051 (internal port 3000)
- **Frontend Vite**: http://localhost:5193 (local development)
- **Database**: localhost:5454 (PostgreSQL 15)
- **Redis**: localhost:6399
- **API Docs**: http://localhost:8051/docs (Swagger)
- **Credentials**: dev_user / dev_password / gene_curator_dev

**Hybrid Mode (RECOMMENDED)**:
- **Database**: Docker container on port 5454
- **Redis**: Docker container on port 6399
- **Backend API**: Local process on port 8051
- **Frontend**: Local Vite dev server on port 5193
- **Benefits**: Instant code reload, no Docker rebuild, fastest iteration

**Production Environment**:
- **Backend**: Port 8001 (configurable)
- **Frontend**: Port 3000 (nginx served)
- **Database**: Port 5432 (internal network)

## Data Flow

### Typical Curation Workflow

```
1. Gene Entry
   └─ Admin creates gene with HGNC ID
   └─ Assigns to scope (e.g., kidney-genetics)
   └─ Optional: Assign curator

2. Precuration Stage
   └─ Curator selects gene for precuration
   └─ Collects disease association evidence
   └─ Schema-driven validation and scoring
   └─ Can save as draft, submit when complete
   └─ Multiple precurations possible per gene-scope

3. Curation Stage
   └─ Curator creates curation referencing precuration
   └─ Collects detailed evidence per methodology schema
   └─ Real-time scoring via pluggable engine
   └─ Draft save/resume with auto-save
   └─ Submit for review when complete

4. Review Stage (4-Eyes Principle)
   └─ Different reviewer assigned (quality assurance)
   └─ Independent review of curation work
   └─ Can approve, reject, or request revision
   └─ Mandatory before activation

5. Active Status
   └─ Approved curation becomes active
   └─ One active curation per gene-scope
   └─ Previous active automatically archived
   └─ Complete audit trail maintained
```

### Evidence Storage & Validation

**JSONB Evidence Storage**:
- Flexible structure adapts to any methodology
- Schema-driven validation at runtime
- Supports 12+ field types (text, number, select, multiselect, evidence_table, etc.)
- Real-time validation feedback

**Pluggable Scoring Engines**:
```python
# ClinGen SOP v11 Engine
verdict = clingen_engine.compute_verdict(evidence_data)

# GenCC Classification Engine
verdict = gencc_engine.compute_verdict(evidence_data)

# Qualitative Assessment Engine
verdict = qualitative_engine.compute_verdict(evidence_data)
```

## Implementation Status

### ✅ Phase 1: Core Infrastructure (Complete)
- PostgreSQL schema with scope-based architecture
- FastAPI backend with JWT authentication
- Vue 3 + Vite frontend with Pinia
- Docker-based development environment
- Health monitoring and logging

### ✅ Phase 2: Schema-Agnostic Foundation (Complete)
- Schema repository and management system
- Dynamic validation engine (12+ field types)
- Pluggable scoring engine registry
- Scope-based organization
- Multi-stage workflow engine (5 stages)
- 4-eyes principle review system

### ✅ Phase 3: API Implementation (Complete)
- 10 endpoint modules with 30+ routes
- Complete CRUD operations for all entities
- JWT authentication and RBAC
- Scope-based access control
- Workflow transitions and analytics
- Gene assignment and workload management

### ✅ Phase 4: Frontend Integration (Complete)
- 9 Pinia stores with API integration
- Authentication and protected routes
- User, gene, scope, schema management
- Workflow and validation integration
- Responsive Vuetify UI

### 🔄 Phase 5: Production Readiness (Ongoing)
- [x] Comprehensive testing suite
- [x] Code quality with linting and formatting
- [x] Security best practices (JWT, CORS, validation)
- [x] Docker-based deployment
- [x] Health monitoring and observability
- [ ] Dynamic UI form generation (backend ready, frontend pending)
- [ ] Draft auto-save functionality (backend ready, frontend pending)
- [ ] Production deployment documentation

## Important File References

### Planning & Documentation
- `README.md`: Project overview and quick start
- `PLAN.md`: Complete architecture vision
- `plan/README.md`: Architecture overview
- `plan/SCHEMA_SPECIFICATIONS.md`: Schema format specification
- `plan/SCORING_ENGINE_GUIDE.md`: Plugin development guide

### Configuration Files
- `docker-compose.yml`: Production Docker configuration
- `docker-compose.dev.yml`: Development overrides
- `backend/pyproject.toml`: Python dependencies + tool config (uv)
- `frontend/package.json`: Frontend dependencies + scripts
- `Makefile`: Development commands

### Database
- `database/sql/001_schema_foundation.sql`: Core tables & enums
- `database/sql/002_schema_triggers.sql`: Triggers & constraints
- `database/sql/003_schema_views.sql`: Views & queries
- `database/sql/004_seed_data.sql`: Sample development data

### Backend Core
- `backend/app/main.py`: FastAPI application entry
- `backend/app/api/v1/api.py`: API router configuration
- `backend/app/models/models.py`: SQLAlchemy models
- `backend/app/core/config.py`: Application settings
- `backend/app/core/schema_validator.py`: Dynamic validation
- `backend/app/scoring/registry.py`: Scoring engine registry

### Frontend Core
- `frontend/src/main.js`: Vue application entry
- `frontend/src/router/index.js`: Route configuration
- `frontend/src/stores/`: Pinia state management
- `frontend/src/api/`: API client configuration

## Development Guidelines

### When Working with Schemas
- Schemas are stored in `curation_schemas` table with JSONB
- Use schema validator for runtime validation
- Test with all three scoring engines (ClinGen, GenCC, Qualitative)
- See `plan/SCHEMA_SPECIFICATIONS.md` for format details

### When Working with Scopes
- All curation work is scope-based (kidney-genetics, etc.)
- Users can be assigned to multiple scopes
- Genes can be assigned to multiple scopes
- One active curation per gene-scope combination

### When Working with Workflows
- Follow 5-stage pipeline: entry → precuration → curation → review → active
- 4-eyes principle is mandatory (different reviewer)
- Draft states support work-in-progress
- All transitions are tracked in audit log

### When Adding Scoring Engines
1. Extend `ScoringEngine` base class in `backend/app/scoring/base.py`
2. Implement `compute_score()` and `compute_verdict()` methods
3. Register in `backend/app/scoring/registry.py`
4. Add tests in `backend/app/tests/`
5. See `plan/SCORING_ENGINE_GUIDE.md` for details

### Code Quality Standards
- **Backend**: Ruff + mypy + bandit (use `make lint`)
- **Frontend**: ESLint + Prettier (use `npm run lint`)
- **Type Safety**: Python type hints + mypy strict mode
- **Testing**: pytest for backend, comprehensive coverage expected
- **Security**: Bandit security checks, no secrets in code

### CRITICAL: SQLAlchemy Boolean Filters (ALWAYS FOLLOW)

**⚠️ WARNING**: SQLAlchemy boolean filters MUST use Pythonic direct evaluation, NOT Python identity operators.

**✅ CORRECT (Pythonic style)**:
```python
# Direct boolean evaluation - SQLAlchemy overloads __bool__()
query.filter(Model.is_active)
query.filter(~Model.is_active)  # negation

# Or explicit comparison (less Pythonic)
query.filter(Model.is_active == True)
query.filter(Model.is_active == False)
```

**❌ WRONG (Python identity check)**:
```python
# Python 'is' operator checks object identity, not SQLAlchemy column value
query.filter(Model.is_active is True)   # WILL FAIL
query.filter(Model.is_active is False)  # WILL FAIL
```

**Why This Matters**:
- SQLAlchemy columns have overloaded `__bool__()` methods
- Python `is` operator performs identity check (checks if same object in memory)
- `is True` will ALWAYS be False because SQLAlchemy column is not the literal `True` object
- This bug caused API to return 0 results instead of 25 scopes (2025-10-14)

**Detection**:
```bash
# Check for this anti-pattern in code
grep -r "is True\|is False" app/crud/ app/api/
```

**References**:
- Bug report: `docs/refactoring/CODE_QUALITY_LINTING_FIXES.md`
- SQLAlchemy docs: https://docs.sqlalchemy.org/en/20/core/sqlelement.html

### CRITICAL: Never Use Sed for Code Refactoring (ALWAYS FOLLOW)

**⚠️ WARNING**: NEVER use `sed` command for code refactoring. Use IDE refactoring tools or Edit tool instead.

**Why Sed Fails**:
- Line-based text editor, doesn't understand syntax
- Can't handle multi-line expressions correctly
- Places comments in wrong locations
- Breaks indentation and structure
- No context awareness (function boundaries, class definitions)

**Examples of Sed Failures** (2025-10-14):
```python
# Sed broke this by placing comment before closing paren
.filter(Model.is_active is True  # Fixed: use == instead of is)
# Should be:
.filter(Model.is_active)  # Fixed: use == instead of is

# Sed broke this naming convention fix
TestSessionLocal =  # noqa: N806 sessionmaker(autocommit=False...)
# Should be:
TestSessionLocal = sessionmaker(autocommit=False...)  # noqa: N806
```

**✅ Use Instead**:
- **Python**: PyCharm/VSCode refactoring, or Edit tool
- **JavaScript**: VSCode refactoring, or Edit tool
- **Multi-file**: Task tool with specific instructions

**If You Must Use Sed** (rare cases):
1. Test on ONE file first
2. Check the diff carefully
3. Run linting immediately after
4. Test the code functionality
5. Document what you changed and why

**References**:
- Bug report: `docs/refactoring/CODE_QUALITY_LINTING_FIXES.md`

### CRITICAL: Always Run Linting Before Commits (REQUIRED)

**⚠️ REQUIRED**: Linting MUST pass before committing code. No exceptions.

**Commands**:
```bash
# Backend linting (MUST pass - zero errors, zero warnings)
cd backend
uv run ruff check app/          # Python linting
uv run ruff format app/         # Auto-formatting
uv run mypy app/                # Type checking
uv run bandit -r app/           # Security analysis

# Frontend linting (MUST have 0 errors, warnings OK if documented)
cd frontend
npm run lint                    # ESLint with auto-fix
npm run format                  # Prettier formatting

# Or use Makefile shortcuts
make lint              # Backend only
make lint-frontend     # Frontend only
make format-all        # Auto-format everything
make check             # Complete quality check (lint + tests)
```

**Why This Matters**:
- Catches bugs before they reach production
- Enforces consistent code style
- Detects security issues early
- Type checking prevents runtime errors
- Saves time in code review

**Git Pre-Commit Hook** (Recommended):
```bash
#!/bin/bash
# .git/hooks/pre-commit (make executable with chmod +x)
cd backend && uv run ruff check app/ || exit 1
cd frontend && npm run lint || exit 1
echo "✅ Linting passed"
```

**References**:
- Bug report: `docs/refactoring/CODE_QUALITY_LINTING_FIXES.md`

### Unified Logging System (ALWAYS USE)

Gene Curator uses a production-grade unified logging system with request correlation, database persistence, and performance monitoring.

**Basic Usage**:
```python
from app.core.logging import get_logger

logger = get_logger(__name__)  # NOT logging.getLogger()

# Works in both async and sync contexts (auto-detects)
logger.info("Message", key="value", another_key=123)
logger.error("Error occurred", error=exception, context_data="value")
```

**NEVER Use These**:
- ❌ `logging.getLogger()` - Always use `get_logger()` instead
- ❌ `print()` - Always use logger
- ❌ Manual context building - Context is automatic via middleware
- ❌ `f"Error: {e}"` string formatting - Use `error=e` parameter

**Performance Monitoring**:
```python
from app.core.logging import timed_operation, api_endpoint, database_query

@api_endpoint()  # Automatic endpoint timing
async def my_endpoint():
    pass

@timed_operation("complex_calculation", warning_threshold_ms=200)
async def calculate():
    pass

@database_query("SELECT")
async def query_data():
    pass

@batch_operation("bulk_import", batch_size_getter=lambda data, **kwargs: len(data))
def bulk_import(data):
    pass
```

**Request Correlation**:
- All logs within a request automatically include the same `request_id`
- Query logs in production: `SELECT * FROM system_logs WHERE request_id = 'abc-123'`
- Request timing added to response headers: `X-Request-ID`, `X-Process-Time`

**Context Binding**:
```python
# Bind context for a specific operation
curation_logger = logger.bind(curation_id=42, scope_id=1)
curation_logger.info("Message")  # Includes curation_id and scope_id
```

**Automatic Sanitization**:
The logging system automatically protects sensitive data:
- Tokens, passwords, API keys → `[REDACTED]`
- Email addresses → `[REDACTED_EMAIL]`
- Genetic variants (HGVS notation) → `[REDACTED_VARIANT]`
- Genomic coordinates → `[REDACTED_COORDINATE]`

**When to Log**:
- **DEBUG**: Detailed operation flow (disabled in production)
- **INFO**: Normal operations (curation created, gene assigned)
- **WARNING**: Slow operations, deprecated usage, recoverable errors
- **ERROR**: Failed operations, caught exceptions
- **CRITICAL**: System failures, data corruption

**Database Persistence**:
- All logs automatically persisted to `system_logs` table
- Partitioned by month with 90-day retention
- JSONB context field for rich queries
- Query examples:
  ```sql
  -- All errors for a specific request
  SELECT * FROM system_logs WHERE request_id = 'abc-123';

  -- Slow operations
  SELECT * FROM system_logs WHERE duration_ms > 1000;

  -- User activity
  SELECT * FROM system_logs WHERE user_id = 'user-uuid';
  ```

### Frontend Logging System (ALWAYS USE)

Gene Curator's frontend uses a unified logging system with privacy protection, browser compatibility, and request correlation with the backend.

**Basic Usage**:
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

**NEVER Use These**:
- ❌ `console.log()` - Always use logger instead
- ❌ `console.error()` - Use logger.error() instead
- ❌ `alert()` - Use proper UI notifications + logging
- ❌ Direct console methods - Use logger for all output

**Privacy Protection**:
- Automatic sanitization of sensitive data (tokens, emails, genetic variants)
- Safe to log objects without manual redaction
- Performance-optimized with quick pre-checks before expensive regex tests
- Supports HGVS notation, genomic coordinates, and medical data redaction

**Request Correlation**:
- All API calls automatically include correlation ID (`X-Request-ID` header)
- Frontend logs match backend logs via same correlation ID
- Query backend: `SELECT * FROM system_logs WHERE request_id = 'correlation-id'`
- Enables end-to-end request tracking across frontend and backend

**API Call Logging**:
- Automatic logging of all API requests/responses via axios interceptors
- Performance tracking (duration in milliseconds)
- Error logging with full context (status, response data)
- Token refresh attempts logged automatically

**Performance Tracking**:
```javascript
const startTime = performance.now()
// ... operation ...
logger.logPerformance('operation_name', startTime, { data: 'value' })
```

**Component Context**:
```javascript
// Component name automatically included in logs
const logger = useLogger()  // Auto-detects component name
logger.info('Button clicked')  // Logs include component: 'MyComponent'

// Or override component name
const logger = useLogger('CustomName')
```

**Browser Compatibility**:
- UUID generation works in all browsers (polyfill included for Safari < 15.4)
- Tested in Safari 14+, Chrome 88+, Firefox 85+
- No crypto.randomUUID() dependency issues

**Log Levels**:
- **DEBUG**: Detailed operation flow (default in dev, disabled in production)
- **INFO**: User actions, navigation, state changes
- **WARN**: Unexpected situations, deprecated usage, slow operations
- **ERROR**: Failed operations, API errors, caught exceptions
- **CRITICAL**: Severe errors affecting app stability

**Configuration**:
```javascript
// Settings persisted in LocalStorage
logService.setMinLogLevel('INFO')       // Set minimum level
logService.setMaxEntries(100)           // Set max stored logs
logService.setConsoleEcho(true)         // Enable/disable console echo
logService.clearLogs()                   // Clear all logs
```

**Log Viewer UI** (In-Browser Development Tool):
- **Keyboard Shortcut**: `Ctrl+L` (Windows/Linux) or `Cmd+L` (Mac) to toggle log viewer
- **Features**:
  - Real-time log updates with automatic scrolling
  - Search and filter logs by message, level, or correlation ID
  - Filter by log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
  - View detailed log entry data (timestamp, message, data, context)
  - Export logs for bug reports (JSON or CSV format)
  - Clear logs button for fresh start
  - Persistent settings (log level, max entries, console echo)
- **Why Use It**:
  - See all frontend logs without opening browser console
  - Search across all logged events easily
  - Match frontend logs to backend logs via correlation ID
  - Export logs for sharing with team or bug reports
  - Persistente settings across browser sessions

**Export Functionality**:
```javascript
// Export logs programmatically
const exportData = logService.exportLogs()  // Returns JSON with metadata

// From Log Viewer UI:
// 1. Open log viewer (Ctrl+L / Cmd+L)
// 2. Click "Export" button
// 3. Choose format: JSON (full detail) or CSV (spreadsheet-friendly)
// 4. File automatically downloads with timestamp
```

**Best Practices**:
- Use logger in ALL components (not just for errors)
- Log user actions for debugging: clicks, navigations, form submissions
- Log API calls (automatic via interceptors)
- Log component lifecycle events: mounted, unmounted, data loaded
- Include relevant context in data parameter
- Use appropriate log levels
- Don't worry about sensitive data - automatic sanitization protects it

**When to Log (Frontend)**:
- User interactions (button clicks, form submissions)
- Navigation events (route changes)
- API calls (automatic via interceptors)
- Component lifecycle (mounting, data loading)
- State changes (Pinia store mutations)
- Errors and exceptions (automatic via error handler)
- Performance issues (slow operations > 1s)

**Memory Management**:
- Logs automatically trimmed to max entries (100 dev, 50 production)
- Statistics tracked (total received, dropped)
- Memory usage computed

**Architecture**:
- **Singleton Service** (`logService.js`): Centralized logging
- **Pinia Store** (`logStore.js`): Reactive log state
- **Vue Plugin** (`logger.js`): Global `$logger` property
- **Composable** (`useLogger.js`): Component-scoped loggers
- **Sanitizer** (`logSanitizer.js`): Privacy protection
- **UUID Polyfill** (`uuidPolyfill.js`): Browser compatibility

**Critical Fixes Applied**:
- ✅ Memory leak fix: Scoped logger functions (no global pollution)
- ✅ Race condition fix: Synchronous updates in Pinia store
- ✅ Browser compatibility: UUID polyfill for older browsers
- ✅ Performance: Quick pre-check before expensive regex tests
- ✅ Initialization: Store initialized once during plugin install

**Implementation Files**:
```
frontend/src/
├── services/logService.js           # Singleton logging service
├── utils/
│   ├── logSanitizer.js              # Privacy protection utility
│   └── uuidPolyfill.js              # Browser compatibility
├── stores/logStore.js               # Pinia reactive log state
├── components/logging/              # Log Viewer UI components
│   ├── LogViewer.vue                # Main log viewer interface
│   ├── LogEntry.vue                 # Individual log entry display
│   ├── LogFilters.vue               # Filtering controls
│   └── LogSettings.vue              # Settings dialog
├── plugins/logger.js                # Vue plugin ($logger)
└── composables/useLogger.js         # Component-scoped loggers
```

**Reference Documentation**:
- Full specification: `docs/enhancements/003-frontend-unified-logging-system-CORRECTED.md`
- All 6 critical bugs fixed (memory leak, race condition, browser compatibility, etc.)
- Production-ready with comprehensive testing

### Configuration Management (ALWAYS USE)

Gene Curator uses a modern, three-tier configuration system that eliminates hardcoded values and follows DRY, KISS, and SOLID principles.

**Three-Tier Architecture**:
1. **Constants** (`app/core/constants.py`): Immutable application-wide values
2. **Environment Settings** (`app/core/config.py`): Environment-specific config from `.env`
3. **API Configuration** (`backend/config/api.yaml`): Deployment-specific API settings

**✅ Design Principles**:
- **DRY** (Don't Repeat Yourself): Single source of truth for all configuration
- **KISS** (Keep It Simple): Simple YAML format, no complex logic
- **SOLID**: Separation of concerns, modular design
- **Type Safety**: Pydantic validation for all configuration values
- **Environment Overrides**: YAML defaults can be overridden via env vars
- **Immutability**: Configuration loaded once and cached

#### Using Constants (Most Common)

For application-wide magic numbers and strings:

```python
from app.core.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    LOGS_DEFAULT_LIMIT,
    LOGS_MAX_LIMIT,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    APP_NAME,
    APP_VERSION,
)

# Pagination in endpoints
@router.get("/items")
def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
):
    ...

# HTTP status codes
return JSONResponse(status_code=HTTP_200_OK, content=data)
```

**Available Constants**:
- Pagination: `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`, `GENES_DEFAULT_LIMIT`
- HTTP status codes: `HTTP_200_OK`, `HTTP_404_NOT_FOUND`, etc.
- Timeouts: `DEFAULT_REQUEST_TIMEOUT_SECONDS`, `LONG_RUNNING_OPERATION_TIMEOUT_SECONDS`
- File uploads: `MAX_FILE_SIZE_BYTES`, `ALLOWED_FILE_EXTENSIONS`
- Logging: `LOG_RETENTION_DEFAULT_DAYS`, `LOGS_MAX_EXPORT_LIMIT`
- Security: `ACCESS_TOKEN_EXPIRE_MINUTES`, `MIN_PASSWORD_LENGTH`
- Application metadata: `APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`

See full list: `backend/app/core/constants.py`

#### Using API Configuration

For deployment-specific settings that may vary per environment:

```python
from app.core.api_config import (
    get_cors_config,
    get_pagination_config,
    get_logging_config,
    get_rate_limit,
    get_timeout_config,
)

# CORS configuration
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.allow_origins,
    allow_credentials=cors_config.allow_credentials,
)

# Pagination with configured limits
@router.get("/logs")
async def get_logs(limit: int | None = None):
    logging_config = get_logging_config()
    effective_limit = limit or logging_config.max_export_limit

    # Enforce maximum
    if effective_limit > logging_config.max_export_limit:
        effective_limit = logging_config.max_export_limit
    ...

# Rate limiting
rate_limit = get_rate_limit("admin")  # or "authenticated", "curator"
apply_rate_limit(rate_limit.requests_per_minute, rate_limit.burst_size)
```

#### Configuration File Structure

**`backend/config/api.yaml`** (see full file for details):

```yaml
api:
  cors:
    allow_origins:
      - "http://localhost:3051"   # Frontend Docker
      - "http://localhost:5193"   # Vite dev server
    allow_credentials: false

  rate_limits:
    default: {requests_per_minute: 60, burst_size: 10}
    authenticated: {requests_per_minute: 300, burst_size: 50}
    curator: {requests_per_minute: 500, burst_size: 75}
    admin: {requests_per_minute: 1000, burst_size: 100}

  pagination:
    default_page_size: 50
    max_page_size: 1000
    genes: {default: 100, max: 500}
    logs: {default: 100, max: 1000}

  logging:
    retention_days: 90
    max_export_limit: 100000

  features:
    enable_docs_in_production: false
    enable_rate_limiting: false
    enable_experimental: false
```

#### Environment Variable Overrides

Override YAML values with environment variables:

```bash
# Format: GENE_CURATOR_API__<section>__<key>
export GENE_CURATOR_API__CORS__ALLOW_ORIGINS='["https://production.example.com"]'
export GENE_CURATOR_API__PAGINATION__DEFAULT_PAGE_SIZE=100
export GENE_CURATOR_API__LOGGING__RETENTION_DAYS=120
export GENE_CURATOR_API__FEATURES__ENABLE_RATE_LIMITING=true
```

#### When to Use Each Tier

**Use Constants when:**
- Value is truly application-wide and never changes
- It's a magic number that needs a name (50, 100, 1000)
- It's a standard value (HTTP status codes, algorithm names)
- Example: `HTTP_404_NOT_FOUND`, `DEFAULT_PAGE_SIZE`

**Use Environment Settings when:**
- Value contains secrets (SECRET_KEY, DATABASE_URL)
- Value changes per environment (ENVIRONMENT, DEBUG, LOG_LEVEL)
- Core application configuration (not API-level)
- Example: Database connection strings, JWT secrets

**Use API Configuration when:**
- Value is deployment-specific (CORS origins, rate limits)
- Operations team needs to adjust without code changes
- Multiple related values that form a logical group
- Example: Pagination limits, timeout settings, feature flags

#### Best Practices

**DO:**
- ✅ Import specific constants: `from app.core.constants import DEFAULT_PAGE_SIZE`
- ✅ Use config accessors: `get_pagination_config()`, `get_cors_config()`
- ✅ Validate configuration: All config uses Pydantic models
- ✅ Document why a value is set: Add comments to YAML file
- ✅ Use feature flags: Enable/disable features without deployment

**DON'T:**
- ❌ Hardcode magic numbers: Use constants instead
- ❌ Import entire modules: `from app.core.constants import *`
- ❌ Bypass config system: No `allow_origins=["http://localhost:3000"]`
- ❌ Store secrets in YAML: Use environment variables
- ❌ Put workflow/schema config in YAML: That's for the schema repository

#### Migration Pattern

When refactoring code to use configuration:

```python
# ❌ Before: Hardcoded values
@router.get("/items")
def list_items(limit: int = Query(100, ge=1, le=1000)):
    ...

# ✅ After: Using constants
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

@router.get("/items")
def list_items(limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)):
    ...

# ✅ After: Using API config (for configurable limits)
from app.core.api_config import get_pagination_config

@router.get("/items")
def list_items(limit: int | None = Query(None)):
    config = get_pagination_config()
    effective_limit = limit or config.default_page_size
    if effective_limit > config.max_page_size:
        effective_limit = config.max_page_size
    ...
```

#### Configuration Files Reference

- **Constants**: `backend/app/core/constants.py` (~300 lines, immutable values)
- **Settings**: `backend/app/core/config.py` (env-based settings with Pydantic)
- **API Config Module**: `backend/app/core/api_config.py` (YAML loader + accessors)
- **API Config File**: `backend/config/api.yaml` (deployment-specific settings)
- **Tests**: `backend/app/tests/unit/test_api_config.py` (26 unit tests, all passing)
- **Enhancement Doc**: `docs/enhancements/006-simple-api-configuration.md`

#### Testing Configuration

```bash
# Run configuration unit tests
cd backend
uv run pytest app/tests/unit/test_api_config.py -v

# Test with custom config file
GENE_CURATOR_API__PAGINATION__DEFAULT_PAGE_SIZE=25 uv run pytest

# Reload configuration in tests (clears cache)
from app.core.api_config import reload_config
config = reload_config()
```

**Key Architectural Decision**: This configuration system handles **API-level settings only**. Workflow, schema, and methodology configuration belongs in the **schema repository** (database). This maintains Gene Curator's schema-agnostic design.

### Package Management
- **Backend**: Use `uv` (modern Python package manager) - faster than pip/poetry
- **Frontend**: Use `npm` (standard Node.js package manager)
- **Docker**: Use volumes for dependency caching

## Common Development Tasks

### Adding a New API Endpoint
1. Create endpoint file in `backend/app/api/v1/endpoints/`
2. Define Pydantic schemas in `backend/app/schemas/`
3. Implement CRUD operations in `backend/app/crud/`
4. Register router in `backend/app/api/v1/api.py`
5. Add tests in `backend/app/tests/`

### Creating a New Frontend View
1. Create view component in `frontend/src/views/`
2. Create/update Pinia store in `frontend/src/stores/`
3. Add route in `frontend/src/router/index.js`
4. Add navigation in appropriate layout component
5. Test with authentication and permissions

### Database Schema Changes
1. Modify SQL files in `database/sql/`
2. Update SQLAlchemy models in `backend/app/models/models.py`
3. Update Pydantic schemas in `backend/app/schemas/`
4. Run `make db-reset` to apply changes
5. Update seed data if needed in `004_seed_data.sql`

### Testing Workflow
```bash
# Backend tests
cd backend
uv run pytest                  # All tests
uv run pytest app/tests/unit/  # Unit tests only
uv run pytest -k test_name     # Specific test
uv run pytest --cov=app        # With coverage

# Frontend tests (when implemented)
cd frontend
npm run test                   # Run tests
npm run test:unit              # Unit tests
```

## Deployment

### Development Deployment (Hybrid Mode - RECOMMENDED)
```bash
git clone https://github.com/halbritter-lab/gene-curator.git
cd gene-curator

# Start hybrid development environment
make hybrid-up                 # Start DB in Docker

# In separate terminals:
make backend                   # Terminal 1: Backend API
make frontend                  # Terminal 2: Frontend

# Access points:
# - Frontend: http://localhost:5193
# - API Docs: http://localhost:8051/docs
# - Database: localhost:5454
# - Default credentials: admin@gene-curator.dev / admin123
```

### Development Deployment (Full Docker)
```bash
git clone https://github.com/halbritter-lab/gene-curator.git
cd gene-curator
make dev                       # Start all services in Docker
# Access: http://localhost:3051
# API Docs: http://localhost:8051/docs
# Default credentials: admin@gene-curator.dev / admin123
```

### Production Deployment
```bash
# Build production images
docker compose build

# Start production services
docker compose up -d

# Check health
make health

# View logs
docker compose logs -f

# Check status
make status
```

### Environment Variables (Production)
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret (generate secure random key)
- `ALGORITHM`: JWT algorithm (HS256)
- `ENVIRONMENT`: production
- `ALLOWED_ORIGINS`: Frontend URLs for CORS

## Key Resources

### Documentation
- **API Documentation**: http://localhost:8001/docs (development)
- **Schema Specifications**: `plan/SCHEMA_SPECIFICATIONS.md`
- **Scoring Engine Guide**: `plan/SCORING_ENGINE_GUIDE.md`
- **Architecture Plan**: `PLAN.md`

### Development Tools
- **Backend Package Manager**: [uv](https://docs.astral.sh/uv/) - modern, fast
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Frontend Framework**: [Vue 3](https://vuejs.org/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **UI Framework**: [Vuetify](https://vuetifyjs.com/)
- **State Management**: [Pinia](https://pinia.vuejs.org/)

### Sample Data (Development)
- **Admin**: admin@gene-curator.dev / admin123
- **Curator**: curator@gene-curator.dev / curator123
- **Viewer**: viewer@gene-curator.dev / viewer123
- **Sample Genes**: Multiple HGNC-compliant genes with metadata
- **Sample Scopes**: kidney-genetics, cardio-genetics, neuro-genetics

## Scientific Background

### ClinGen SOP v11 Support
Gene Curator implements automated ClinGen Standard Operating Procedures v11:
- Genetic evidence scoring (case-level, segregation, case-control)
- Experimental evidence scoring (functional, model organisms, rescue)
- Automated verdict classification (Definitive, Strong, Moderate, Limited, etc.)
- Evidence summary generation following ClinGen templates

### GenCC Classification Support
Gene Curator supports GenCC (Gene Curation Coalition) classification:
- Definitive, Strong, Moderate, Limited, Disputed, Refuted evidence levels
- Systematic evidence collection and evaluation
- Standardized reporting format

### Custom Institutional Methodologies
Gene Curator accommodates any institution-specific approach:
- Define custom evidence fields via schema
- Implement custom scoring logic via plugin
- Configure custom workflow states
- Adapt UI dynamically to methodology

---

**Gene Curator** - Methodology-agnostic platform for genetic curation across all clinical specialties.
