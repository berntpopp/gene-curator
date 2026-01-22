# Codebase Structure

**Analysis Date:** 2026-01-22

## Directory Layout

```
gene-curator/
├── backend/                    # FastAPI backend (Python)
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── endpoints/      # 18 API endpoint modules
│   │   ├── crud/               # Database operations + workflow engine
│   │   ├── models/             # SQLAlchemy ORM definitions
│   │   ├── schemas/            # Pydantic request/response
│   │   ├── services/           # Business logic, permissions, scoring
│   │   ├── scoring/            # ClinGen, GenCC, Qualitative engines
│   │   ├── core/               # Config, security, logging, database
│   │   ├── middleware/         # Logging middleware
│   │   ├── tests/              # Unit, integration, security tests
│   │   └── main.py             # FastAPI app entry point
│   ├── config/                 # YAML-based API configuration
│   │   └── api.yaml            # CORS, rate limits, feature flags
│   ├── pyproject.toml          # Dependencies (uv)
│   └── pytest.ini              # Test configuration
│
├── frontend/                   # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── views/              # 30+ full-page components
│   │   ├── components/         # 66+ reusable UI components
│   │   ├── stores/             # 20 Pinia state stores
│   │   ├── router/             # Vue Router configuration
│   │   ├── api/                # API client modules
│   │   ├── services/           # Business logic (logService, etc.)
│   │   ├── composables/        # Vue 3 composition API helpers
│   │   ├── utils/              # Utilities (sanitizers, validators)
│   │   ├── types/              # TypeScript definitions
│   │   ├── config/             # Navigation, constants
│   │   ├── plugins/            # Logger, error handler
│   │   ├── test/               # Test utilities
│   │   ├── main.js             # Entry point
│   │   └── App.vue             # Root component
│   ├── package.json            # Dependencies (npm)
│   ├── vite.config.js          # Vite build config
│   └── vitest.config.js        # Unit test config
│
├── database/                   # PostgreSQL schema
│   ├── sql/
│   │   ├── 001-010/            # Core tables (users, scopes, genes)
│   │   ├── 011-020/            # Workflow, schemas, evidence
│   │   ├── 021-030/            # Triggers, views, migrations
│   │   └── *.sql               # Seed data
│   └── init.sh                 # Database initialization script
│
├── docs/                       # User-facing documentation
│   ├── API_REFERENCE.md        # API endpoint documentation
│   ├── SETUP.md                # Installation & configuration
│   ├── CLINGEN_SOP.md          # ClinGen SOP v11 methodology
│   ├── SCHEMA_AGNOSTIC.md      # Schema-agnostic design explanation
│   └── *.md                    # Other feature docs
│
├── plan/                       # Planning & tracking (NOT code)
│   ├── enhancements/           # Feature proposals
│   ├── refactoring/            # Technical debt solutions
│   ├── ISSUE_ROADMAP.md        # Issue tracking and priorities
│   └── *.md                    # Planning documents
│
├── .planning/codebase/         # GSD codebase analysis (this file + ARCHITECTURE.md, CONVENTIONS.md, etc.)
│
├── .github/                    # GitHub Actions CI/CD
│   └── workflows/
│       ├── backend-tests.yml   # Backend test pipeline
│       ├── frontend-tests.yml  # Frontend test pipeline
│       └── deploy.yml          # Deployment automation
│
├── .env.dev                    # Development environment config (NOT committed)
├── .env.example                # Example env template
├── Makefile                    # 50+ development commands
├── CLAUDE.md                   # AI development guide
├── CONTRIBUTING.md             # Developer onboarding
└── README.md                   # Project overview
```

## Directory Purposes

**`backend/app/`:**
- Purpose: Core Python application code
- Contains: All backend logic, ORM models, API endpoints
- Key files: `main.py` (entry point), `models/models.py` (database models)

