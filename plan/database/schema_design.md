# PostgreSQL Schema Design - Scope-Based Multi-Stage Workflow

## Overview

This schema design implements a comprehensive scope-based, multi-stage curation workflow that organizes work by clinical specialties while supporting any scientific methodology through configurable schemas. The design enables 5-stage workflow management with 4-eyes principle quality assurance.

## Core Design Principles

1. **Scope-Based Organization**: Clinical specialty domains (kidney-genetics, cardio-genetics, etc.) as first-class entities
2. **Multi-Stage Workflow**: 5-stage pipeline (Entry → Precuration → Curation → Review → Active Status)
3. **4-Eyes Principle**: Mandatory independent peer review with different reviewer validation
4. **Multi-Curation Support**: Multiple curations per gene-scope with active/archived status management
5. **Schema-Agnostic Storage**: JSONB evidence storage adapting to any methodology within scope context
6. **Complete Audit Trail**: Immutable records with full provenance and reviewer tracking
7. **Performance Optimization**: Scope-based indexing and query optimization

## Database Schema

### Enum Types

```sql
-- User roles for scope-based RBAC
CREATE TYPE user_role AS ENUM ('viewer', 'curator', 'admin');

-- Workflow stage tracking
CREATE TYPE workflow_stage AS ENUM ('entry', 'precuration', 'curation', 'review', 'active');

-- Review status for 4-eyes principle
CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'needs_revision');

-- Curation status within workflow
CREATE TYPE curation_status AS ENUM ('draft', 'pending_review', 'approved', 'rejected', 'active', 'archived');

-- Schema types for workflow pairing
CREATE TYPE schema_type AS ENUM ('precuration', 'curation', 'combined');
```

### Core Tables

#### Users Table (Enhanced with Scope Assignment)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role user_role NOT NULL DEFAULT 'viewer',
    institution VARCHAR(255),
    assigned_scopes UUID[], -- Array of scope IDs user can access
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_institution ON users(institution);
CREATE INDEX idx_users_assigned_scopes ON users USING GIN (assigned_scopes);
```

#### Scopes Table (Clinical Specialties)
```sql
CREATE TABLE scopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,              -- kidney-genetics, cardio-genetics, etc.
    display_name VARCHAR(255) NOT NULL,             -- "Kidney Genetics", "Cardio Genetics"
    description TEXT,
    institution VARCHAR(255),                       -- Owning institution
    is_active BOOLEAN DEFAULT true,
    default_workflow_pair_id UUID,                  -- Will reference workflow_pairs(id)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT valid_scope_name CHECK (name ~ '^[a-z0-9-]+$')
);

CREATE INDEX idx_scopes_name ON scopes(name);
CREATE INDEX idx_scopes_institution ON scopes(institution);
CREATE INDEX idx_scopes_active ON scopes(is_active) WHERE is_active = true;
```

#### Schema Management Tables
```sql
-- Curation methodology schemas
CREATE TABLE curation_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    schema_type schema_type NOT NULL,
    
    -- Complete schema definition
    field_definitions JSONB NOT NULL,
    validation_rules JSONB NOT NULL,
    scoring_configuration JSONB,
    workflow_states JSONB NOT NULL,
    ui_configuration JSONB NOT NULL,
    
    -- Metadata
    description TEXT,
    institution VARCHAR(255),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(name, version)
);

-- Workflow pairs (precuration + curation schema combinations)
CREATE TABLE workflow_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    
    precuration_schema_id UUID REFERENCES curation_schemas(id),
    curation_schema_id UUID REFERENCES curation_schemas(id),
    
    -- How data flows between stages
    data_mapping JSONB NOT NULL,
    
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Add foreign key constraint to scopes after workflow_pairs is created
ALTER TABLE scopes ADD CONSTRAINT fk_scopes_default_workflow_pair 
    FOREIGN KEY (default_workflow_pair_id) REFERENCES workflow_pairs(id);
