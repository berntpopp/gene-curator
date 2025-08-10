# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Gene Curator Project Overview

Gene Curator is a **dual-architecture** genetic curation platform that combines a **production ClinGen SOP v11 system** with a **fully implemented schema-agnostic, methodology-agnostic architecture**. The platform supports both fixed ClinGen workflows and flexible, configurable curation methodologies through a sophisticated three-tier architecture with PostgreSQL, FastAPI, and Vue 3.

### Current Implementation Status (As of January 2025)
- **Backend**: FastAPI with dual system support - ClinGen SOP v11 + Schema-agnostic architecture
- **Frontend**: Vue 3 + Vite + Pinia with both ClinGen-specific and dynamic components  
- **Database**: PostgreSQL with both fixed ClinGen schema AND flexible schema-agnostic tables
- **Authentication**: JWT-based with enhanced RBAC (viewer, curator, reviewer, admin, scope_admin)
- **Workflow**: Both legacy workflow AND multi-stage workflow with 4-eyes principle

### Architecture Status - Dual System Implementation
**🎯 LEGACY SYSTEM (ClinGen-Centric) - ✅ PRODUCTION READY**:
- **✅ Complete**: Three-tier architecture with ClinGen SOP v11 compliance
- **✅ Complete**: Vue 3 + Vite frontend with ClinGen-specific UI components
- **✅ Complete**: FastAPI backend with PostgreSQL database
- **✅ Complete**: JWT authentication with RBAC (3 roles)
- **✅ Complete**: Fixed ClinGen schema with workflow states
- **✅ Complete**: JSONB evidence storage in `details` columns
- **✅ Complete**: Basic workflow management with status transitions

**🚀 SCHEMA-AGNOSTIC SYSTEM - ✅ FULLY IMPLEMENTED**:
- **✅ Complete**: Schema-driven architecture supporting any methodology (ClinGen, GenCC, institutional)
- **✅ Complete**: Scope-based organization with clinical specialties
- **✅ Complete**: Multi-stage workflow with 4-eyes principle (5 stages: entry → precuration → curation → review → active)
- **✅ Complete**: Pluggable scoring engines registry (ClinGen, GenCC, Qualitative)
- **✅ Complete**: Dynamic schema validation engine with 12+ field types
- **✅ Complete**: Gene assignment system with curator workload management
- **✅ Complete**: Multi-curation support per gene-scope with active/archived status
- **🔄 Ready**: Dynamic UI generation capabilities (backend complete, frontend integration pending)

## Essential Commands

### Docker-Based Development (Recommended)
```bash
# Primary Development Commands
make dev           # Start full development environment (backend:8000, frontend:3001, db:5433)
make dev-build     # Build and start development environment
make dev-down      # Stop development environment
make dev-logs      # Show development logs

# Database Commands
make db-init       # Initialize database with schema
make db-reset      # Reset database (destructive)
make db-shell      # Open PostgreSQL shell

# Testing
make test          # Run all tests
make test-backend  # Run backend tests only
make test-frontend # Run frontend tests only

# Code Quality
make lint          # Run backend linting (ruff, mypy, bandit)
make format        # Format backend code with ruff

# Utilities
make health        # Check service health
make status        # Show Docker container status
make clean         # Clean up Docker resources
make backend-shell # Open backend container shell
```

