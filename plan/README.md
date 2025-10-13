# Gene Curator: Schema-Agnostic Architecture Implementation Plan

This directory contains the complete implementation plan for transforming Gene Curator into a flexible, methodology-agnostic curation platform that supports any scientific approach through configurable schemas.

## Architecture Overview

### Core Principle
**Everything configurable through schemas**: field definitions, validation rules, scoring algorithms, workflow states, and UI components. No curation methodology should be hard-coded into the system.

### Key Innovations

#### 1. Schema-Driven Design
- **Methodology Agnostic**: Support ClinGen, GenCC, custom institutional approaches
- **Version Control**: Full versioning of schema definitions and evolution
- **Plugin Architecture**: Scoring engines and UI components loaded dynamically
- **Configuration Over Code**: New methodologies via JSON, not software updates

#### 2. Flexible Data Architecture  
- **JSONB Evidence Storage**: Adapts to any schema structure automatically
- **Dynamic Validation**: Schema-driven rules engine
- **Computed Fields**: Real-time scoring and verdict calculation
- **Complete Audit Trail**: Immutable records with full provenance

#### 3. Universal Platform Design
- **Multi-Methodology**: Multiple approaches working simultaneously
- **Institution-Specific**: Customizable to organizational standards
- **Future-Proofing**: Accommodates methodologies not yet developed
- **Scientific Rigor**: Maintains data integrity across all approaches

## Implementation Work Streams

### 🗄️ Schema Management System
**Focus**: Core infrastructure for methodology definitions
**Key Deliverables**:
- Schema repository with version control
- Schema pairing system (precuration + curation)
- User/institution preference management
- Schema validation and integrity checking

### 🔧 Pluggable Scoring Engines
**Focus**: Methodology-specific scoring logic as plugins
**Key Deliverables**:
- Scoring engine base interface and registry
- ClinGen SOP v11 engine implementation
- GenCC-based classification engine
- Custom institutional scoring examples

### 🎨 Dynamic User Interface
**Focus**: Schema-driven form generation and interaction
**Key Deliverables**:
- Dynamic form builder from schema definitions
- Real-time validation and scoring updates
- Configurable workflow state management
- Responsive, methodology-agnostic components

### 🗃️ Flexible Data Storage
**Focus**: Methodology-agnostic database design
**Key Deliverables**:
- JSONB-based evidence storage system
- Schema-aware triggers and constraints
- Performance optimization for flexible queries
- Data migration from fixed ClinGen structure

## Supported Methodologies (Examples)

### 1. ClinGen SOP v11 (Gene-Disease Validity)
```json
{
  "name": "ClinGen_SOP_v11",
  "scoring_engine": "clingen_sop_v11",
  "evidence_categories": ["genetic_evidence", "experimental_evidence"],
  "verdicts": ["Definitive", "Strong", "Moderate", "Limited"],
  "max_score": 18
}
```

### 2. GenCC-Based Classification
```json
{
  "name": "GenCC_Classification",  
  "scoring_engine": "gencc_based",
  "evidence_categories": ["genetic_evidence", "experimental_evidence"],
  "verdicts": ["Definitive", "Strong", "Moderate", "Limited"]
}
```

### 3. Custom Institutional Approach
```json
{
  "name": "Institution_Custom_v1",
  "scoring_engine": "qualitative_assessment", 
  "evidence_categories": ["clinical_assessment", "literature_review"],
  "verdicts": ["Strong Association", "Moderate Association", "Weak Association"]
}
```

## Project Structure