**`backend/app/api/v1/endpoints/`:**
- Purpose: REST endpoint definitions
- Contains: 18 modules handling HTTP requests/responses
- Key files: `auth.py`, `scopes.py`, `genes.py`, `curations.py`, `workflow.py`, `schema_validation.py`
- Pattern: Each file = one domain resource (e.g., `curations.py` handles POST/GET/PUT /curations)

**`backend/app/crud/`:**
- Purpose: Direct database operations and business logic
- Contains: CRUD base class + specialized modules
- Key files: `base.py` (generic CRUD), `workflow_engine.py` (state machine), `curation.py`, `precuration.py`, `gene_assignment.py`
- Pattern: One file per model, with specialized query methods beyond basic CRUD

**`backend/app/models/`:**
- Purpose: SQLAlchemy ORM definitions
- Contains: `models.py` (all model definitions), enums
- Key classes: `Scope`, `Gene`, `GeneAssignment`, `CurationNew`, `PrecurationNew`, `Review`, `UserNew`, `ScopeMembership`, `CurationSchema`
- Pattern: Modern SQLAlchemy 2.0 with `Mapped[]` type hints and custom type aliases

**`backend/app/schemas/`:**
- Purpose: Pydantic request/response validation
- Contains: Request schemas (for creating/updating), response schemas (for returning data)
- Key files: `auth.py`, `curation.py`, `gene.py`, `gene_assignment.py`, `scope.py`, `validation.py`, `workflow_engine.py`
- Pattern: InDBBase - base class with common fields, separate Create/Update/Response classes

**`backend/app/services/`:**
- Purpose: Business logic, validation, permissions, external integrations
- Contains: Permission checks, scoring engines, ontology lookups
- Key files: `scope_permissions.py` (RBAC), `validation_service.py`, `gene_summary_service.py`, `ontology_service.py`, `publication_service.py`
- Subdirectory: `validators/` (ClinGen, GenCC, Qualitative scoring implementations)

**`backend/app/core/`:**
- Purpose: Infrastructure, configuration, shared utilities
- Contains: Config, security, logging, database setup, schema validation
- Key files:
  - `config.py`: Environment variables
  - `constants.py`: Immutable values
  - `api_config.py`: YAML-driven feature configuration
  - `database.py`: SQLAlchemy setup, session management
  - `deps.py`: FastAPI dependency injection (auth, scope, permissions)
  - `schema_validator.py`: Dynamic JSON schema validation engine
  - `logging/`: Unified logging system with request correlation

**`backend/app/tests/`:**
- Purpose: Test suites
- Contains: Unit tests, integration tests, security tests
- Subdirectories:
  - `unit/`: Isolated component tests (auth, enums, validators)
  - `integration/`: Full API tests with database
  - `security/`: Permission and RLS policy tests

**`backend/config/`:**
- Purpose: YAML-based configuration
- Contains: `api.yaml` with CORS, rate limits, feature flags
- Pattern: Loaded at startup, environment variable overrides supported

**`frontend/src/views/`:**
- Purpose: Full-page components (Vue Router pages)
- Contains: 30+ views for different workflows
- Key files:
  - `Login.vue`, `Register.vue`: Auth flow
  - `Dashboard.vue`: User dashboard
  - `scope/ScopeDashboard.vue`: Scope-specific workspace
  - `curation/CurationFormView.vue`, `PrecurationFormView.vue`: Workflow forms
  - `curation/ReviewQueueView.vue`: Peer review interface
  - `GeneCatalogueView.vue`: Gene browse/search
  - `SchemaManagement.vue`: Admin schema editor
  - `UserManagement.vue`: Admin user control

**`frontend/src/components/`:**
- Purpose: Reusable UI components
- Contains: 66+ Vue components organized by feature
- Subdirectories:
  - `common/`: Generic components (AppBar, FooterBar, ErrorBoundary, EmptyState)
  - `forms/`: Form-related (ValidatedInput, DynamicFormComponent)
  - `dialogs/`: Modal dialogs
  - `navigation/`: Menu, breadcrumb components
  - `curation/`: Curation workflow components
  - `evidence/`: Evidence item inputs (PMIDInput, HPOInput, MONDOAutocomplete)
  - `clingen/`: ClinGen-specific components
  - `scope/`: Scope management components
  - `gene/`: Gene display components
  - `logging/`: Log viewer component

