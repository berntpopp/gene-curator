# Architecture

**Analysis Date:** 2026-01-22

## Pattern Overview

**Overall:** Layered n-tier architecture with schema-agnostic domain design, scope-based multi-tenancy, and multi-stage workflow orchestration.

**Key Characteristics:**
- **Schema-agnostic foundation**: Clinically flexible curation through configurable schemas stored in database rather than code
- **Scope-based organization**: Clinical specialties (kidney-genetics, cardio-genetics, etc.) as first-class entities with many-to-many gene assignments
- **Multi-stage workflow**: 5-stage pipeline (Entry → Precuration → Curation → Review → Active) with mandatory 4-eyes peer review principle
- **Role-based access control (RBAC)**: 5 roles (admin, scope_admin, curator, reviewer, viewer) with scope-specific role assignment via `scope_memberships`
- **Pluggable scoring engines**: ClinGen SOP v11, GenCC, Qualitative, and Registry methodologies as interchangeable components

## Layers

**Presentation Layer (Frontend):**
- Purpose: Vue 3 SPA providing real-time schema-driven UI
- Location: `frontend/src/`
- Contains: Views, components, stores (Pinia), API client, plugins, utilities
- Depends on: Backend REST API (`http://localhost:8051/api/v1`)
- Used by: End users (admins, curators, reviewers, viewers)

**API Layer (Backend):**
- Purpose: RESTful endpoint dispatch and request/response transformation
- Location: `backend/app/api/v1/endpoints/`
- Contains: 18 endpoint modules (auth, scopes, schemas, genes, curations, precurations, workflow, evidence, etc.)
- Depends on: CRUD layer, services, dependencies (auth, permissions, logging)
- Used by: Frontend SPA via HTTP

**Domain/Service Layer (Backend):**
- Purpose: Business logic, workflow orchestration, validation, permission enforcement
- Location: `backend/app/crud/`, `backend/app/services/`
- Contains:
  - CRUD operations: `workflow_engine.py`, `curation.py`, `precuration.py`, `gene.py`, `gene_assignment.py`, `scope.py`, `scope_membership.py`, `gene_catalogue.py`
  - Services: `scope_permissions.py`, `validation_service.py`, `gene_summary_service.py`, `ontology_service.py`, `publication_service.py`
  - Validators: ClinGen, GenCC, Qualitative scoring engines
- Depends on: Models, core utilities, database
- Used by: API endpoints

**Data Access Layer (CRUD):**
- Purpose: Direct database interaction with business rule enforcement
- Location: `backend/app/crud/`
- Base class: `CRUDBase` in `base.py` (generic with Create, Read, Update, Delete patterns)
- Pattern: Each CRUD module specialized for its model (e.g., `curation_crud`, `workflow_engine` for multi-stage management)
- Depends on: SQLAlchemy models, database session
- Used by: Endpoints and service layer

**Core/Infrastructure Layer (Backend):**
- Purpose: Configuration, security, logging, database connectivity, schema validation
- Location: `backend/app/core/`
- Contains:
  - `config.py`: Environment-based settings from `.env.dev`
  - `constants.py`: Immutable values (page sizes, HTTP codes, ClinGen SOP versions)
  - `api_config.py`: YAML-driven configuration (CORS, rate limits, feature flags)
  - `database.py`: SQLAlchemy engine, session management, modern declarative base
  - `security.py`: JWT token verification, credential exceptions
  - `deps.py`: FastAPI dependencies (authentication, user extraction, scope injection)
  - `schema_validator.py`: Dynamic JSON schema validation engine for curation fields
  - `logging/`: Unified logging with request correlation, performance tracking, DB persistence
- Depends on: External libraries (SQLAlchemy, Pydantic, FastAPI)
- Used by: All other layers

**Data Models (Database):**
- Purpose: SQLAlchemy ORM definitions with strong typing
- Location: `backend/app/models/models.py`
- Pattern: Modern SQLAlchemy 2.0 with `Mapped[]` type annotations and custom type aliases
- Key entities: `Scope`, `Gene`, `GeneAssignment`, `PrecurationNew`, `CurationNew`, `Review`, `ActiveCuration`, `UserNew`, `ScopeMembership`, `CurationSchema`, `Invitation`
- Database: PostgreSQL 15+ with full-text search, JSONB fields, UUID primary keys

