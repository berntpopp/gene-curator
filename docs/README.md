# Gene Curator Documentation

## Overview

This documentation provides comprehensive technical details for the Gene Curator platform - a modern three-tier genetic curation system with native ClinGen SOP v11 compliance.

## Documentation Structure

### Core Architecture Documents

#### [🏗️ Architecture Overview](./ARCHITECTURE.md)
**System design and technology stack**
- Three-tier architecture (Database → API → Frontend)
- Technology stack and design principles
- Deployment architecture and performance considerations
- Migration strategy from Firebase to PostgreSQL

#### [🗄️ Database Schema](./DATABASE_SCHEMA.md)
**PostgreSQL schema with ClinGen compliance**
- Complete table definitions and relationships
- JSONB evidence structure documentation
- Automated scoring triggers and constraints
- Performance optimizations and indexing strategy

#### [📋 Workflow Documentation](./WORKFLOW.md)
**Complete curation process flows**
- Gene → Pre-curation → Curation workflow
- State transitions and user roles
- Data transformations and business rules
- Quality assurance and review processes

### Implementation Details

#### [🔬 ClinGen SOP v11 Compliance](./CLINGEN_COMPLIANCE.md)
**Evidence scoring and classification system**
- Automated evidence scoring engine
- SOP v11 scoring rules and constraints
- Summary generation (Template v5.1)
- Classification logic and workflow integration

#### [🔌 API Reference](./API_REFERENCE.md)
**Complete FastAPI endpoint documentation**
- Authentication and authorization
- CRUD operations for all entities
- ClinGen-specific endpoints
- Request/response schemas and examples

#### [🎨 Frontend Development Guide](./FRONTEND_GUIDE.md)
**Vue 3 component architecture and patterns**
- ClinGen-specific UI components
- Pinia state management patterns
- User interface workflows
- Development and testing strategies

## Quick Navigation

### By User Role

**🔬 Scientists & Curators**
- [Workflow Documentation](./WORKFLOW.md) - Understanding the curation process  
- [ClinGen Compliance](./CLINGEN_COMPLIANCE.md) - Evidence requirements and scoring
- [Frontend Guide](./FRONTEND_GUIDE.md) - User interface workflows

**👨‍💻 Developers**
- [Architecture Overview](./ARCHITECTURE.md) - System design principles
- [API Reference](./API_REFERENCE.md) - Backend integration
- [Database Schema](./DATABASE_SCHEMA.md) - Data structure and relationships
- [Frontend Guide](./FRONTEND_GUIDE.md) - Component development

**🔧 System Administrators**
- [Architecture Overview](./ARCHITECTURE.md) - Deployment and infrastructure
- [Database Schema](./DATABASE_SCHEMA.md) - Schema management and maintenance
- [API Reference](./API_REFERENCE.md) - System configuration and monitoring

### By Implementation Phase

**📋 Planning & Design**
- [Architecture Overview](./ARCHITECTURE.md)
- [Workflow Documentation](./WORKFLOW.md)
- [ClinGen Compliance](./CLINGEN_COMPLIANCE.md)

**🔨 Backend Development**
- [Database Schema](./DATABASE_SCHEMA.md)
- [API Reference](./API_REFERENCE.md)
- [ClinGen Compliance](./CLINGEN_COMPLIANCE.md)

**🎨 Frontend Development**
- [Frontend Guide](./FRONTEND_GUIDE.md)
- [API Reference](./API_REFERENCE.md)
- [Workflow Documentation](./WORKFLOW.md)

## Key Features Documented

### 🧬 ClinGen Native Compliance
- **Database-Level Enforcement**: Evidence scoring implemented as PostgreSQL triggers
- **Automated Summary Generation**: Template v5.1 compliant evidence summaries
- **Real-time Validation**: Client and server-side SOP v11 compliance checking
- **Expert Panel Integration**: GCEP workflow support and GenCC submission

### 🏗️ Modern Architecture
- **Three-Tier Design**: Clear separation of concerns with API-first approach
- **Type Safety**: End-to-end TypeScript with Pydantic validation
- **Performance Optimized**: PostgreSQL queries, Vite builds, JSONB indexing
- **Scalable Deployment**: Containerized with horizontal scaling support