### Schema-Agnostic System API Endpoints
```bash
# Scope Management (Clinical Specialties)
GET    /api/v1/scopes                     # List all scopes
POST   /api/v1/scopes                     # Create new scope  
GET    /api/v1/scopes/{scope_id}          # Get scope details
PUT    /api/v1/scopes/{scope_id}          # Update scope
DELETE /api/v1/scopes/{scope_id}          # Delete scope
GET    /api/v1/scopes/{scope_id}/statistics # Scope analytics

# Schema Repository (Methodology Management)
GET    /api/v1/schemas                    # List all schemas
POST   /api/v1/schemas                    # Create new schema
GET    /api/v1/schemas/{schema_id}        # Get schema definition
PUT    /api/v1/schemas/{schema_id}        # Update schema
DELETE /api/v1/schemas/{schema_id}        # Delete schema
GET    /api/v1/schemas/{schema_id}/usage-statistics # Schema usage

# Dynamic Validation
POST   /api/v1/validation/validate-evidence    # Validate evidence against schema
POST   /api/v1/validation/validate-schema      # Validate schema definition
GET    /api/v1/validation/generate-json-schema/{schema_id} # Generate JSON Schema for UI
GET    /api/v1/validation/supported-field-types # List supported field types

# Gene Assignment System
GET    /api/v1/gene-assignments                # List assignments
POST   /api/v1/gene-assignments/bulk          # Bulk assign genes to scopes
GET    /api/v1/gene-assignments/curator/{curator_id}/workload # Curator workload
PUT    /api/v1/gene-assignments/{assignment_id}/priority # Update priority

# Multi-Stage Workflow Engine
GET    /api/v1/workflow/analytics               # Workflow analytics
POST   /api/v1/workflow/curation/{curation_id}/transition # Transition workflow stage
GET    /api/v1/workflow/curation/{curation_id}/available-transitions # Available transitions
GET    /api/v1/workflow/peer-reviewers          # Available peer reviewers

# Enhanced Gene Management
GET    /api/v1/genes-new                       # List genes with assignment status
GET    /api/v1/genes-new/{gene_id}/assignments # Gene scope assignments
GET    /api/v1/genes-new/{gene_id}/curation-progress # Curation progress by scope
```

### Frontend Commands (Direct)
```bash
# Development (in frontend/ directory)
npm run dev        # Start Vite development server (http://localhost:5173)
npm run build      # Build for production (outputs to /dist)
npm run preview    # Preview production build

# Code Quality
npm run lint       # ESLint with auto-fix
npm run lint:check # ESLint check only (no fixes)
npm run format     # Prettier formatting
npm run format:check # Prettier check only (no formatting)
npm run test:lint  # Run comprehensive linting test suite
```

### Backend Commands (Direct)
```bash
# Development (in backend/ directory)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Code Quality
uv run python scripts/lint.py    # Run all linting checks
uv run python scripts/format.py  # Auto-format code
uv run ruff check                # Ruff linting only
uv run mypy app                   # Type checking only
uv run bandit -r app              # Security analysis only

# Testing
uv run pytest                    # Run pytest tests
uv run pytest --cov=app          # Run tests with coverage
```

## Architecture Overview

### Technology Stack

#### Dual-Architecture Implementation
- **Database**: PostgreSQL 15+ with dual schema support:
  - Fixed ClinGen schema (001-003.sql) for legacy system
  - Flexible schema-agnostic tables (004-007.sql) with JSONB evidence storage
- **Backend**: FastAPI + SQLAlchemy with uv package management:
  - Legacy ClinGen scoring engine for fixed workflows
  - **NEW**: Pluggable scoring engine registry (ClinGen, GenCC, Qualitative)
  - **NEW**: Dynamic schema validation engine with 12+ field types
  - **NEW**: Multi-stage workflow engine with 4-eyes principle
- **Frontend**: Vue 3.4.21 + Vite + Pinia:
  - ClinGen-specific UI components (legacy system)
  - **NEW**: Schema validation and dynamic form capabilities (backend ready)
- **UI Framework**: Vuetify 3.9.3 (Material Design)
- **Authentication**: JWT + FastAPI Security with **enhanced RBAC** (viewer, curator, reviewer, admin, scope_admin)
- **Build System**: Vite 5.2.8 (modern ESM-based builds)
- **State Management**: Pinia 2.1.7 with API integration for both systems
- **Standards Compliance**: 
  - Legacy: Automated ClinGen SOP v11 evidence scoring and summary generation
  - **NEW**: Multi-methodology support (ClinGen, GenCC, institutional approaches)

#### Legacy Architecture (Pre-Migration)
- **Frontend**: Vue.js 3.2.13 with Vue CLI Service 5.0.0
- **Backend**: Firebase 10.7.1 (Firestore + Authentication)
- **Build**: Vue CLI (deprecated, migrated to Vite)

### Core Architectural Patterns

#### 1. Dual Database Architecture
The implementation uses **two complementary database architectures**:

**Legacy ClinGen Schema (001-003.sql)**:
- **Fixed Tables**: `users`, `genes`, `precurations`, `curations`, `change_log`
- **ClinGen Enums**: Fixed verdict types, workflow statuses, precuration decisions
- **JSONB Storage**: Evidence details stored in `details` columns for flexibility
- **Workflow States**: 6 predefined states with role-based permissions
- **Audit Trail**: Complete change tracking with provenance hashing

