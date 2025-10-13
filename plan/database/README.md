# Database Structure Plan - PostgreSQL Migration

This directory contains the database design and migration plan for transitioning from Firebase Firestore to PostgreSQL with ClinGen SOP v11 compliance.

## Work Stream Overview

**Objective**: Design and implement a hybrid PostgreSQL schema that directly implements ClinGen SOP v11 requirements while maintaining the flexibility of the current configuration-driven workflow system.

**Key Innovations**:
- Native ClinGen evidence scoring in the database layer
- Automated summary generation from structured evidence
- Verifiable provenance tracking for scientific rigor
- Configuration-driven workflow preservation

## Directory Structure

```
database/
├── README.md                    # This overview
├── schema_design.md            # Complete PostgreSQL schema with ClinGen support
├── migration_plan.md           # Firebase to PostgreSQL migration strategy
├── clingen_compliance.md       # ClinGen SOP v11 implementation details
├── sql/
│   ├── 001_initial_schema.sql  # Core tables and types
│   ├── 002_clingen_enums.sql   # ClinGen-specific enums and constraints
│   ├── 003_indexes.sql         # Performance indexes for complex queries
│   └── 004_triggers.sql        # Automatic scoring and validation triggers
└── migration/
    ├── firebase_export.py      # Firebase data export script
    ├── data_transform.py       # Transform Firebase data to PostgreSQL
    └── validation.py           # Validate migrated data integrity
```

## Key Features

### 1. ClinGen Native Support
- **Evidence Scoring**: Automatic calculation of genetic and experimental evidence scores
- **Verdict Classification**: Algorithmic determination of curation verdicts
- **Summary Generation**: Template-driven evidence summary creation
- **Nomenclature Validation**: ClinGen dyadic naming convention support

### 2. Scientific Rigor
- **Immutable Records**: Append-only change tracking
- **Content Addressing**: SHA-256 hashes for tamper-evident records
- **Provenance Tracking**: Complete audit trail with cryptographic verification
- **Version Control**: Linked record chains for reproducible science

### 3. Performance Optimization
- **JSONB Indexing**: GIN indexes for complex evidence structure queries
- **Computed Columns**: Automatic score calculation with stored results
- **Query Optimization**: Specialized indexes for ClinGen-specific searches

## Dependencies

- **Source Data**: Current Firebase Firestore collections (genes, precurations, curations)
- **ClinGen Reference**: Official SOP v11 and Evidence Summary Template v5.1
- **Configuration Preservation**: Existing workflow configs in `src/config/workflows/`

## Work Stream Status

- [x] Requirements analysis from original plan
- [ ] Schema design documentation
- [ ] Migration strategy development
- [ ] SQL implementation
- [ ] Validation scripts

## Next Steps

1. Extract schema design from original plan → `schema_design.md`
2. Create detailed migration strategy → `migration_plan.md`
3. Document ClinGen compliance implementation → `clingen_compliance.md`
4. Implement SQL scripts in `sql/` directory
5. Build migration tooling in `migration/` directory

## Integration Points

- **API Work Stream**: Database schema informs FastAPI model design
- **Frontend Work Stream**: ClinGen evidence structure drives UI component design
- **Original Firebase**: Reference implementation for data structure mapping