# Gene Curator - Schema-Agnostic Genetic Curation Platform

> **🎉 SCHEMA-AGNOSTIC ARCHITECTURE COMPLETE**
> 
> Gene Curator has been successfully transformed into a flexible, methodology-agnostic curation platform while maintaining full ClinGen SOP v11 compliance. The system now supports any genetic curation methodology through configurable schemas.

## Architecture Overview

Gene Curator is a containerized schema-agnostic platform that supports multiple genetic curation methodologies:

### 🏗️ Architecture Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Database** | PostgreSQL 15+ | JSONB schemas, multi-methodology support |
| **Backend** | FastAPI + SQLAlchemy + uv | Schema-driven API, pluggable scoring engines |
| **Frontend** | Vue 3 + Vite + Pinia | Dynamic UI, methodology-agnostic components |
| **Orchestration** | Docker Compose | Development and deployment |

### 🚀 Key Features

- **Schema-Agnostic**: Support for ClinGen, GenCC, or custom methodologies
- **Scope-Based Organization**: Clinical specialty domains (kidney-genetics, cardio-genetics, etc.)
- **Pluggable Scoring Engines**: Registry-based scoring system
- **Dynamic Validation**: Real-time evidence validation with business rules
- **Multi-Stage Workflow**: Entry → Precuration → Curation → Review → Active
- **4-Eyes Principle**: Mandatory peer review for quality assurance
- **Modern Tooling**: Backend uses [uv](https://docs.astral.sh/uv/) for blazing-fast Python package management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)
- Git

### Development Setup

1. **Clone and start the development environment:**
   ```bash
   git clone https://github.com/halbritter-lab/gene-curator.git
   cd gene-curator
   make dev
   ```

2. **Access the applications:**
   - **Frontend Application**: http://localhost:3001
   - **API Documentation**: http://localhost:8001/docs
   - **Database**: localhost:5454 (credentials in docker-compose.dev.yml)

3. **Check service health:**
   ```bash
   make health
   ```

### Alternative Setup (without Make)

```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Stop environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

## Development Commands

```bash
# Environment management
make dev          # Start development environment
make dev-build    # Rebuild and start
make dev-down     # Stop environment
make dev-logs     # View logs

# Database operations
make db-init      # Initialize database with schema and seed data
make db-reset     # Reset database completely
make db-shell     # Access PostgreSQL shell

# Code quality
make test         # Run all tests
make lint         # Run linting
make format       # Format code

# Utilities
make status       # Show service status
make clean        # Clean up Docker resources
```

## Database Features

### ClinGen SOP v11 Compliance

The database implements native ClinGen compliance through:

- **Automatic Scoring Triggers**: Evidence scores calculated per SOP v11 matrix
- **Verdict Classification**: Algorithmic determination of curation verdicts
- **Provenance Tracking**: Complete audit trail with SHA-256 record hashes
- **Evidence Validation**: Structured JSONB evidence store with validation

### Sample Data

The development database includes:
- **Sample Users**: Admin, curator, and viewer accounts with role-based access control
- **Sample Genes**: Multiple genes with HGNC-compliant metadata
- **Sample Precurations**: Disease association examples with lumping/splitting decisions
- **Sample Curations**: Multi-methodology curation examples (ClinGen, GenCC, Qualitative)

**Default Development Credentials:**
- Admin: `admin@gene-curator.dev` / `admin123`
- Curator: `curator@gene-curator.dev` / `curator123`
- Viewer: `viewer@gene-curator.dev` / `viewer123`

## API Features

### FastAPI Backend

- **OpenAPI Documentation**: Automatic API documentation at `/docs`
- **Type Safety**: Full Pydantic validation and serialization
- **Health Checks**: Database and scoring engine health monitoring
- **Authentication**: JWT-based authentication with role-based access control
- **Schema Management**: Dynamic schema repository and validation
- **Workflow Engine**: Multi-stage workflow with 4-eyes principle

### Schema-Agnostic Scoring

The backend includes multiple scoring engines:

```bash
# Example: Test the API health
curl -X GET "http://localhost:8001/api/v1/health"

# Example: Login and get token
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@gene-curator.dev", "password": "admin123"}'

# Example: Access protected endpoint
curl -X GET "http://localhost:8001/api/v1/precurations/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Frontend Architecture

The frontend features:
- **Vue 3 + Composition API**: Modern reactive framework with Composition API
- **Vite Build System**: Lightning-fast development and builds
- **Pinia State Management**: Type-safe centralized state management
- **Vuetify 3**: Material Design component library
- **Schema-Driven Components**: Dynamic form generation from API schemas
- **Authentication**: JWT token management with automatic refresh
- **Multi-methodology Support**: Components adapt to different curation methodologies

## Schema System

The system implements a flexible schema-driven approach:
- **Schema Repository**: JSON schemas stored in database with versioning
- **Dynamic Validation**: Real-time evidence validation with business rules  
- **Pluggable Scoring**: Registry-based scoring engines (ClinGen, GenCC, Qualitative)
- **Scope Management**: Clinical specialty organization with RBAC
- **Workflow Engine**: Multi-stage workflows with configurable transitions

## Project Structure

```
gene-curator/
├── backend/                 # FastAPI backend application
│   ├── app/                # Application code
│   │   ├── api/v1/         # REST API endpoints (25+ endpoints)
│   │   ├── core/           # Core functionality (config, database, validation)
│   │   ├── crud/           # Database CRUD operations
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── scoring/        # Pluggable scoring engines
│   │   └── tests/          # Comprehensive test suite
│   └── scripts/            # Development and deployment scripts
├── frontend/               # Vue 3 + Vite frontend application
│   ├── src/
│   │   ├── api/            # API client with authentication
│   │   ├── components/     # Reusable Vue components
│   │   ├── stores/         # Pinia state management
│   │   ├── views/          # Page-level components
│   │   └── router/         # Vue Router configuration
│   └── public/             # Static assets
├── database/               # Database setup and migrations
│   └── sql/                # PostgreSQL schema definitions (7 files)
└── plan/                   # Architecture documentation
    └── scripts/            # Reference materials and examples
```

## Scientific Features

### Evidence Management
- **Structured Evidence Entry**: Forms for case-level, segregation, and experimental evidence
- **Automatic Scoring**: Real-time calculation per ClinGen SOP v11
- **Evidence Summary**: Template-driven summary generation
- **External Integration**: Support for PanelApp, ClinVar, and other sources

### Quality Assurance
- **Multi-stage Review**: Primary and secondary curator review process
- **Change Tracking**: Complete audit log of all modifications
- **Verification**: Cryptographic record verification for scientific integrity
- **Compliance Monitoring**: Automated ClinGen standard compliance checking

## Implementation Status

### ✅ Phase 1: Schema-Agnostic Foundation (COMPLETE)
- [x] PostgreSQL schema with JSONB evidence storage
- [x] Schema repository and validation system
- [x] Pluggable scoring engine registry
- [x] Multi-stage workflow engine with 4-eyes principle
- [x] Scope-based organization with RBAC

### ✅ Phase 2: API Implementation (COMPLETE)
- [x] JWT authentication and authorization system
- [x] Complete CRUD operations for all entities (25+ endpoints)
- [x] Multi-methodology scoring engines (ClinGen, GenCC, Qualitative)
- [x] Real-time evidence validation
- [x] Advanced search, filtering, and statistics

### ✅ Phase 3: Frontend Development (COMPLETE)
- [x] Vue 3 + Vite application with hot reload
- [x] Pinia state management with API integration
- [x] Authentication and protected routes
- [x] Data tables with search and pagination
- [x] Responsive design with Vuetify 3

### 🚀 Phase 4: Production Readiness (ONGOING)
- [x] Comprehensive testing suite (100+ tests)
- [x] Code quality with linting and formatting
- [x] Security best practices (JWT, CORS, validation)
- [x] Docker-based deployment
- [x] Health monitoring and observability

## Getting Started

### Quick Development Setup

1. **Clone and start:**
   ```bash
   git clone https://github.com/halbritter-lab/gene-curator.git
   cd gene-curator
   make dev
   ```

2. **Access applications:**
   - Frontend: http://localhost:3001
   - API Docs: http://localhost:8001/docs
   - Login: `admin@gene-curator.dev` / `admin123`

3. **Development workflow:**
   ```bash
   # Backend linting (using modern uv)
   cd backend && uv run python scripts/lint.py
   
   # Backend formatting
   cd backend && uv run python scripts/format.py
   
   # Frontend linting  
   cd frontend && npm run lint && npm run format
   
   # Run tests
   make test
   ```

### Development Tools

- **Package Management**: uv (backend) - blazing-fast Python package manager, npm (frontend)
- **Code Quality**: ESLint + Prettier (frontend), Ruff + MyPy (backend)
- **Hot Reload**: Vite dev server (frontend), Uvicorn reload (backend)
- **API Testing**: OpenAPI docs at `/docs` with interactive testing
- **Database**: PostgreSQL with pgAdmin available on port 5050

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **ClinGen Consortium**: For establishing the Gene-Disease Validity Standard Operating Procedures
- **GenCC**: For the Gene Curation Coalition standards and guidelines
- **Scientific Community**: For the principles of verifiable, attributable, and replicable genetic curation
- **Vue.js & FastAPI Communities**: For excellent frameworks that enable rapid development

---

**Gene Curator** - Supporting the future of genetic curation through flexible, methodology-agnostic architecture.