**API Schemas (Pydantic):**
- Purpose: Request/response validation and serialization
- Location: `backend/app/schemas/`
- Pattern: InDBBase pattern - base schemas shared, request/response variants split
- Categories: `auth.py`, `curation.py`, `precuration.py`, `gene.py`, `gene_assignment.py`, `scope.py`, `workflow_engine.py`, `validation.py`, `scoring.py`, etc.
- Depends on: Pydantic V2 with `ConfigDict`, FastAPI integration

## Data Flow

**Curation Creation & Workflow Transition Flow:**

1. **Entry Point**: User accesses `CurationFormView` (frontend) → Calls `POST /api/v1/curations`
2. **API Endpoint** (`curations.py`):
   - Validates request schema (Pydantic)
   - Checks user scope membership & permissions via `ScopePermissionService`
   - Calls `curation_crud.create()`
3. **CRUD Layer** (`curation.py`):
   - Creates `CurationNew` record in `curation_new` table
   - Initializes with `workflow_stage=WorkflowStage.ENTRY`
   - Calls `workflow_engine.validate_transition()` to enforce state machine
   - Commits to database
4. **Workflow Engine** (`workflow_engine.py`):
   - Validates transition legality (e.g., ENTRY → PRECURATION only)
   - Checks peer-review requirements (4-eyes principle for REVIEW → ACTIVE)
   - Updates stage and audit trail
   - Raises `WorkflowValidationResult` on constraint violation
5. **Response**: JSON with `CurationResponse` schema back to frontend
6. **Frontend Store** (`stores/curations.js`):
   - Updates state via `fetchCurations()` action
   - Manages optimistic locking via `lock_version` field
   - Handles conflict errors for concurrent edits

**Gene Assignment & Scope Association:**

1. User creates assignment: `POST /api/v1/gene-assignments`
2. API validates scope membership and gene existence
3. CRUD creates many-to-many link in `gene_assignments` table with `scope_id` + `gene_id`
4. Generates `workflow_pair` (parent container for precuration/curation pair)
5. Scope-based filtering ensures users only see assigned genes in their scopes

**Schema-Driven Form Validation:**

1. Frontend fetches schema: `GET /api/v1/schemas/{schema_id}`
2. Response includes field definitions (type, validation rules, UI hints)
3. Frontend dynamically renders form with `DynamicFormComponent`
4. On submit, validation runs client-side using `schema_validator.ts` rules
5. Server-side validation repeats in `CurationUpdate` endpoint using `schema_validator.py`
6. Non-conforming data rejected with `ValidationErrorResponse`

**State Management:**

- **Frontend**: Pinia stores (auth, scopes, curations, precurations, genes, users, workflow, validation, notifications, disclaimer)
- **Backend**: SQLAlchemy ORM state + database transactions
- **Shared**: JWT token in `localStorage`, correlation IDs in headers for request tracing

## Key Abstractions

**WorkflowEngine:**
- Purpose: Multi-stage state machine with business rule enforcement
- Examples: `backend/app/crud/workflow_engine.py`
- Pattern: Singleton-like (instantiated once, called from endpoints)
- Methods: `validate_transition()`, `transition_to_stage()`, `get_workflow_state()`, `submit_for_review()`, `approve_review()`, `get_statistics()`
- Enforces: Valid transitions, 4-eyes peer review, one-active-per-gene-scope rule

**ScopePermissionService:**
- Purpose: Check user authorization for scope-specific operations
- Examples: `backend/app/services/scope_permissions.py`
- Pattern: Injected via dependency, queried before CRUD operations
- Methods: `has_scope_role()`, `can_assign_gene()`, `can_create_curation()`, `get_user_scope_roles()`
- Depends on: `ScopeMembership` model with role field

**SchemaValidator:**
- Purpose: Dynamic field validation from `CurationSchema` records
- Examples: `backend/app/core/schema_validator.py`, `frontend/src/utils/schemaValidator.ts`
- Pattern: Reads schema definitions from database, applies rules to evidence data
- Supported field types: text, number, select, multiselect, date, file, checkbox, textarea, rich-text, custom-enum
- Returns: `ValidationErrorResponse` with field paths and rule violations