**Schema-Agnostic Architecture (004-007.sql)**:
- **Core Tables**: `scopes`, `curation_schemas`, `workflow_pairs`, `gene_assignments`
- **Flexible Storage**: JSONB evidence storage with dynamic validation
- **Scope-Based**: Clinical specialty organization (kidney-genetics, cardio-genetics, etc.)
- **Multi-Stage Workflow**: 5-stage pipeline with 4-eyes principle
- **Enhanced RBAC**: Extended roles including scope_admin and reviewer
- **Multi-Methodology**: Support for any curation approach through schema definitions

#### 2. Store Pattern (frontend/src/stores/)
All stores follow a consistent pattern for API operations using Pinia:

```javascript
// Common store functions (API-based)
fetchItems()                            // Fetch all items via API
fetchItemById(id)                       // Fetch single item via API
createItem(data)                        // Create with API validation
updateItem(id, data)                    // Update with API validation
deleteItem(id)                          // Delete via API
workflowAction(id, action)              // Workflow state transitions
```

Key features:
- RESTful API integration with axios
- Pinia state management with composition API
- ClinGen-specific state (verdicts, scores, evidence)
- JWT token management and refresh
- Workflow state management and transitions
- Search and filtering capabilities

#### 3. Authentication & Authorization
- JWT-based authentication with FastAPI Security
- Three roles: `admin`, `curator`, `viewer`
- Backend RBAC enforcement via API middleware
- Frontend route guards check authentication and role requirements
- Token refresh and automatic logout on expiration

#### 4. Component Architecture
- **Configuration-driven UI**: Components dynamically render based on config objects (preserved)
- **Reusable components**: DataDisplayTable, HelpIcon, MessageSnackbar, ConfirmationModal
- **Form handling**: Dynamic field rendering with built-in validation
- **State management**: Pinia stores with Composition API, PostgreSQL as source of truth
- **ClinGen Components**: Specialized evidence entry, scoring display, and summary generation UI

### Key Directories

```
/frontend/src
  /components     # Reusable Vue components
    /clingen      # ClinGen-specific components (legacy system)
    /dynamic      # Schema-driven components (future UI integration)
  /views          # Page-level components
  /stores         # Pinia stores (API data layer) - supports both systems
  /router         # Route definitions and guards
  /api            # API client and axios configuration
  /types          # TypeScript type definitions
  /composables    # Vue composition functions
/backend/app
  /api/v1         # FastAPI route handlers (13+ endpoints)
    /endpoints    # Individual endpoint files
      gene_assignments.py    # Gene assignment API
      genes_new.py          # Enhanced gene management
      schema_validation.py  # Dynamic validation API
      schemas.py           # Schema repository API
      scopes.py            # Scope management API
      workflow.py          # Multi-stage workflow API
  /models         # SQLAlchemy database models
    database_models.py     # Legacy ClinGen models
    schema_agnostic_models.py # New schema-agnostic models
  /schemas        # Pydantic request/response schemas
  /core           # Application configuration and security
    schema_validator.py    # Dynamic validation engine ✅
  /crud           # Database CRUD operations
    gene_assignment.py     # Gene assignment CRUD
    schema_repository.py   # Schema management CRUD
    scope.py              # Scope management CRUD
    workflow_engine.py    # Multi-stage workflow engine
  /scoring        # Pluggable scoring engines ✅
    registry.py          # Scoring engine registry
    clingen.py          # ClinGen SOP v11 engine
    gencc.py            # GenCC classification engine
    qualitative.py      # Qualitative assessment engine
  /tests          # Comprehensive test suites ✅
    /integration         # Integration tests
/database/sql     # Database schema files
  001-003.sql     # Legacy ClinGen schema
  004-007.sql     # Schema-agnostic foundation ✅
```

### Data Flow

#### Dual System Architecture

**Legacy ClinGen System**:
```
Gene Entry → Precuration → Curation → Workflow States → Publication
    ↓           ↓            ↓            ↓              ↓
  genes/   precurations/ curations/  status_mgmt/   publishing/
```

**Schema-Agnostic System**:
```
Scope Selection → Gene Assignment → Multi-Stage Workflow → Publication
      ↓              ↓                      ↓               ↓
   scopes/    gene_assignments/    workflow_engine/    active_status/
                                        ↓
                    Entry → Precuration → Curation → Review → Active
                      ↓         ↓           ↓         ↓        ↓
                   drafts/  precurations/ curations/ reviews/ published/
```