**`frontend/src/stores/`:**
- Purpose: Pinia state management
- Contains: 20 stores following Pinia pattern
- Key stores:
  - `auth.js`: User login, token, permissions
  - `scopes.js`: User's scopes, current scope selection
  - `curations.js`: Curation list, current curation, draft state
  - `precurations.js`: Similar for precurations
  - `genes.js`: Gene catalog state
  - `workflow.js`: Workflow state transitions
  - `validation.js`: Validation rules state
  - `schemas.js`: Available schemas
  - `notifications.js`: Toast notifications
  - `logStore.js`: In-memory log entries

**`frontend/src/api/`:**
- Purpose: API client modules (Axios wrappers)
- Contains: API functions grouped by resource
- Key files: `client.js` (axios setup), `auth.js`, `curations.js`, `genes.js`, `scopes.js`
- Pattern: Each module exports functions that call backend endpoints

**`frontend/src/services/`:**
- Purpose: Business logic, utilities
- Contains: `logService.js` (logging), `scopeService.js` (scope helpers)

**`frontend/src/composables/`:**
- Purpose: Vue 3 Composition API helpers
- Contains: Reusable logic extracted from components
- Pattern: Prefix with `use` (e.g., `useLogger`, `useNotification`)

**`frontend/src/utils/`:**
- Purpose: Pure utility functions
- Contains: Validators, sanitizers, UUID polyfill, string formatters
- Key files: `schemaValidator.ts`, `logSanitizer.ts`, `uuidPolyfill.ts`

**`database/sql/`:**
- Purpose: PostgreSQL schema and migrations
- Contains: 25+ SQL files defining tables, indexes, triggers, seed data
- Numbering: 001-010 (core), 011-020 (workflow), 021-030 (migrations)
- Seed files: `006_test_user_setup.sql`, `014_seed_clingen_schema.sql`

**`docs/`:**
- Purpose: User and developer documentation
- Contains: API references, setup guides, methodology explanations
- Key files: `API_REFERENCE.md`, `SETUP.md`, `CLINGEN_SOP.md`, `SCHEMA_AGNOSTIC.md`

**`plan/`:**
- Purpose: Planning and tracking (NOT production code)
- Contains: Enhancement proposals, refactoring plans, roadmaps
- Key files: `ISSUE_ROADMAP.md`, `enhancements/*.md`, `refactoring/*.md`

## Key File Locations

**Entry Points:**
- Backend API: `backend/app/main.py` (FastAPI app, starts on port 8051)
- Frontend SPA: `frontend/src/main.js` (Vue 3, starts on port 5193)
- Database init: `database/sql/` (25+ migration files)

**Configuration:**
- `.env.dev`: All environment variables
- `backend/config/api.yaml`: API-specific config (CORS, feature flags)
- `frontend/.env.local`: Frontend env vars (API URL, app title)
- `Makefile`: 50+ development commands

**Core Logic:**
- Workflow: `backend/app/crud/workflow_engine.py` (state machine)
- Validation: `backend/app/core/schema_validator.py` (dynamic schema validation)
- Permissions: `backend/app/services/scope_permissions.py` (RBAC enforcement)
- Scoring: `backend/app/scoring/` (ClinGen, GenCC, Qualitative implementations)

**Testing:**
- Backend: `backend/app/tests/` (unit, integration, security tests)
- Frontend: `frontend/src/**/__tests__/` (co-located test files)
- Test commands: `make test`, `make lint`, `make test-integration`

## Naming Conventions

**Files:**
- Backend Python: `snake_case.py` (e.g., `workflow_engine.py`, `scope_permissions.py`)
- Frontend Vue: `PascalCase.vue` (e.g., `CurationFormView.vue`, `GeneDetail.vue`)
- Frontend JS: `camelCase.js` or `camelCase.ts` (e.g., `logService.js`, `useLogger.ts`)
- SQL migrations: `NNN_description_here.sql` (e.g., `001_create_users.sql`, `014_seed_clingen_schema.sql`)