```

#### Genes Table (Scope Assignment Ready)
```sql
CREATE TABLE genes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hgnc_id VARCHAR(50) UNIQUE NOT NULL,
    approved_symbol VARCHAR(100) NOT NULL,
    -- Gene details (preserves current flexibility)
    details JSONB DEFAULT '{}',
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_genes_hgnc_id ON genes(hgnc_id);
CREATE INDEX idx_genes_symbol ON genes(approved_symbol);
CREATE INDEX idx_genes_details_gin ON genes USING GIN (details);
```

#### Gene-Scope Assignments Table
```sql
CREATE TABLE gene_scope_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    assigned_curator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(gene_id, scope_id) -- One assignment per gene-scope combination
);

CREATE INDEX idx_gene_scope_assignments_gene ON gene_scope_assignments(gene_id);
CREATE INDEX idx_gene_scope_assignments_scope ON gene_scope_assignments(scope_id);
CREATE INDEX idx_gene_scope_assignments_curator ON gene_scope_assignments(assigned_curator_id);
CREATE INDEX idx_gene_scope_assignments_active ON gene_scope_assignments(is_active) WHERE is_active = true;
```

#### Multi-Stage Workflow Tables

##### Precurations Table (Multiple per Gene-Scope)
```sql
CREATE TABLE precurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    precuration_schema_id UUID NOT NULL REFERENCES curation_schemas(id),
    
    -- Status and workflow
    status curation_status NOT NULL DEFAULT 'draft',
    is_draft BOOLEAN DEFAULT true,
    
    -- Evidence data (schema-agnostic)
    evidence_data JSONB NOT NULL DEFAULT '{}',
    
    -- Auto-save functionality
    auto_saved_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Provenance tracking
    version_number INTEGER DEFAULT 1,
    
    CONSTRAINT precuration_creator_has_scope_access CHECK (
        created_by IS NULL OR 
        EXISTS(SELECT 1 FROM users WHERE id = created_by AND scope_id = ANY(assigned_scopes))
    )
);

CREATE INDEX idx_precurations_gene_scope ON precurations(gene_id, scope_id);
CREATE INDEX idx_precurations_scope ON precurations(scope_id);
CREATE INDEX idx_precurations_status ON precurations(status);
CREATE INDEX idx_precurations_creator ON precurations(created_by);
CREATE INDEX idx_precurations_draft ON precurations(is_draft) WHERE is_draft = true;
CREATE INDEX idx_precurations_evidence_gin ON precurations USING GIN (evidence_data);
```

##### Curations Table (Multiple per Gene-Scope, Requires Precuration)
```sql
CREATE TABLE curations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    precuration_id UUID NOT NULL REFERENCES precurations(id) ON DELETE RESTRICT, -- Must reference precuration
    workflow_pair_id UUID NOT NULL REFERENCES workflow_pairs(id),
    
    -- Status and workflow
    status curation_status NOT NULL DEFAULT 'draft',
    is_draft BOOLEAN DEFAULT true,
    
    -- Evidence data (schema-agnostic)
    evidence_data JSONB NOT NULL DEFAULT '{}',
    
    -- Computed results (updated by triggers based on schema)
    computed_scores JSONB DEFAULT '{}',
    computed_verdict VARCHAR(100),
    computed_summary TEXT,
    
    -- Auto-save functionality
    auto_saved_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Provenance tracking
    version_number INTEGER DEFAULT 1,
    record_hash VARCHAR(64) UNIQUE,
    
    CONSTRAINT curation_creator_has_scope_access CHECK (
        created_by IS NULL OR 
        EXISTS(SELECT 1 FROM users WHERE id = created_by AND scope_id = ANY(assigned_scopes))
    ),
    CONSTRAINT curation_references_completed_precuration CHECK (
        EXISTS(SELECT 1 FROM precurations WHERE id = precuration_id AND status = 'completed')
    )
);