**Schema-Agnostic Implementation**:
- **Scope Management**: Clinical specialty-based organization (kidney-genetics, cardio-genetics)
- **Gene Assignment**: Curator workload management with bulk operations
- **Multi-Stage Workflow**: 5-stage pipeline with 4-eyes principle
- **Dynamic Validation**: Schema-driven validation with pluggable scoring engines
- **Evidence Storage**: Flexible JSONB storage adapting to any methodology
- **API Integration**: 25+ RESTful endpoints for complete system management
- **Database Flexibility**: PostgreSQL enforces business rules while supporting any methodology

**Legacy Implementation**:
- **Gene Management**: HGNC-compliant gene entries with JSONB details
- **Precuration Stage**: Disease association with lumping/splitting decisions
- **Curation Stage**: ClinGen evidence collection with fixed scoring fields
- **Workflow Management**: 6-state workflow with role-based permissions
- **Evidence Storage**: JSONB details columns for flexible evidence structures
- **API Integration**: RESTful endpoints for all CRUD operations
- **Database Constraints**: PostgreSQL enforces ClinGen SOP v11 compliance

#### Legacy Firebase Architecture (Deprecated)
```
Gene Data → Precuration Stage → Curation Stage(s)
    ↓            ↓                    ↓
  genes/     precurations/       curations/
```

### Working with Configurations

#### Current Database Schema (Fixed ClinGen)
Implemented in `database/sql/001_initial_schema.sql`:

**Core Tables**:
- `users`: Authentication and RBAC (3 roles)
- `genes`: HGNC-compliant gene entries with JSONB details
- `precurations`: Disease association with lumping/splitting
- `curations`: ClinGen evidence collection with fixed scoring
- `change_log`: Complete audit trail with provenance

**Fixed Enums**:
- `curation_verdict`: ClinGen SOP v11 classifications
- `workflow_status`: 6-state workflow management
- `user_role`: viewer, curator, admin permissions
- `precuration_decision`: Lump, Split, Undecided

#### Current Implementation Status
**Backend Components (Implemented)**:
- `backend/app/models/database_models.py`: SQLAlchemy models for all entities
- `backend/app/api/v1/endpoints/`: REST API endpoints for CRUD operations
- `backend/app/schemas/`: Pydantic schemas for API validation
- `backend/app/core/`: Authentication, security, and database configuration

**Frontend Components (Implemented)**:
- `frontend/src/components/clingen/`: ClinGen-specific UI components
- `frontend/src/stores/`: Pinia stores for API integration
- `frontend/src/views/`: Page-level components for all workflows
- `frontend/src/api/`: Axios-based API client with authentication

### Environment Setup

#### Backend Environment
Create `backend/.env` with PostgreSQL and JWT configuration:
```
DATABASE_URL=postgresql://user:password@localhost:5432/gene_curator
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Frontend Environment
Create `frontend/.env.local` with API configuration:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=Gene Curator
VITE_ENABLE_MOCK_DATA=false
```

### Deployment

The application uses a three-tier deployment architecture:

#### Development
- Full Stack: `make dev` (Docker Compose with backend:8000, frontend:3001, db:5433)
- Backend Only: `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend Only: `npm run dev` (Vite dev server on :5173)
- Database: PostgreSQL via Docker or local instance

#### Production
- Backend: FastAPI with Uvicorn (containerized)
- Frontend: Static build served via CDN or web server
- Database: PostgreSQL with connection pooling
- Authentication: JWT tokens with refresh mechanism

## Current Implementation & Future Architecture Transformation

### Current ClinGen SOP v11 Implementation

The project currently implements ClinGen SOP v11 compliance with a fixed schema:

#### Current ClinGen Features
1. **Fixed Evidence Fields**: Predefined genetic and experimental evidence score fields
2. **Verdict Classification**: 7 ClinGen verdict types (Definitive, Strong, etc.)
3. **JSONB Evidence Storage**: Flexible evidence details in PostgreSQL JSONB columns
4. **Workflow Management**: 6-state workflow with role-based permissions
5. **Audit Trail**: Complete provenance tracking with SHA-256 hashing

#### ClinGen Data Architecture

**Enhanced PostgreSQL Schema**:
```sql
-- Core ClinGen verdicts and scoring
CREATE TYPE curation_verdict AS ENUM (
    'Definitive', 'Strong', 'Moderate', 'Limited', 
    'No Known Disease Relationship', 'Disputed', 'Refuted'
);

