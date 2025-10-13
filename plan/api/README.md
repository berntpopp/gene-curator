# API Plan - FastAPI Backend with ClinGen Scoring Engine

This directory contains the API design and implementation plan for the FastAPI backend that will replace Firebase Functions and implement native ClinGen SOP v11 compliance.

## Work Stream Overview

**Objective**: Build a modern, type-safe API layer that enforces ClinGen standards at the business logic level, providing automated evidence scoring and summary generation.

**Key Innovations**:
- **ClinGen Business Logic Engine**: Automatic evidence scoring per SOP v11
- **Evidence Summary Generator**: Template-driven summary creation per Template v5.1
- **Clean Architecture**: Separation of concerns with proper dependency injection
- **Type Safety**: Pydantic models ensure data consistency and validation

## Directory Structure

```
api/
├── README.md                   # This overview
├── architecture.md             # API architecture and design patterns
├── clingen_engine.md          # ClinGen scoring and summary engine design
├── endpoints.md               # Complete API endpoint documentation
├── models.md                  # Pydantic models and schemas
├── authentication.md          # JWT authentication and RBAC
├── testing.md                 # Testing strategy and test cases
└── implementation/
    ├── project_structure.md   # FastAPI project organization
    ├── dependencies.md        # Python dependencies and versions
    ├── deployment.md          # Docker and deployment configuration
    └── migration_api.md       # API for Firebase to PostgreSQL migration
```

## Key Features

### 1. ClinGen Compliance Engine
- **Automated Scoring**: Real-time calculation of genetic and experimental evidence scores
- **Verdict Classification**: Algorithmic determination based on SOP v11 rules
- **Summary Generation**: Template-driven evidence summary creation
- **Validation**: Ensure all evidence meets ClinGen formatting requirements

### 2. Modern API Design
- **Type Safety**: Pydantic models for request/response validation
- **Dependency Injection**: Clean separation of business logic and data access
- **Error Handling**: Comprehensive error responses with proper HTTP status codes
- **API Documentation**: Automatic OpenAPI/Swagger documentation

### 3. Enhanced Workflow Support
- **Professional Curation**: Multi-stage review process with audit logging
- **Provenance Tracking**: Complete source attribution and version control
- **External Evidence**: Integration with PanelApp, Blueprint Genetics, etc.
- **Advanced Querying**: Complex search with JSONB-based filtering

## Core Components

### Business Logic Layer
```python
# Core ClinGen scoring engine
app/core/clingen/
├── scoring_engine.py          # Evidence scoring per SOP v11
├── summary_generator.py       # Template-based summary generation
├── nomenclature.py           # ClinGen naming validation
└── validators.py             # Evidence format validation

# Scientific workflow management
app/core/workflow/
├── curation_workflow.py      # Professional review process
├── provenance.py            # Source tracking and attribution
└── quality_control.py       # Data integrity validation
```

### API Layer
```python
# RESTful endpoints
app/api/v1/
├── genes.py                  # Gene management endpoints
├── precurations.py          # Precuration workflow endpoints
├── curations.py             # Full curation CRUD with ClinGen features
├── users.py                 # User management and authentication
├── search.py                # Advanced search and filtering
└── admin.py                 # Administrative functions

# WebSocket for real-time features
app/websocket/
├── scoring_updates.py       # Real-time score calculation
└── collaboration.py         # Multi-user curation support
```

### Data Access Layer
```python
# Database operations
app/crud/
├── base.py                  # Generic CRUD operations
├── genes.py                 # Gene-specific database operations
├── curations.py            # Curation CRUD with ClinGen logic
└── users.py                # User management

# Database models
app/models/
├── gene.py                 # Gene SQLAlchemy model
├── curation.py            # Curation model with ClinGen fields
├── user.py                # User and authentication models
└── change_log.py          # Audit trail model
```

## Integration Points

- **Database Work Stream**: Uses PostgreSQL schema with ClinGen compliance features
- **Frontend Work Stream**: Provides typed API contracts for Vue 3 components
- **Original Firebase**: Maintains compatibility during migration period

## Work Stream Status

- [x] Requirements extracted from original plan
- [ ] Architecture documentation
- [ ] ClinGen engine specification
- [ ] API endpoint design
- [ ] Pydantic model definition
- [ ] Authentication strategy
- [ ] Testing framework setup

## Next Steps

1. Document API architecture and design patterns
2. Specify ClinGen scoring engine implementation
3. Define complete endpoint structure
4. Create Pydantic model schemas
5. Design authentication and authorization
6. Plan comprehensive testing strategy

## Success Criteria

- **ClinGen Compliance**: 100% accurate evidence scoring per SOP v11
- **Performance**: Sub-200ms response times for all endpoints
- **Type Safety**: Full Pydantic validation with comprehensive error handling
- **Scientific Rigor**: Complete provenance tracking and audit trails
- **Developer Experience**: Auto-generated documentation and clear API contracts