CREATE INDEX idx_curations_gene_scope ON curations(gene_id, scope_id);
CREATE INDEX idx_curations_scope ON curations(scope_id);
CREATE INDEX idx_curations_precuration ON curations(precuration_id);
CREATE INDEX idx_curations_status ON curations(status);
CREATE INDEX idx_curations_creator ON curations(created_by);
CREATE INDEX idx_curations_draft ON curations(is_draft) WHERE is_draft = true;
CREATE INDEX idx_curations_workflow_pair ON curations(workflow_pair_id);
CREATE INDEX idx_curations_verdict ON curations(computed_verdict) WHERE computed_verdict IS NOT NULL;
CREATE INDEX idx_curations_evidence_gin ON curations USING GIN (evidence_data);
CREATE INDEX idx_curations_scores_gin ON curations USING GIN (computed_scores);
```

##### Reviews Table (4-Eyes Principle)
```sql
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    
    status review_status NOT NULL DEFAULT 'pending',
    
    -- Review content
    comments TEXT,
    feedback_data JSONB DEFAULT '{}',
    
    -- Review actions
    reviewed_at TIMESTAMPTZ,
    
    -- Metadata
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- 4-eyes principle constraint: reviewer must be different from curation creator
    CONSTRAINT different_reviewer CHECK (
        reviewer_id != (SELECT created_by FROM curations WHERE id = curation_id)
    ),
    
    -- Reviewer must have access to the scope
    CONSTRAINT reviewer_has_scope_access CHECK (
        EXISTS(
            SELECT 1 FROM curations c 
            JOIN users u ON u.id = reviewer_id 
            WHERE c.id = curation_id AND c.scope_id = ANY(u.assigned_scopes)
        )
    )
);

CREATE INDEX idx_reviews_curation ON reviews(curation_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id);
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_reviews_assigned ON reviews(assigned_at);
```

##### Active Curations Table (One Active per Gene-Scope)
```sql
CREATE TABLE active_curations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    
    -- Activation details
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Previous active curation (for audit trail)
    replaced_curation_id UUID REFERENCES curations(id) ON DELETE SET NULL,
    
    -- Archive information
    archived_at TIMESTAMPTZ,
    archived_by UUID REFERENCES users(id) ON DELETE SET NULL,
    archive_reason TEXT,
    
    -- Ensure only one active curation per gene-scope
    UNIQUE(gene_id, scope_id) DEFERRABLE INITIALLY DEFERRED,
    
    -- Curation must be approved before activation
    CONSTRAINT curation_must_be_approved CHECK (
        EXISTS(SELECT 1 FROM curations WHERE id = curation_id AND status = 'approved')
    )
);

CREATE INDEX idx_active_curations_gene_scope ON active_curations(gene_id, scope_id);
CREATE INDEX idx_active_curations_scope ON active_curations(scope_id);
CREATE INDEX idx_active_curations_curation ON active_curations(curation_id);
CREATE INDEX idx_active_curations_activated ON active_curations(activated_at);
CREATE INDEX idx_active_curations_current ON active_curations(archived_at) WHERE archived_at IS NULL;
```

#### Audit Trail Table
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL, -- 'gene', 'precuration', 'curation', 'review', 'active_curation'
    entity_id UUID NOT NULL,
    scope_id UUID REFERENCES scopes(id),
    operation TEXT NOT NULL, -- 'CREATE', 'UPDATE', 'SUBMIT', 'APPROVE', 'REJECT', 'ACTIVATE', 'ARCHIVE'
    changes JSONB, -- Detailed change information
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    
    -- Additional context for multi-stage workflow
    workflow_stage workflow_stage,
    review_action review_status
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_scope ON audit_log(scope_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);
CREATE INDEX idx_audit_log_workflow_stage ON audit_log(workflow_stage);
```

## Triggers and Functions