CREATE TABLE curations (
    -- Core ClinGen metrics
    verdict curation_verdict NOT NULL,
    genetic_evidence_score NUMERIC(4, 2) NOT NULL DEFAULT 0.0,
    experimental_evidence_score NUMERIC(4, 2) NOT NULL DEFAULT 0.0,
    total_score NUMERIC(4, 2) GENERATED ALWAYS AS (genetic_evidence_score + experimental_evidence_score) STORED,
    
    -- Auto-generated evidence summary
    summary_text TEXT, -- Generated from Evidence Summary Template v5.1
    sop_version VARCHAR(10) NOT NULL DEFAULT 'v11',
    
    -- Structured evidence store (JSONB)
    details JSONB NOT NULL -- ClinGen-compliant evidence structure
);
```

**Evidence Structure (curations.details JSONB)**:
- `genetic_evidence`: Case-level data, segregation data, case-control studies
- `experimental_evidence`: Functional studies, model organisms, rescue experiments
- `contradictory_evidence`: Studies that refute the gene-disease relationship
- `lumping_splitting_details`: Rationale for entity definition decisions

#### ClinGen Business Logic

**Automated Scoring System**:
- **Genetic Evidence**: Max 12 points (case-level: 12, segregation: 3, case-control: 6)
- **Experimental Evidence**: Max 6 points across functional, model, and rescue categories
- **Verdict Determination**: Algorithmic classification based on total scores and contradictory evidence

**Evidence Summary Generation**:
- Template-driven text generation following ClinGen Template v5.1
- Automated integration of evidence scores and rationales
- Support for dyadic naming conventions (gene + phenotypic descriptor)

### Migration Architecture Principles

#### Decentralization-Ready Design
- **Immutable Data Primitives**: Every curation treated as versioned, immutable event
- **Verifiable Provenance**: Cryptographic content addressing with SHA-256 hashes
- **Content Integrity**: Tamper-evident records enabling distributed scientific collaboration
- **Event Sourcing Foundation**: Append-only change log for audit trails

#### Three-Tier Architecture Benefits
- **API-First Design**: Clear separation between data, business logic, and presentation
- **Scientific Rigor**: Backend enforces ClinGen compliance automatically
- **Enhanced Performance**: PostgreSQL enables complex queries and ACID transactions
- **Modern Tooling**: Vite build system and Pinia state management

### Development Workflow Considerations

#### ClinGen Compliance Testing
- **Scoring Accuracy Tests**: Validation against SOP v11 examples
- **Summary Generation Tests**: Template compliance verification
- **Scientific Validation**: Expert panel review of implementation
- **Evidence Entry Workflow**: Multi-tab evidence collection with real-time scoring

#### Current Implementation Phases
1. **Phase 1**: Three-tier architecture with fixed ClinGen schema ✅
2. **Phase 2**: FastAPI backend with PostgreSQL database ✅
3. **Phase 3**: Vue 3 frontend with Pinia state management ✅
4. **Phase 4**: JWT authentication with role-based access control ✅
5. **Phase 5**: CRUD operations for all entities ✅
6. **Phase 6**: Workflow state management ✅

#### Planned Schema-Agnostic Transformation (See PLAN.md)
1. **Phase 1**: Schema repository and management system 📋
2. **Phase 2**: Pluggable scoring engines registry 📋
3. **Phase 3**: Dynamic UI generation from schemas 📋
4. **Phase 4**: Scope-based organization 📋
5. **Phase 5**: Multi-methodology support 📋

## Important File References

### Planning Documentation
- `PLAN.md`: Complete schema-agnostic transformation plan
- `plan/README.md`: Architecture overview for methodology-agnostic platform
- `plan/SCHEMA_SPECIFICATIONS.md`: Technical schema format specification
- `plan/SCORING_ENGINE_GUIDE.md`: Plugin development guide
- `plan/scripts/clingen_documents/`: ClinGen SOP and template reference materials

### Key Implementation Files
- `database/sql/001_initial_schema.sql`: PostgreSQL schema with ClinGen compliance
- `backend/app/models/database_models.py`: SQLAlchemy models for all entities
- `frontend/src/stores/`: Pinia stores for API data management
- `backend/app/core/config.py`: FastAPI application configuration
- `backend/pyproject.toml`: Python dependencies and tool configuration
- `frontend/package.json`: Frontend dependencies and build scripts

### Deployment & CI/CD
- `.github/workflows/gh-pages.yml`: GitHub Actions deployment to GitHub Pages
- Uses Node.js 16, builds to `/dist`, creates 404.html fallback

### Development Notes
- **Package Management**: uv for Python backend, npm for frontend
- **Container Development**: Docker Compose for full-stack development environment
- **Testing Framework**: pytest for backend, frontend testing setup in progress
- **Linting**: 
  - Backend: Ruff + mypy + bandit with pre-commit hooks
  - Frontend: ESLint + Prettier with Vite
- **State Management**: Pinia stores with API integration
- **Type Safety**: TypeScript on frontend, Python type hints with mypy on backend
- **ClinGen Reference Materials**: Available in `plan/scripts/clingen_documents/markdown/`
- **Development Tools**: Docker-based development, comprehensive Makefile commands, hot reload

## Development Guidelines

### Dual System Architecture
Gene Curator now operates as a **dual-system platform** with both legacy and schema-agnostic architectures fully implemented and operational.

### Legacy System (ClinGen-Centric) - PRODUCTION READY
When working with the legacy ClinGen system:
- Use fixed database schema with ClinGen enums (001-003.sql)
- Store evidence in JSONB `details` columns in legacy tables
- Follow existing API patterns in `backend/app/api/v1/endpoints/` (legacy endpoints)
- Use Pinia stores for state management with legacy API integration
- Reference ClinGen SOP v11 materials in `plan/scripts/clingen_documents/`

### Schema-Agnostic System - FULLY IMPLEMENTED
When working with the schema-agnostic system:
- Use flexible database schema (004-007.sql) with scope-based organization
- Implement methodology definitions through schema repository system
- Utilize pluggable scoring engines (`backend/app/scoring/`)
- Leverage dynamic validation engine (`backend/app/core/schema_validator.py`)
- Create custom methodologies using schema specifications in `plan/SCHEMA_SPECIFICATIONS.md`
- Build scope-based workflows with multi-stage pipeline and 4-eyes principle
- Use new API endpoints: `/scopes`, `/schemas`, `/validation`, `/workflow`, `/gene-assignments`

### Development Strategy
1. **Legacy System**: Continue maintenance and bug fixes for production ClinGen workflows
2. **Schema-Agnostic System**: Build new features and methodologies using the flexible architecture
3. **Frontend Integration**: Develop dynamic UI components to connect with schema-agnostic backend
4. **Migration Path**: Plan gradual migration of users from legacy to schema-agnostic workflows

### Key Resources
- `PLAN.md`: Complete architecture vision and implementation status
- `plan/README.md`: Architecture overview and implementation phases
- `plan/IMPLEMENTATION_STATUS.md`: Current implementation status and capabilities
- `plan/DEPLOYMENT.md`: Production deployment guidance and verification
- `plan/SCHEMA_SPECIFICATIONS.md`: Technical schema format specification
- `plan/SCORING_ENGINE_GUIDE.md`: Plugin development guide

**Both systems are production-ready and can be used simultaneously, providing maximum flexibility for different curation approaches.**

## Migration Guide & Dual System Usage

### System Selection Strategy

**Use Legacy System (ClinGen-Centric) When:**
- Working with existing ClinGen SOP v11 curations
- Need proven production stability for critical workflows
- Working with established ClinGen-trained curators
- Maintaining compatibility with existing data

**Use Schema-Agnostic System When:**
- Implementing new curation methodologies (GenCC, institutional approaches)
- Need flexibility for multiple clinical specialties (scopes)
- Require multi-stage workflow with peer review (4-eyes principle)
- Building new functionality that needs to scale across methodologies

### Migration Path Options

#### Option 1: Gradual Migration (Recommended)
```bash
# Phase 1: Deploy both systems simultaneously
make dev  # Starts both legacy and schema-agnostic APIs