**GeneAssignmentRepository:**
- Purpose: Query complex gene-scope relationships
- Examples: `backend/app/crud/gene_assignment.py`, `backend/app/crud/gene_catalogue.py`
- Pattern: Specialized query methods beyond basic CRUD
- Methods: `get_genes_for_scope()`, `get_active_curations_for_gene()`, `get_precuration_count()`, `merge_genes()`

## Entry Points

**Backend Startup:**
- Location: `backend/app/main.py`
- Triggers: `make backend` or `cd backend && uv run uvicorn app.main:app --reload --port 8051`
- Responsibilities:
  - Creates FastAPI app with title, version, description
  - Loads CORS config from `config/api.yaml`
  - Adds middlewares (CORS, logging)
  - Registers API router at `/api/v1`
  - Starts logging system, health checks
  - Listens on `0.0.0.0:8051`

**Frontend Startup:**
- Location: `frontend/src/main.js`
- Triggers: `make frontend` or `cd frontend && npm run dev -- --port 5193`
- Responsibilities:
  - Creates Vue 3 app instance
  - Initializes Pinia store
  - Sets up Vuetify theme
  - Registers logger plugin and error handler
  - Initializes Vue Router with lazy-loaded components
  - Mounts to `#app` div
  - Listens on `localhost:5193`

**API Router:**
- Location: `backend/app/api/v1/api.py`
- Includes 18 endpoint modules, organized by domain:
  - Auth: login, register, token refresh
  - Scopes: CRUD, member management, invitations
  - Schemas: schema CRUD, field definitions, validation config
  - Genes: gene catalog, search, statistics
  - Gene Assignments: scope-gene relationships, workflow pairs
  - Curations & Precurations: full workflow lifecycle
  - Workflow: state transitions, review queue, peer review
  - Evidence: ClinGen evidence items
  - External: ontology, publications, validation

## Error Handling

**Strategy:** Layered exception handling with context preservation and request correlation

**Patterns:**

1. **API Level** (`endpoints/*.py`):
   - Catches domain exceptions, converts to `HTTPException` with status code
   - `HTTPException(status_code=409, detail="Curation locked by another user")` for conflicts
   - Uses `api_endpoint()` decorator for auto-logging

2. **Service Level** (`services/*.py`, `crud/*.py`):
   - Raises domain-specific exceptions: `WorkflowValidationResult`, `PermissionError`, `ValidationError`
   - Logs with context: `logger.error("Conflict detected", error=e, curation_id=id, lock_version=v)`

3. **Global Exception Handler** (`main.py`):
   - Catches unhandled exceptions, returns JSON with request_id for support tracing
   - Logs to database for 90-day retention

4. **Frontend Error Handling**:
   - Axios interceptor catches network errors, logs with correlation ID
   - Pinia store error state: `error = { message, isConflict, code }`
   - UI shows snackbar notifications from `notificationStore`

## Cross-Cutting Concerns

**Logging:** Unified system with backend (`app.core.logging`) and frontend (`composables/useLogger`)
- Backend: Request correlation IDs, performance tracking (ms), auto-sanitization of PII
- Frontend: User actions, component lifecycle, API calls with response time
- Persistence: 90-day retention in `log_entries` table
- Viewer: `Ctrl+L` / `Cmd+L` opens real-time log viewer

**Validation:** Three-layer system
- **Client**: Real-time as user types (Pinia validators)
- **API Request**: Pydantic schema validation
- **Business Logic**: `schema_validator.py` enforces ClinGen/GenCC rules

**Authentication:** JWT-based with scope-specific role claims
- Token issued by `auth.py` endpoint
- Stored in `localStorage` on frontend
- Verified in `deps.get_current_user()` dependency
- Scope roles injected via `deps_scope.py`

**Authorization:** Two-layer enforcement
- **Scope-level**: `ScopePermissionService` checks user has role in scope
- **Data-level**: CRUD queries filtered by user's accessible scopes
- Special case: Admins bypass scope checks

**Database Transactions:**
- Session-per-request pattern via `get_db()` dependency
- Auto-commit on success, rollback on exception
- Optimistic locking via `lock_version` field for concurrent curation edits
- Conflict detection and retry logic in frontend store

---

*Architecture analysis: 2026-01-22*