```
plan/
├── README.md                           # This overview document
├── SCHEMA_SPECIFICATIONS.md            # Technical schema format specification
├── SCORING_ENGINE_GUIDE.md             # How to create scoring plugins
├── IMPLEMENTATION_STATUS.md            # Current implementation status and achievements
├── DEPLOYMENT.md                       # Production deployment guide and verification
├── database/                           # Database design work stream
│   ├── README.md                       # Database architecture overview
│   ├── flexible_schema_design.md       # JSONB-based storage design
│   ├── performance_optimization.md     # Indexing and query strategies
│   └── sql/                           # Implementation SQL scripts
├── backend/                            # API work stream  
│   ├── README.md                       # Backend architecture overview
│   ├── schema_management_api.md        # Schema CRUD operations
│   ├── scoring_engine_registry.md      # Plugin system design
│   ├── workflow_engine.md              # State machine implementation
│   └── implementation/                 # Detailed implementation guides
├── frontend/                           # Frontend work stream
│   ├── README.md                       # Frontend architecture overview
│   ├── dynamic_form_generation.md      # Schema-driven UI system
│   ├── real_time_scoring.md            # Live scoring integration
│   ├── schema_selection_ux.md          # User schema management
│   └── implementation/                 # Component implementation guides
└── archived/                           # Previous ClinGen-centric plans
    ├── PLAN_ORIGINAL.md                # Original refactoring plan
    ├── clingen_specific/               # ClinGen-focused documentation
    └── firebase/                       # Firebase implementation reference
```

## Development Phases

### Phase 1: Schema Infrastructure (Weeks 1-3)
**Goal**: Build the foundation for schema-driven architecture

#### Database Layer
- [ ] Design flexible curation storage with JSONB
- [ ] Implement schema repository tables
- [ ] Create schema validation system
- [ ] Build dynamic trigger system for scoring

#### API Layer  
- [ ] Schema management endpoints (CRUD)
- [ ] Scoring engine registry implementation
- [ ] Basic workflow state management
- [ ] Schema validation middleware

#### Frontend Layer
- [ ] Basic dynamic form generation
- [ ] Schema selection interface
- [ ] Real-time validation framework
- [ ] Component registry system

### Phase 2: Core Methodologies (Weeks 4-6)
**Goal**: Implement key curation methodologies as schemas

#### ClinGen Implementation
- [ ] Convert current ClinGen logic to schema definition
- [ ] Implement ClinGen scoring engine plugin
- [ ] Create ClinGen-specific UI components
- [ ] Validate against current functionality

#### GenCC Implementation
- [ ] Design GenCC-based classification schema
- [ ] Implement GenCC scoring engine
- [ ] Build GenCC evidence entry components
- [ ] Test with gene-disease validity data

#### Custom Example
- [ ] Create institutional custom methodology
- [ ] Implement qualitative scoring engine
- [ ] Demonstrate flexibility of system
- [ ] Document custom schema creation process

### Phase 3: Advanced Features (Weeks 7-9)
**Goal**: Complete platform capabilities

#### Workflow Engine
- [ ] Schema-driven state machine implementation
- [ ] Role-based permissions per schema
- [ ] State transition validation
- [ ] Audit trail for state changes

#### Advanced UI Components
- [ ] Evidence table with dynamic columns
- [ ] Literature reference management
- [ ] Batch evidence entry
- [ ] Export/import functionality

#### User Experience
- [ ] Schema preference management
- [ ] Methodology switching interface
- [ ] Dashboard with multi-methodology view
- [ ] Help system with schema-specific guidance

### Phase 4: Production Readiness (Weeks 10-12)
**Goal**: Deploy production-ready system

#### Performance & Scaling
- [ ] JSONB indexing optimization
- [ ] Caching for schema definitions
- [ ] Load testing across methodologies
- [ ] Database query optimization

#### Testing & Validation
- [ ] Comprehensive test suite for all schemas
- [ ] Expert validation of methodology implementations
- [ ] Security audit of flexible architecture
- [ ] Data integrity validation

#### Documentation & Training
- [ ] Schema creation documentation
- [ ] User training materials
- [ ] Developer API documentation
- [ ] Deployment and maintenance guides

## Key Architectural Decisions

### 1. JSONB Over Fixed Columns
**Decision**: Use PostgreSQL JSONB for evidence storage
**Rationale**: Maximum flexibility for unknown future methodologies
**Trade-off**: Some query complexity for infinite extensibility

### 2. Plugin-Based Scoring
**Decision**: Registry of scoring engines rather than inheritance hierarchy  
**Rationale**: Runtime selection and easy addition of new methodologies
**Trade-off**: Slightly more complex initial setup for maximum flexibility

