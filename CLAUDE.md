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

### Docker-Based Development (Recommended)
```bash
# Primary Commands
make dev           # Start full stack (backend:8001, frontend:3001, db:5433)
make dev-build     # Rebuild and start
make dev-down      # Stop environment
make dev-logs      # View logs

# Database
make db-init       # Initialize database
make db-reset      # Reset database (destructive)
make db-shell      # PostgreSQL shell

# Testing & Quality
make test          # Run all tests
make test-backend  # Backend tests only
make test-frontend # Frontend tests only
make lint          # Backend linting (ruff, mypy, bandit)
make format        # Backend formatting

# Utilities
make health        # Check service health
make status        # Container status
make clean         # Clean Docker resources
make backend-shell # Backend container shell
```

### Backend Commands (Direct - in backend/)
```bash
# Development
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

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
npm run dev        # Vite dev server (http://localhost:5173)
npm run build      # Production build
npm run preview    # Preview production build

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

**Backend (.env in backend/)**:
```bash
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5433/gene_curator_dev
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
LOG_LEVEL=debug
ALLOWED_ORIGINS=["http://localhost:3001", "http://localhost:5173"]
```

**Frontend (.env.local in frontend/)**:
```bash
VITE_API_BASE_URL=http://localhost:8001
VITE_APP_TITLE=Gene Curator
VITE_ENVIRONMENT=development
```

### Docker Configuration

**Development Environment**:
- **Backend**: http://localhost:8001 (internal port 8000)
- **Frontend**: http://localhost:3001 (internal port 3000)
- **Database**: localhost:5433 (PostgreSQL 15)
- **API Docs**: http://localhost:8001/docs (Swagger)
- **Credentials**: dev_user / dev_password / gene_curator_dev

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

### Development Deployment
```bash
git clone https://github.com/halbritter-lab/gene-curator.git
cd gene-curator
make dev                       # Start all services
# Access: http://localhost:3001
# API Docs: http://localhost:8001/docs
# Default credentials: admin@gene-curator.dev / admin123
```

### Production Deployment
```bash
# Build production images
docker-compose build

# Start production services
docker-compose up -d

# Check health
curl http://localhost:8001/health

# View logs
docker-compose logs -f
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