### 🔒 Scientific Integrity
- **Immutable Records**: Content-addressable with SHA-256 hashing
- **Complete Provenance**: Full audit trail with user attribution
- **Version Control**: Record chaining enables distributed collaboration
- **Quality Assurance**: Multi-stage review and approval workflow

### 📊 Evidence Management
- **Structured Evidence Entry**: Multi-category evidence collection interface
- **Real-time Scoring**: Live calculation with SOP v11 limit enforcement
- **Citation Validation**: PMID verification and accessibility checking
- **Contradictory Evidence**: Systematic handling of conflicting data

## Getting Started

### For New Users
1. Start with [Architecture Overview](./ARCHITECTURE.md) to understand the system design
2. Review [Workflow Documentation](./WORKFLOW.md) to understand the curation process
3. Explore [ClinGen Compliance](./CLINGEN_COMPLIANCE.md) for evidence requirements

### For Developers
1. Read [Architecture Overview](./ARCHITECTURE.md) for system understanding
2. Study [Database Schema](./DATABASE_SCHEMA.md) for data structure
3. Reference [API Documentation](./API_REFERENCE.md) for integration
4. Follow [Frontend Guide](./FRONTEND_GUIDE.md) for UI development

### For Scientists
1. Review [ClinGen Compliance](./CLINGEN_COMPLIANCE.md) for scientific standards
2. Understand [Workflow Documentation](./WORKFLOW.md) for process details
3. Reference evidence entry patterns in [Frontend Guide](./FRONTEND_GUIDE.md)

## Document Conventions

### Code Examples
All code examples are production-ready and follow project conventions:
- **SQL**: PostgreSQL 15+ compatible with proper indexing
- **Python**: FastAPI with Pydantic validation and type hints
- **JavaScript/Vue**: Composition API with `<script setup>` syntax
- **TypeScript**: Strict typing with proper interface definitions

### API Examples
API examples include:
- Complete request/response cycles
- Error handling patterns
- Authentication requirements
- Rate limiting considerations

### Database Examples
Database examples show:
- Complete DDL with constraints
- Proper indexing strategies
- Trigger implementations
- Performance optimizations

## External References

### ClinGen Resources
- [Gene-Disease Clinical Validity SOP v11](https://clinicalgenome.org/docs/gene-disease-clinical-validity-standard-operating-procedures-version-11/)
- [Evidence Summary Template v5.1](https://clinicalgenome.org/docs/gene-disease-clinical-validity-evidence-summary-template-version-5-1/)
- [ClinGen Expert Panel Process](https://clinicalgenome.org/curation-activities/gene-disease-validity/)

### Technology Documentation
- [Vue 3 Documentation](https://vuejs.org/guide/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Standards and Ontologies
- [HGNC Gene Nomenclature](https://www.genenames.org/)
- [MONDO Disease Ontology](https://mondo.monarchinitiative.org/)
- [Human Phenotype Ontology](https://hpo.jax.org/)
- [GenCC Gene-Disease Validity](https://thegencc.org/)

## Contributing to Documentation

### Documentation Standards
- **Clarity**: Write for both technical and scientific audiences
- **Completeness**: Include working examples and edge cases
- **Currency**: Keep examples synchronized with implementation
- **Cross-references**: Link related concepts across documents

### Update Process
1. Technical changes require documentation updates
2. All code examples must be tested and validated
3. Cross-references should be updated when document structure changes
4. Scientific accuracy requires expert review for ClinGen-related content

---

## Document Status

| Document | Last Updated | Status | Review Required |
|----------|-------------|---------|-----------------|
| [Architecture](./ARCHITECTURE.md) | 2024-01-15 | ✅ Current | Quarterly |
| [Database Schema](./DATABASE_SCHEMA.md) | 2024-01-15 | ✅ Current | With Schema Changes |
| [Workflow](./WORKFLOW.md) | 2024-01-15 | ✅ Current | Semi-annually |
| [ClinGen Compliance](./CLINGEN_COMPLIANCE.md) | 2024-01-15 | ✅ Current | With SOP Updates |
| [API Reference](./API_REFERENCE.md) | 2024-01-15 | ✅ Current | With API Changes |
| [Frontend Guide](./FRONTEND_GUIDE.md) | 2024-01-15 | ✅ Current | With Component Updates |

For questions or suggestions about this documentation, please open an issue in the project repository.