### Automatic Scoring Trigger (Schema-Aware)
```sql
CREATE OR REPLACE FUNCTION calculate_dynamic_scores()
RETURNS TRIGGER AS $$
DECLARE
    schema_config JSONB;
    scoring_engine VARCHAR(100);
    scoring_result JSONB;
    scope_context JSONB;
BEGIN
    -- Get scope context and scoring configuration
    SELECT 
        cs.scoring_configuration,
        json_build_object(
            'scope_name', s.name,
            'scope_display_name', s.display_name,
            'institution', s.institution
        )
    INTO schema_config, scope_context
    FROM curation_schemas cs
    JOIN workflow_pairs wp ON wp.curation_schema_id = cs.id
    JOIN scopes s ON s.id = NEW.scope_id
    WHERE wp.id = NEW.workflow_pair_id;
    
    scoring_engine := schema_config->>'engine';
    
    -- Call methodology-specific scoring function with scope context
    CASE scoring_engine
        WHEN 'clingen_sop_v11' THEN
            NEW.computed_scores := calculate_clingen_scores(
                NEW.evidence_data, 
                schema_config, 
                scope_context
            );
        WHEN 'gencc_based' THEN
            NEW.computed_scores := calculate_gencc_scores(
                NEW.evidence_data, 
                schema_config, 
                scope_context
            );
        WHEN 'qualitative_assessment' THEN
            NEW.computed_scores := calculate_qualitative_scores(
                NEW.evidence_data, 
                schema_config, 
                scope_context
            );
        ELSE
            RAISE EXCEPTION 'Unknown scoring engine: % for scope: %', 
                scoring_engine, scope_context->>'scope_name';
    END CASE;
    
    -- Extract computed verdict and summary
    NEW.computed_verdict := NEW.computed_scores->>'verdict';
    NEW.computed_summary := NEW.computed_scores->>'summary';
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_scores
    BEFORE INSERT OR UPDATE ON curations
    FOR EACH ROW
    EXECUTE FUNCTION calculate_dynamic_scores();
```

### Content Hash Generation (Enhanced for Scope Context)
```sql
CREATE OR REPLACE FUNCTION generate_record_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.record_hash := encode(
        digest(
            NEW.gene_id::text || 
            NEW.scope_id::text ||
            NEW.precuration_id::text ||
            NEW.evidence_data::text ||
            EXTRACT(epoch FROM NEW.created_at)::text,
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_hash
    BEFORE INSERT ON curations
    FOR EACH ROW
    EXECUTE FUNCTION generate_record_hash();
```

### Audit Logging Trigger
```sql
CREATE OR REPLACE FUNCTION log_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    operation_type TEXT;
    entity_scope_id UUID;
BEGIN
    -- Determine operation type
    IF TG_OP = 'INSERT' THEN
        operation_type := 'CREATE';
    ELSIF TG_OP = 'UPDATE' THEN
        operation_type := 'UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        operation_type := 'DELETE';
    END IF;
    
    -- Get scope_id based on table
    IF TG_TABLE_NAME = 'curations' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
    ELSIF TG_TABLE_NAME = 'precurations' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
    END IF;
    
    INSERT INTO audit_log (
        entity_type,
        entity_id,
        scope_id,
        operation,
        changes,
        user_id
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        entity_scope_id,
        operation_type,
        CASE 
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)
            ELSE to_jsonb(NEW)
        END,
        COALESCE(NEW.updated_by, OLD.updated_by, NEW.created_by, OLD.created_by)
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Apply audit trigger to key tables
CREATE TRIGGER trigger_audit_curations
    AFTER INSERT OR UPDATE OR DELETE ON curations
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

CREATE TRIGGER trigger_audit_precurations
    AFTER INSERT OR UPDATE OR DELETE ON precurations
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

CREATE TRIGGER trigger_audit_reviews
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();
```

## Views for Common Queries

### Complete Multi-Stage Workflow View
```sql
CREATE VIEW workflow_complete AS
SELECT 
    gsa.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    gsa.scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    
    -- Precuration counts
    COUNT(DISTINCT p.id) as precuration_count,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'completed') as completed_precuration_count,
    
    -- Curation counts
    COUNT(DISTINCT c.id) as curation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'draft') as draft_curation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'pending_review') as pending_review_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'approved') as approved_curation_count,
    
    -- Review status
    COUNT(DISTINCT r.id) as review_count,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'pending') as pending_review_count,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'approved') as approved_review_count,
    
    -- Active status
    ac.curation_id as active_curation_id,
    ac.activated_at as activated_at
    
FROM gene_scope_assignments gsa
JOIN genes g ON gsa.gene_id = g.id
JOIN scopes s ON gsa.scope_id = s.id
LEFT JOIN precurations p ON p.gene_id = gsa.gene_id AND p.scope_id = gsa.scope_id
LEFT JOIN curations c ON c.gene_id = gsa.gene_id AND c.scope_id = gsa.scope_id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN active_curations ac ON ac.gene_id = gsa.gene_id AND ac.scope_id = gsa.scope_id AND ac.archived_at IS NULL
WHERE gsa.is_active = true
GROUP BY gsa.gene_id, g.approved_symbol, g.hgnc_id, gsa.scope_id, s.name, s.display_name, ac.curation_id, ac.activated_at;
```