### 3. Schema-First UI Generation
**Decision**: Generate forms dynamically from schema definitions
**Rationale**: Single UI codebase supports infinite methodologies
**Trade-off**: Less UI customization for universal compatibility

### 4. Clean Slate Migration
**Decision**: Fresh implementation without backward compatibility
**Rationale**: Remove all ClinGen-centric technical debt
**Trade-off**: One-time migration effort for long-term flexibility

## Success Criteria

### Technical Success
- [x] **Scope-Based Organization**: Clinical specialty-based curation domains implemented
- [x] **Multi-Stage Workflow**: 5-stage pipeline with 4-eyes principle quality assurance
- [x] **Multi-Curation Support**: Multiple curations per gene-scope with active/archived management
- [x] **Multi-Methodology Support**: 3+ methodologies working simultaneously (ClinGen, GenCC, Qualitative engines operational)
- [x] **Zero-Code Deployment**: New schemas deployable via configuration (schema repository system operational)
- [ ] **Performance**: Sub-200ms response times for all scope-based operations (needs performance testing)
- [x] **Maintainability**: 75% reduction in methodology-specific code (pluggable architecture implemented)

### Scientific Success  
- [x] **ClinGen Compliance**: Full SOP v11 support maintained within scope-based workflow
- [ ] **GenCC Support**: Complete classification capability across clinical specialties
- [x] **4-Eyes Principle**: Independent peer review mandatory before activation
- [ ] **Expert Validation**: Positive feedback from scientific users across different scopes
- [x] **Data Integrity**: 100% audit trail and provenance tracking with reviewer attribution
- [x] **Quality Assurance**: Mandatory independent review with different reviewer validation

### User Success
- [x] **Scope-Based Navigation**: Users can work within their clinical specialty domains
- [x] **Multi-Stage Workflow**: Clear progression through all workflow stages
- [ ] **Intuitive Interface**: Users can switch methodologies seamlessly within scopes
- [ ] **Reduced Effort**: 25% reduction in curation time through improved workflow
- [ ] **Consistency**: Improved data quality through multi-stage validation and peer review
- [x] **Flexibility**: Institutions can organize by clinical specialties and customize methodologies
- [x] **Collaborative**: 4-eyes principle enables effective peer review and knowledge sharing

## Risk Mitigation

### High-Priority Risks
1. **Schema Complexity**: Start with simple schemas, build complexity gradually
2. **Performance Concerns**: Early benchmarking of JSONB queries
3. **User Adoption**: Maintain familiar interfaces while adding flexibility

### Medium-Priority Risks
1. **Migration Complexity**: Comprehensive testing and validation procedures
2. **Methodology Accuracy**: Expert review of all implementations
3. **System Integration**: Clear API contracts and version management

## Getting Started

### For Schema Development
1. Read `SCHEMA_SPECIFICATIONS.md` for technical format
2. Study `METHODOLOGY_EXAMPLES.md` for real implementations
3. Follow `SCORING_ENGINE_GUIDE.md` for plugin development

### For Database Work
1. Review `database/flexible_schema_design.md`
2. Study `database/performance_optimization.md`
3. Implement from `database/sql/` scripts

### For API Development
1. Read `backend/schema_management_api.md`
2. Study `backend/scoring_engine_registry.md`  
3. Follow `backend/implementation/` guides

### For Frontend Development
1. Review `frontend/dynamic_form_generation.md`
2. Study `frontend/real_time_scoring.md`
3. Follow `frontend/implementation/` guides

## Integration Philosophy

The schema-agnostic architecture creates a **universal curation platform** where:

- **Scientists** can use any established methodology or create custom approaches
- **Institutions** can adapt the platform to their specific standards and requirements
- **Developers** can add new methodologies through configuration rather than coding
- **The Platform** remains relevant as scientific practices evolve and new methodologies emerge

This represents a fundamental shift from building a ClinGen tool to building **the platform that can support ClinGen and everything else**.

---

*This plan transforms Gene Curator from a methodology-specific tool into a universal platform for scientific curation that adapts to any approach through the power of schema-driven architecture.*