# Phase 2: Create scopes for clinical specialties
POST /api/v1/scopes/
{
  "name": "kidney-genetics",
  "display_name": "Kidney Genetics",
  "institution": "Your Institution"
}

# Phase 3: Assign genes to scopes while maintaining legacy workflows
POST /api/v1/gene-assignments/bulk
{
  "gene_ids": ["existing-gene-ids"],
  "scope_id": "scope-uuid",
  "priority_level": "medium"
}

# Phase 4: Train users on new workflow stages
GET /api/v1/workflow/analytics  # Monitor adoption
```

#### Option 2: New Methodology Implementation
```bash
# Create custom methodology schema
POST /api/v1/schemas/
{
  "name": "institutional_custom",
  "version": "1.0.0",
  "type": "curation",
  "field_definitions": { /* custom fields */ },
  "scoring_configuration": {"engine": "qualitative_assessment"}
}

# Validate schema works
POST /api/v1/validation/validate-schema
# Test with sample data
POST /api/v1/validation/validate-evidence
```

### Database Migration Commands

#### Deploy Schema-Agnostic Tables (Alongside Legacy)
```bash
# Run new schema files (004-007) without affecting legacy (001-003)
psql -d gene_curator < database/sql/004_schema_agnostic_foundation.sql
psql -d gene_curator < database/sql/005_schema_agnostic_triggers.sql
psql -d gene_curator < database/sql/006_schema_agnostic_views.sql
psql -d gene_curator < database/sql/007_schema_agnostic_seed_data.sql
```

#### Verify Dual System Status
```bash
# Check legacy tables exist
psql -d gene_curator -c "SELECT count(*) FROM users, genes, curations;"