### Scope-Based Statistics View
```sql
CREATE VIEW scope_statistics AS
SELECT 
    s.id as scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    s.institution,
    
    -- Gene assignments
    COUNT(DISTINCT gsa.gene_id) as gene_count,
    
    -- Workflow stage counts
    COUNT(DISTINCT p.id) as precuration_count,
    COUNT(DISTINCT c.id) as curation_count,
    COUNT(DISTINCT r.id) as review_count,
    COUNT(DISTINCT ac.id) as active_curation_count,
    
    -- Status breakdowns
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'draft') as draft_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'pending_review') as pending_review_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'approved') as approved_count,
    
    -- Curator activity
    COUNT(DISTINCT gsa.assigned_curator_id) as curator_count,
    COUNT(DISTINCT r.reviewer_id) as reviewer_count
    
FROM scopes s
LEFT JOIN gene_scope_assignments gsa ON s.id = gsa.scope_id AND gsa.is_active = true
LEFT JOIN precurations p ON p.scope_id = s.id
LEFT JOIN curations c ON c.scope_id = s.id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN active_curations ac ON ac.scope_id = s.id AND ac.archived_at IS NULL
WHERE s.is_active = true
GROUP BY s.id, s.name, s.display_name, s.institution;
```

### 4-Eyes Principle Compliance View
```sql
CREATE VIEW review_compliance AS
SELECT 
    c.id as curation_id,
    c.gene_id,
    c.scope_id,
    s.name as scope_name,
    c.created_by as curator_id,
    creator.name as curator_name,
    r.reviewer_id,
    reviewer.name as reviewer_name,
    r.status as review_status,
    
    -- 4-eyes compliance check
    CASE 
        WHEN r.reviewer_id IS NULL THEN 'No Reviewer Assigned'
        WHEN r.reviewer_id = c.created_by THEN 'VIOLATION: Same Person'
        WHEN r.status = 'approved' THEN 'Compliant'
        WHEN r.status = 'pending' THEN 'Pending Review'
        ELSE 'Under Review'
    END as compliance_status,
    
    c.status as curation_status,
    r.assigned_at,
    r.reviewed_at
    
FROM curations c
JOIN scopes s ON c.scope_id = s.id
LEFT JOIN users creator ON c.created_by = creator.id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN users reviewer ON r.reviewer_id = reviewer.id
WHERE c.status IN ('pending_review', 'approved', 'active');
```

## Performance Considerations

1. **Scope-Based Indexing**: Optimized indexes for scope-filtered queries
2. **Multi-Stage Indexes**: Composite indexes for workflow stage relationships
3. **JSONB Performance**: GIN indexes on evidence structures and computed scores
4. **Active Curation Constraint**: Unique constraint ensuring one active per gene-scope
5. **Review Assignment Optimization**: Indexes supporting 4-eyes principle queries
6. **Audit Trail Partitioning**: Consider partitioning audit_log by timestamp for large volumes

## Migration Strategy

1. **Clean Architecture Approach**: Fresh implementation designed for scope-based workflow
2. **Data Migration**: Transform existing data to multi-stage, scope-based structure
3. **Schema Validation**: Ensure all existing methodologies work within scope context
4. **4-Eyes Principle Setup**: Establish reviewer assignments and compliance validation
5. **Active Status Migration**: Identify and migrate current active curations
6. **Performance Testing**: Validate query performance across scopes and workflow stages

## Next Steps

1. Implement comprehensive SQL migration scripts
2. Create scope setup and management procedures
3. Build 4-eyes principle validation and assignment tools
4. Develop performance testing procedures for multi-stage queries
5. Document scope-based administration and user management processes

This schema design enables a comprehensive scope-based, multi-stage curation platform that maintains scientific rigor through the 4-eyes principle while providing the flexibility to support any clinical specialty using any scientific methodology.