**Directories:**
- Backend: `snake_case/` (e.g., `app/api/v1/endpoints/`, `app/services/validators/`)
- Frontend: `lowercase/` (e.g., `src/views/curation/`, `src/components/evidence/`)
- Feature modules: Named for domain (e.g., `curation/`, `scope/`, `gene/`)

**Database:**
- Tables: `snake_case` with semantic suffixes (e.g., `curation_new`, `scope_membership`, `gene_assignment`)
- Columns: `snake_case` (e.g., `lock_version`, `workflow_stage`)
- Enums: `UPPERCASE` (e.g., `PENDING`, `APPROVED`, `DRAFT`)

## Where to Add New Code

**New API Feature (e.g., new curation endpoint):**
- **Endpoint**: `backend/app/api/v1/endpoints/curations.py` (add route + handler)
- **CRUD**: `backend/app/crud/curation.py` (add specialized query method)
- **Schema**: `backend/app/schemas/curation.py` (add Pydantic request/response class)
- **Model**: `backend/app/models/models.py` (if new table needed)
- **Tests**: `backend/app/tests/integration/test_*.py` (add endpoint test)

**New Pinia Store (e.g., new frontend state):**
- **Store**: `frontend/src/stores/myfeature.js` (define state, getters, actions)
- **API module**: `frontend/src/api/myfeature.js` (wrap backend calls)
- **Component**: `frontend/src/views/MyFeatureView.vue` (use store via `useMyFeatureStore()`)

**New Component (e.g., new form field):**
- **Component**: `frontend/src/components/forms/MyField.vue` (define template, script, style)
- **Tests**: `frontend/src/components/forms/__tests__/MyField.spec.js` (co-located test)
- **Export**: Register in parent component or add to `components/forms/index.js`

**New Validation Rule:**
- **Backend**: `backend/app/core/schema_validator.py` (add rule to `_validate_field()` method)
- **Frontend**: `frontend/src/utils/schemaValidator.ts` (mirror rule for client-side validation)
- **Tests**: `backend/app/tests/unit/test_schema_validators.py` (add test case)

**New Scoring Engine:**
- **Implementation**: `backend/app/scoring/my_engine.py` (extend `BaseScoringEngine`)
- **Service**: `backend/app/services/validators/my_validator.py` (wrap for CRUD use)
- **Schema**: Add new field type to `curation_schemas` table
- **Tests**: `backend/app/tests/unit/test_my_validator.py`

**New Service/Utility:**
- **Backend service**: `backend/app/services/my_service.py` (stateless business logic)
- **Frontend service**: `frontend/src/services/myService.js` (client-side utility)
- **Composable**: `frontend/src/composables/useMyFeature.ts` (Vue 3 logic hooks)

**Database Migration:**
- **Create SQL file**: `database/sql/NNN_description.sql` (sequential numbering)
- **Follow patterns**: Use existing files as templates (constraints, indexes, triggers)
- **Run locally**: `make db-init` includes migration

## Special Directories

**`backend/app/core/logging/`:**
- Purpose: Unified logging system
- Generated: No (source code)
- Committed: Yes
- Contains: `__init__.py` (setup), logger classes, formatters, handlers
- Used by: All backend modules via `get_logger(__name__)`

**`frontend/src/test/`:**
- Purpose: Shared test utilities and fixtures
- Generated: No
- Committed: Yes
- Contains: Test setup, mocks, factories

**`backend/app/tests/fixtures/`:**
- Purpose: Pytest fixtures for database state
- Generated: No
- Committed: Yes
- Contains: Fixture definitions for users, scopes, genes, curations

**`node_modules/` and `__pycache__/`:**
- Purpose: Dependency caches (NOT committed)
- Generated: Yes (by `npm install` or `uv sync`)
- Committed: No (in `.gitignore`)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md

---

*Structure analysis: 2026-01-22*