# Check new tables exist
psql -d gene_curator -c "SELECT count(*) FROM scopes, curation_schemas, gene_assignments;"
```

### Development Workflow

#### Working with Legacy System
```bash
# Use existing API patterns
GET /api/v1/genes          # Legacy gene management
GET /api/v1/curations      # Legacy curation workflow
GET /api/v1/precurations   # Legacy precuration system

# Follow existing Pinia store patterns
// frontend/src/stores/curationStore.js (existing)
```

#### Working with Schema-Agnostic System
```bash
# Use new API patterns
GET /api/v1/scopes                    # Scope management
GET /api/v1/schemas                   # Schema repository
GET /api/v1/gene-assignments          # Gene assignment system
GET /api/v1/workflow/analytics        # Workflow monitoring
POST /api/v1/validation/validate-evidence  # Dynamic validation

# Create new Pinia stores for schema-agnostic features
// frontend/src/stores/scopeStore.js (new)
// frontend/src/stores/schemaStore.js (new)
// frontend/src/stores/workflowStore.js (new)
```

### Frontend Integration Strategy

#### Phase 1: Add Schema-Agnostic Stores
```javascript
// frontend/src/stores/schemaStore.js
import { defineStore } from 'pinia'
import { schemaApi } from '@/api/schemas'

export const useSchemaStore = defineStore('schema', {
  state: () => ({
    schemas: [],
    activeSchema: null
  }),
  actions: {
    async fetchSchemas() {
      this.schemas = await schemaApi.list()
    },
    async validateEvidence(data, schemaId) {
      return await schemaApi.validateEvidence(data, schemaId)
    }
  }
})
```

#### Phase 2: Create Dynamic Components
```javascript
// frontend/src/components/dynamic/DynamicForm.vue
// Uses /api/v1/validation/generate-json-schema/{schema_id}
// Renders forms based on schema definitions
```

#### Phase 3: Scope-Based Navigation
```javascript
// Add scope selection to existing navigation
// Integrate with existing user authentication
// Preserve existing ClinGen workflows
```

### Verification & Testing

#### Test Schema-Agnostic System
```bash
# Backend functionality test
python -c "
from app.core.schema_validator import schema_validator
from app.scoring.registry import ScoringEngineRegistry
registry = ScoringEngineRegistry()
print('Available engines:', list(registry._engines.keys()))
"

# API integration test
curl -X GET http://localhost:8000/api/v1/scopes
curl -X GET http://localhost:8000/api/v1/schemas
```

#### Monitor System Health
```bash
# Use existing health check
make health

# Check both database schemas
psql -d gene_curator -c "SELECT 'legacy' as system, count(*) FROM curations 
UNION SELECT 'schema-agnostic' as system, count(*) FROM curation_instances;"
```

### Rollback Strategy

#### If Issues with Schema-Agnostic System
```bash
# Schema-agnostic system is additive - legacy system unaffected
# Simply don't use new endpoints, continue with existing workflow
# Remove new tables only if necessary (data loss warning):
# DROP TABLE IF EXISTS scopes, curation_schemas, gene_assignments CASCADE;
```

The dual system approach ensures **zero risk** to existing production workflows while enabling powerful new capabilities.