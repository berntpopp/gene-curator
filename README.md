# Gene Curator

**A flexible, methodology-agnostic platform for genetic evidence curation and gene-disease validity assessment.**

## Purpose

Gene Curator enables clinical genetics teams to curate gene-disease associations using any methodology—whether ClinGen SOP, GenCC standards, or institution-specific approaches. The platform ensures scientific rigor through structured evidence capture, automated scoring, peer review workflows, and complete provenance tracking.

## Core Capabilities

- **Methodology Flexibility**: Support for ClinGen, GenCC, or custom curation frameworks through configurable schemas
- **Clinical Organization**: Scope-based structure for specialty domains (kidney genetics, cardiology, neurology, etc.)
- **Quality Assurance**: Multi-stage workflow with mandatory peer review (4-eyes principle)
- **Evidence Management**: Structured capture with real-time validation and automated scoring
- **Team Collaboration**: Role-based access control with curator workload management
- **Scientific Integrity**: Complete audit trails with cryptographic record verification

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
   - **Frontend Application**: http://localhost:3051
   - **API Documentation**: http://localhost:8051/docs
   - **Database**: localhost:5454 (credentials in docker-compose.dev.yml)

3. **Check service health:**
   ```bash
   make health
   ```

## Common Commands

```bash
# Environment management
make dev          # Start development environment
make dev-build    # Rebuild and start
make dev-down     # Stop environment
make status       # Show service status

# Database operations
make db-init      # Initialize database with schema and seed data
make db-reset     # Reset database completely

# Code quality
make test         # Run all tests
make lint         # Run linting (backend + frontend)
make format       # Format code (backend + frontend)
```

## How It Works

### Multi-Stage Curation Workflow

1. **Entry**: Genes are assigned to clinical scopes and curators
2. **Precuration**: Initial disease association assessment with lumping/splitting analysis
3. **Curation**: Detailed evidence collection following the selected methodology
4. **Review**: Independent peer review by a different curator (4-eyes principle)
5. **Active**: Approved curations become the authoritative gene-disease assertion

### Methodology Support

Gene Curator adapts to your curation approach through:
- **Configurable Schemas**: Define evidence fields, validation rules, and scoring logic
- **Pluggable Scoring Engines**: Built-in support for ClinGen SOP v11, GenCC, and custom algorithms
- **Dynamic Forms**: UI automatically adapts to your methodology's requirements
- **Flexible Workflows**: Customize stages, transitions, and approval processes

### Default Login Credentials (Development)

- Admin: `admin@gene-curator.dev` / `admin123`
- Curator: `curator@gene-curator.dev` / `curator123`
- Viewer: `viewer@gene-curator.dev` / `viewer123`

## Architecture

```
gene-curator/
├── backend/                 # FastAPI + PostgreSQL backend
│   ├── app/api/v1/         # REST API endpoints
│   ├── app/scoring/        # Pluggable scoring engines
│   └── app/tests/          # Test suite
├── frontend/               # Vue 3 + Vite application
│   ├── src/components/     # UI components
│   └── src/stores/         # State management
└── database/sql/           # PostgreSQL schema definitions
```

## Documentation

- **API Documentation**: http://localhost:8051/docs (interactive OpenAPI)
- **Architecture Details**: See `CLAUDE.md` for development guidelines
- **Schema Specifications**: See `plan/SCHEMA_SPECIFICATIONS.md`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **ClinGen Consortium**: For establishing the Gene-Disease Validity Standard Operating Procedures
- **GenCC**: For the Gene Curation Coalition standards and guidelines
- **Scientific Community**: For the principles of verifiable, attributable, and replicable genetic curation
- **Vue.js & FastAPI Communities**: For excellent frameworks that enable rapid development

---

**Gene Curator** - Supporting the future of genetic curation through flexible, methodology-agnostic architecture.
