# Gene Curator - Database Schema Documentation

## Overview

The Gene Curator database implements a **scope-based, schema-agnostic** PostgreSQL design that supports any curation methodology through flexible JSONB storage, multi-stage workflows, and clinical specialty organization. This document provides comprehensive details of the database design that enables methodology flexibility and rigorous quality assurance through 4-eyes principle review.

## Schema Design Principles

1. **Scope-Based Organization**: Clinical specialties (kidney-genetics, cardio-genetics) organize all curation work
2. **Multi-Stage Workflow**: 5-stage pipeline (entry → precuration → curation → review → active status)
3. **Quality Assurance**: 4-eyes principle with mandatory peer review before activation
4. **Methodology Agnostic**: No curation approach is privileged or hard-coded
5. **Flexible Evidence Storage**: JSONB adapts to any evidence structure with draft states
6. **Schema-Driven Validation**: Rules defined in schema configurations, not database constraints
7. **Immutable Provenance**: Every record is content-addressable and verifiable
8. **Performance Optimized**: Efficient indexing for scope-based queries and multi-curation management

## Core Schema Tables

### 1. Scopes Table (Clinical Specialty Organization)

```sql
CREATE TABLE scopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,              -- kidney-genetics, cardio-genetics, etc.
    display_name VARCHAR(255) NOT NULL,             -- "Kidney Genetics", "Cardio Genetics"
    description TEXT,
    
    -- Scope configuration
    institution VARCHAR(255),                       -- Owning institution
    is_active BOOLEAN DEFAULT true,
    
    -- Default schema preferences for this scope
    default_workflow_pair_id UUID REFERENCES workflow_pairs(id),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_scope_name CHECK (name ~ '^[a-z0-9-]+$')
);
```

**Key Features:**
- **Clinical Specialty Organization**: Each scope represents a clinical domain
- **Institution Support**: Scopes can be institution-specific or shared
- **Default Schemas**: Each scope can have preferred methodology defaults
- **Naming Convention**: Enforced lowercase-hyphen format for consistency

### 2. Users Table (RBAC Foundation)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer', -- viewer|curator|admin
    institution VARCHAR(255),                  -- User's institutional affiliation
    is_active BOOLEAN DEFAULT true,
    
    -- Scope assignments (users can work in multiple scopes)
    assigned_scopes UUID[] DEFAULT '{}',       -- Array of scope_ids user can access
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);
```

**Key Features:**
- **Role-Based Access Control**: `viewer` (read-only), `curator` (create/edit), `admin` (all permissions)
- **Scope-Based Access**: Users assigned to specific clinical specialties
- **Multi-Scope Support**: Users can work across multiple clinical domains
- **Institutional Affiliation**: Links users to organizations for schema preferences
- **JWT Integration**: Works with FastAPI Security for token-based auth

### 3. Curation Schemas Table (Methodology Definitions)

```sql
CREATE TABLE curation_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    schema_type schema_type NOT NULL, -- precuration|curation|combined
    
    -- Complete schema definition (JSONB)
    field_definitions JSONB NOT NULL,      -- What data to collect
    validation_rules JSONB NOT NULL,       -- How to validate data
    scoring_configuration JSONB,           -- How to calculate scores/verdicts
    workflow_states JSONB NOT NULL,        -- State machine definition
    ui_configuration JSONB NOT NULL,       -- How to render forms
    
    -- Metadata
    description TEXT,
    institution VARCHAR(255),              -- Institutional ownership
    based_on_schema UUID REFERENCES curation_schemas(id), -- Schema inheritance
    
    -- Audit
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(name, version)
);
```

**Key Features:**
- **Methodology Storage**: Complete definition of any curation approach
- **Version Control**: Full versioning for schema evolution
- **Schema Inheritance**: Base schemas can be extended for customization
- **Institution Support**: Organizations can have private schemas

### 4. Workflow Pairs Table (Schema Combinations)

```sql
CREATE TABLE workflow_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    
    -- Schema pairing
    precuration_schema_id UUID REFERENCES curation_schemas(id),
    curation_schema_id UUID REFERENCES curation_schemas(id),
    
    -- Data flow configuration
    data_mapping JSONB NOT NULL,           -- How precuration data flows to curation
    
    -- Metadata
    description TEXT,
    institution VARCHAR(255),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(name, version)
);
```

**Key Features:**
- **Schema Pairing**: Combines precuration + curation methodologies
- **Data Flow**: Defines how data moves between workflow stages
- **Reusability**: Same schemas can be paired in different combinations

### 5. Schema Selections Table (User Preferences)

```sql
CREATE TABLE schema_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    institution VARCHAR(255),
    workflow_pair_id UUID REFERENCES workflow_pairs(id),
    is_default BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure only one default per user
    UNIQUE(user_id, is_default) DEFERRABLE INITIALLY DEFERRED
);
```

### 6. Genes Table (Gene Registry)

```sql
CREATE TABLE genes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hgnc_id VARCHAR(50) UNIQUE NOT NULL,           -- HGNC:12345 format
    approved_symbol VARCHAR(100) NOT NULL,         -- Official gene symbol
    previous_symbols TEXT[],                       -- Array of old symbols
    alias_symbols TEXT[],                          -- Array of aliases
    chromosome VARCHAR(10),                        -- 1-22, X, Y, MT
    location VARCHAR(50),                          -- Chromosomal position
    gene_type VARCHAR(100),                        -- protein_coding, lncRNA, etc.
    
    -- Flexible gene details (methodology-agnostic)
    details JSONB DEFAULT '{}',
    
    -- Provenance & integrity
    record_hash VARCHAR(64) NOT NULL UNIQUE,       -- SHA-256 content hash
    previous_hash VARCHAR(64),                     -- Version chaining
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_hgnc_id CHECK (hgnc_id ~* '^HGNC:[0-9]+$')
);
```

**Key Features:**
- **HGNC Compliance**: Validates HGNC ID format
- **Flexible Details**: JSONB accommodates any gene-specific data
- **Content Integrity**: SHA-256 hashing for verification

### 7. Gene-Scope Assignments Table

```sql
CREATE TABLE gene_scope_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    
    -- Optional curator assignment for this gene-scope combination
    assigned_curator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Assignment metadata
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(gene_id, scope_id)
);
```

**Key Features:**
- **Gene-Scope Pairing**: Links genes to clinical specialties
- **Curator Assignment**: Optional assignment of specific curators to gene-scope combinations
- **Uniqueness**: One assignment per gene-scope pair
- **Audit Trail**: Tracks who assigned genes to scopes and when

### 8. Precurations Table (Multi-Stage Workflow - Stage 1)

```sql
CREATE TABLE precurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    precuration_schema_id UUID NOT NULL REFERENCES curation_schemas(id),
    
    -- Workflow state
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- draft|in_review|completed
    
    -- Flexible evidence storage (schema-driven)
    evidence_data JSONB DEFAULT '{}',
    
    -- Draft management
    is_draft BOOLEAN DEFAULT true,
    auto_saved_at TIMESTAMPTZ,
    
    -- Provenance tracking
    record_hash VARCHAR(64) NOT NULL UNIQUE,
    previous_hash VARCHAR(64),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Ensure multiple precurations per gene-scope are allowed
    -- (no unique constraint on gene_id, scope_id)
    
    FOREIGN KEY (gene_id, scope_id) REFERENCES gene_scope_assignments(gene_id, scope_id)
);
```

**Key Features:**
- **Scope-Based**: Links to specific clinical specialties
- **Multiple Per Gene-Scope**: Allows multiple precurations for the same gene within a scope
- **Draft Management**: Supports save/resume functionality with auto-save timestamps
- **Schema-Driven**: Uses precuration schemas for methodology flexibility
- **Content Integrity**: Immutable records with cryptographic hashing

### 9. Curations Table (Multi-Stage Workflow - Stage 2)

```sql
CREATE TABLE curations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    curation_schema_id UUID NOT NULL REFERENCES curation_schemas(id),
    
    -- Required precuration reference
    precuration_id UUID NOT NULL REFERENCES precurations(id) ON DELETE CASCADE,
    
    -- Workflow state
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- draft|pending_review|completed
    
    -- Flexible evidence storage (schema-driven)
    evidence_data JSONB DEFAULT '{}',
    
    -- Schema-computed results (populated by triggers)
    computed_scores JSONB DEFAULT '{}',
    computed_verdict VARCHAR(100),
    computed_summary TEXT,
    
    -- Draft management
    is_draft BOOLEAN DEFAULT true,
    auto_saved_at TIMESTAMPTZ,
    
    -- Provenance tracking
    record_hash VARCHAR(64) NOT NULL UNIQUE,
    previous_hash VARCHAR(64),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Ensure multiple curations per gene-scope are allowed
    -- (no unique constraint on gene_id, scope_id)
    
    FOREIGN KEY (gene_id, scope_id) REFERENCES gene_scope_assignments(gene_id, scope_id)
);
```

**Key Features:**
- **Precuration Dependency**: Every curation must reference a precuration
- **Scope-Based**: Links to specific clinical specialties
- **Multiple Per Gene-Scope**: Allows multiple curations for the same gene within a scope
- **Schema-Driven Scoring**: Dynamic computation based on methodology
- **Draft Management**: Supports save/resume functionality
- **Content Integrity**: Immutable records with cryptographic hashing

### 10. Reviews Table (Multi-Stage Workflow - 4-Eyes Principle)

```sql
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    
    -- 4-eyes principle: reviewer must be different from curation creator
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    
    -- Review outcome
    status review_status NOT NULL, -- pending|approved|rejected|needs_revision
    review_comments TEXT,
    
    -- Review metadata
    reviewed_at TIMESTAMPTZ,
    review_duration_minutes INTEGER,
    
    -- Audit trail
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure reviewer is different from curation creator
    CONSTRAINT different_reviewer CHECK (
        reviewer_id != (SELECT created_by FROM curations WHERE id = curation_id)
    )
);
```

**Key Features:**
- **4-Eyes Principle**: Enforced different reviewer constraint
- **Review States**: Comprehensive review workflow management
- **Review Tracking**: Duration and detailed comments
- **Quality Assurance**: Mandatory review before curation activation

### 11. Active Curations Table (Multi-Stage Workflow - Active Status Management)

```sql
CREATE TABLE active_curations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    
    -- Active status management
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Previous active curation (for audit trail)
    replaced_curation_id UUID REFERENCES curations(id),
    
    -- Only one active curation per gene-scope
    UNIQUE(gene_id, scope_id),
    
    FOREIGN KEY (gene_id, scope_id) REFERENCES gene_scope_assignments(gene_id, scope_id)
);
```

**Key Features:**
- **One Active Per Scope**: Unique constraint ensures single active curation per gene-scope
- **Activation Tracking**: Complete audit trail of status changes
- **Replacement History**: Links to previously active curations
- **Automatic Archiving**: Previous active curations become archived when new ones are activated

## Database Enums

```sql
-- User roles for RBAC
CREATE TYPE user_role AS ENUM ('viewer', 'curator', 'admin');

-- Schema types
CREATE TYPE schema_type AS ENUM ('precuration', 'curation', 'combined');

-- Review status for 4-eyes principle
CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'needs_revision');
```

**Note**: 
- Verdict enums and workflow status enums are **NOT** defined at database level - they are defined within schema configurations to maintain methodology flexibility
- The `current_stage` enum has been removed as workflow stages are now handled by separate tables
- Draft states and workflow statuses are managed as VARCHAR fields to allow schema-driven customization

## Dynamic Scoring Engine (Schema-Aware Triggers)

### Flexible Scoring Trigger

```sql
CREATE OR REPLACE FUNCTION calculate_dynamic_scores()
RETURNS TRIGGER AS $$
DECLARE
    schema_config JSONB;
    scoring_engine VARCHAR(100);
    scoring_result JSONB;
BEGIN
    -- Get schema configuration for this curation
    SELECT cs.scoring_configuration INTO schema_config
    FROM curation_schemas cs
    WHERE cs.id = NEW.curation_schema_id;
    
    -- Only calculate scores if not in draft mode and has evidence data
    IF NOT NEW.is_draft AND jsonb_typeof(NEW.evidence_data) = 'object' AND NEW.evidence_data != '{}' THEN
        -- Extract scoring engine name
        scoring_engine := schema_config->>'engine';
        
        -- Call appropriate scoring function based on schema
        CASE scoring_engine
            WHEN 'clingen_sop_v11' THEN
                scoring_result := calculate_clingen_scores(NEW.evidence_data, schema_config);
            WHEN 'gencc_based' THEN
                scoring_result := calculate_gencc_scores(NEW.evidence_data, schema_config);
            WHEN 'qualitative_assessment' THEN
                scoring_result := calculate_qualitative_scores(NEW.evidence_data, schema_config);
            WHEN 'custom_institutional' THEN
                scoring_result := calculate_custom_scores(NEW.evidence_data, schema_config);
            ELSE
                RAISE EXCEPTION 'Unknown scoring engine: %', scoring_engine;
        END CASE;
        
        -- Update computed fields with results
        NEW.computed_scores := scoring_result->'scores';
        NEW.computed_verdict := scoring_result->>'verdict';
        NEW.computed_summary := scoring_result->>'summary';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_scores
    BEFORE INSERT OR UPDATE ON curations
    FOR EACH ROW
    EXECUTE FUNCTION calculate_dynamic_scores();
```

### Individual Scoring Function Examples

#### ClinGen SOP v11 Scoring Function

```sql
CREATE OR REPLACE FUNCTION calculate_clingen_scores(evidence_data JSONB, config JSONB)
RETURNS JSONB AS $$
DECLARE
    genetic_score NUMERIC(4,2) := 0.0;
    experimental_score NUMERIC(4,2) := 0.0;
    total_score NUMERIC(4,2);
    verdict TEXT;
    has_contradictory BOOLEAN;
BEGIN
    -- Calculate genetic evidence score (max 12 per SOP v11)
    SELECT COALESCE(SUM((evidence->>'points')::NUMERIC), 0)
    INTO genetic_score
    FROM (
        SELECT evidence FROM jsonb_array_elements(evidence_data->'genetic_evidence'->'case_level_data') AS evidence
        UNION ALL
        SELECT evidence FROM jsonb_array_elements(evidence_data->'genetic_evidence'->'segregation_data') AS evidence
        UNION ALL
        SELECT evidence FROM jsonb_array_elements(evidence_data->'genetic_evidence'->'case_control_data') AS evidence
    ) AS all_genetic;
    
    genetic_score := LEAST(genetic_score, 12.0);
    
    -- Calculate experimental evidence score (max 6 per SOP v11)
    SELECT COALESCE(SUM((evidence->>'points')::NUMERIC), 0)
    INTO experimental_score
    FROM (
        SELECT evidence FROM jsonb_array_elements(evidence_data->'experimental_evidence'->'function') AS evidence
        UNION ALL
        SELECT evidence FROM jsonb_array_elements(evidence_data->'experimental_evidence'->'models') AS evidence
        UNION ALL
        SELECT evidence FROM jsonb_array_elements(evidence_data->'experimental_evidence'->'rescue') AS evidence
    ) AS all_experimental;
    
    experimental_score := LEAST(experimental_score, 6.0);
    
    -- Calculate total score
    total_score := genetic_score + experimental_score;
    
    -- Check for contradictory evidence
    has_contradictory := jsonb_array_length(evidence_data->'contradictory_evidence') > 0;
    
    -- Determine verdict based on ClinGen SOP v11 rules
    IF has_contradictory THEN
        verdict := 'Disputed';
    ELSIF total_score >= 12 THEN
        verdict := 'Definitive';
    ELSIF total_score >= 7 THEN
        verdict := 'Strong';
    ELSIF total_score >= 4 THEN
        verdict := 'Moderate';
    ELSIF total_score >= 1 THEN
        verdict := 'Limited';
    ELSE
        verdict := 'No Known Disease Relationship';
    END IF;
    
    RETURN jsonb_build_object(
        'scores', jsonb_build_object(
            'genetic_evidence_score', genetic_score,
            'experimental_evidence_score', experimental_score,
            'total_score', total_score
        ),
        'verdict', verdict,
        'summary', format('ClinGen SOP v11: Genetic=%s, Experimental=%s, Total=%s → %s', 
            genetic_score, experimental_score, total_score, verdict)
    );
END;
$$ LANGUAGE plpgsql;
```

#### GenCC-Based Scoring Function

```sql
CREATE OR REPLACE FUNCTION calculate_gencc_scores(evidence_data JSONB, config JSONB)
RETURNS JSONB AS $$
DECLARE
    confidence_score NUMERIC(4,2) := 0.0;
    verdict TEXT;
BEGIN
    -- GenCC-based calculation (example implementation)
    SELECT 
        CASE 
            WHEN evidence_data->'clinical_evidence'->>'phenotype_overlap' = 'complete' THEN 3.0
            WHEN evidence_data->'clinical_evidence'->>'phenotype_overlap' = 'partial' THEN 2.0
            ELSE 1.0
        END +
        CASE 
            WHEN evidence_data->'clinical_evidence'->>'inheritance_pattern' = 'consistent' THEN 2.0
            ELSE 0.0
        END +
        COALESCE((evidence_data->'clinical_evidence'->>'population_data')::NUMERIC, 0.0)
    INTO confidence_score;
    
    -- Determine verdict
    IF confidence_score >= 8 THEN
        verdict := 'Definitive';
    ELSIF confidence_score >= 6 THEN
        verdict := 'Strong';
    ELSIF confidence_score >= 4 THEN
        verdict := 'Moderate';
    ELSE
        verdict := 'Limited';
    END IF;
    
    RETURN jsonb_build_object(
        'scores', jsonb_build_object('confidence_score', confidence_score),
        'verdict', verdict,
        'summary', format('GenCC-based: Confidence=%s → %s', confidence_score, verdict)
    );
END;
$$ LANGUAGE plpgsql;
```

## Schema Examples in Database

### ClinGen SOP v11 Schema (Stored in curation_schemas table)

```json
{
  "field_definitions": {
    "genetic_evidence": {
      "type": "object",
      "properties": {
        "case_level_data": {
          "type": "array",
          "item_schema": {
            "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
            "proband_label": {"type": "string", "required": true},
            "variant_type": {"type": "enum", "options": ["null", "missense"]},
            "points": {"type": "number", "min": 0, "max": 2}
          }
        }
      }
    },
    "experimental_evidence": {
      "type": "object",
      "properties": {
        "function": {"type": "array"},
        "models": {"type": "array"},
        "rescue": {"type": "array"}
      }
    }
  },
  "scoring_configuration": {
    "engine": "clingen_sop_v11",
    "max_genetic_score": 12,
    "max_experimental_score": 6,
    "verdicts": {
      "Definitive": {"min_score": 12, "no_contradictory": true},
      "Strong": {"min_score": 7, "max_score": 11, "no_contradictory": true},
      "Moderate": {"min_score": 4, "max_score": 6},
      "Limited": {"min_score": 1, "max_score": 3},
      "No Known Disease Relationship": {"score": 0}
    }
  },
  "workflow_states": {
    "states": ["Draft", "In_Primary_Review", "In_Secondary_Review", "Approved", "Published"],
    "transitions": {
      "Draft": ["In_Primary_Review"],
      "In_Primary_Review": ["Draft", "In_Secondary_Review"],
      "In_Secondary_Review": ["In_Primary_Review", "Approved"],
      "Approved": ["Published"]
    }
  }
}
```

## Database Indexes (Performance Optimization)

### Core Indexes

```sql
-- Scope indexes
CREATE INDEX idx_scopes_name ON scopes(name);
CREATE INDEX idx_scopes_institution ON scopes(institution);
CREATE INDEX idx_scopes_active ON scopes(is_active) WHERE is_active = true;

-- Schema repository indexes
CREATE INDEX idx_schemas_name_version ON curation_schemas(name, version);
CREATE INDEX idx_schemas_institution ON curation_schemas(institution);
CREATE INDEX idx_schemas_active ON curation_schemas(is_active) WHERE is_active = true;

-- Workflow pair indexes
CREATE INDEX idx_workflow_pairs_name ON workflow_pairs(name, version);
CREATE INDEX idx_workflow_pairs_schemas ON workflow_pairs(precuration_schema_id, curation_schema_id);

-- User preference indexes
CREATE INDEX idx_schema_selections_user ON schema_selections(user_id);
CREATE INDEX idx_schema_selections_default ON schema_selections(user_id, is_default) WHERE is_default = true;

-- User scope access indexes
CREATE INDEX idx_users_assigned_scopes ON users USING GIN (assigned_scopes);

-- Gene indexes
CREATE INDEX idx_genes_hgnc_id ON genes(hgnc_id);
CREATE INDEX idx_genes_symbol ON genes(approved_symbol);
CREATE INDEX idx_genes_details_gin ON genes USING GIN (details);

-- Gene-scope assignment indexes
CREATE INDEX idx_gene_scope_assignments_gene ON gene_scope_assignments(gene_id);
CREATE INDEX idx_gene_scope_assignments_scope ON gene_scope_assignments(scope_id);
CREATE INDEX idx_gene_scope_assignments_curator ON gene_scope_assignments(assigned_curator_id);
CREATE INDEX idx_gene_scope_assignments_active ON gene_scope_assignments(is_active) WHERE is_active = true;

-- Precuration indexes (scope-based)
CREATE INDEX idx_precurations_gene_scope ON precurations(gene_id, scope_id);
CREATE INDEX idx_precurations_schema ON precurations(precuration_schema_id);
CREATE INDEX idx_precurations_status ON precurations(status);
CREATE INDEX idx_precurations_creator ON precurations(created_by);
CREATE INDEX idx_precurations_draft ON precurations(is_draft) WHERE is_draft = true;
CREATE INDEX idx_precurations_evidence_gin ON precurations USING GIN (evidence_data);

-- Curation indexes (scope-based)
CREATE INDEX idx_curations_gene_scope ON curations(gene_id, scope_id);
CREATE INDEX idx_curations_precuration ON curations(precuration_id);
CREATE INDEX idx_curations_schema ON curations(curation_schema_id);
CREATE INDEX idx_curations_status ON curations(status);
CREATE INDEX idx_curations_verdict ON curations(computed_verdict);
CREATE INDEX idx_curations_creator ON curations(created_by);
CREATE INDEX idx_curations_draft ON curations(is_draft) WHERE is_draft = true;
CREATE INDEX idx_curations_evidence_gin ON curations USING GIN (evidence_data);
CREATE INDEX idx_curations_scores_gin ON curations USING GIN (computed_scores);

-- Review indexes (4-eyes principle)
CREATE INDEX idx_reviews_curation ON reviews(curation_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id);  
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_reviews_pending ON reviews(status) WHERE status = 'pending';

-- Active curation indexes
CREATE INDEX idx_active_curations_gene_scope ON active_curations(gene_id, scope_id);
CREATE INDEX idx_active_curations_curation ON active_curations(curation_id);
CREATE INDEX idx_active_curations_activated_by ON active_curations(activated_by);
```

### Methodology-Specific Indexes

```sql
-- ClinGen-specific indexes (created when ClinGen schemas are active)
CREATE INDEX idx_curations_clingen_genetic_score 
ON curations ((computed_scores->>'genetic_evidence_score')::numeric)
WHERE curation_schema_id IN (
    SELECT cs.id FROM curation_schemas cs 
    WHERE cs.name LIKE 'ClinGen%'
);

CREATE INDEX idx_curations_clingen_experimental_score 
ON curations ((computed_scores->>'experimental_evidence_score')::numeric)  
WHERE curation_schema_id IN (
    SELECT cs.id FROM curation_schemas cs 
    WHERE cs.name LIKE 'ClinGen%'
);

-- GenCC-specific indexes
CREATE INDEX idx_curations_gencc_confidence_score 
ON curations ((computed_scores->>'confidence_score')::numeric)
WHERE curation_schema_id IN (
    SELECT cs.id FROM curation_schemas cs 
    WHERE cs.name LIKE 'GenCC%'
);

-- Scope-specific performance indexes
CREATE INDEX idx_curations_kidney_genetics_verdict
ON curations (computed_verdict)
WHERE scope_id IN (SELECT id FROM scopes WHERE name = 'kidney-genetics');

CREATE INDEX idx_curations_cardio_genetics_verdict
ON curations (computed_verdict) 
WHERE scope_id IN (SELECT id FROM scopes WHERE name = 'cardio-genetics');
```

## Database Views

### Comprehensive Curation View (Scope-Based)

```sql
CREATE VIEW curations_comprehensive AS
SELECT 
    c.id as curation_id,
    c.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    
    -- Scope information
    c.scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    
    -- Workflow state
    c.status as curation_status,
    c.computed_verdict,
    c.computed_scores,
    c.is_draft,
    
    -- Schema information
    cur_schema.name as curation_schema_name,
    cur_schema.scoring_configuration->>'engine' as scoring_engine,
    
    -- Precuration reference
    c.precuration_id,
    p.status as precuration_status,
    prec_schema.name as precuration_schema_name,
    
    -- Review information
    r.id as review_id,
    r.status as review_status,
    r.reviewer_id,
    reviewer.name as reviewer_name,
    r.reviewed_at,
    
    -- Active status
    ac.id is NOT NULL as is_active,
    ac.activated_at,
    ac.activated_by,
    activator.name as activated_by_name,
    
    -- Metadata
    c.created_at,
    c.updated_at,
    creator.name as created_by_name
FROM curations c
JOIN genes g ON c.gene_id = g.id
JOIN scopes s ON c.scope_id = s.id
JOIN curation_schemas cur_schema ON c.curation_schema_id = cur_schema.id
JOIN precurations p ON c.precuration_id = p.id
JOIN curation_schemas prec_schema ON p.precuration_schema_id = prec_schema.id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN users reviewer ON r.reviewer_id = reviewer.id
LEFT JOIN active_curations ac ON ac.curation_id = c.id
LEFT JOIN users activator ON ac.activated_by = activator.id
LEFT JOIN users creator ON c.created_by = creator.id;
```

### Scope-Based Statistics View

```sql
CREATE VIEW scope_methodology_statistics AS
SELECT 
    s.name as scope_name,
    s.display_name as scope_display_name,
    cur_schema.name as methodology_name,
    cur_schema.scoring_configuration->>'engine' as scoring_engine,
    c.computed_verdict,
    COUNT(*) as curation_count,
    COUNT(*) FILTER (WHERE ac.id IS NOT NULL) as active_curation_count,
    AVG((c.computed_scores->>'total_score')::numeric) as avg_total_score
FROM curations c
JOIN scopes s ON c.scope_id = s.id
JOIN curation_schemas cur_schema ON c.curation_schema_id = cur_schema.id
LEFT JOIN active_curations ac ON ac.curation_id = c.id
WHERE c.computed_verdict IS NOT NULL AND NOT c.is_draft
GROUP BY s.name, s.display_name, cur_schema.name, cur_schema.scoring_configuration->>'engine', c.computed_verdict
ORDER BY scope_name, methodology_name, curation_count DESC;
```

### Review Workflow Statistics

```sql
CREATE VIEW review_workflow_statistics AS
SELECT 
    s.name as scope_name,
    s.display_name as scope_display_name,
    COUNT(c.id) as total_curations,
    COUNT(r.id) as reviewed_curations,
    COUNT(r.id) FILTER (WHERE r.status = 'approved') as approved_curations,
    COUNT(r.id) FILTER (WHERE r.status = 'rejected') as rejected_curations,
    COUNT(r.id) FILTER (WHERE r.status = 'pending') as pending_reviews,
    AVG(r.review_duration_minutes) as avg_review_duration_minutes,
    COUNT(DISTINCT r.reviewer_id) as unique_reviewers
FROM curations c
JOIN scopes s ON c.scope_id = s.id
LEFT JOIN reviews r ON r.curation_id = c.id
WHERE NOT c.is_draft
GROUP BY s.name, s.display_name
ORDER BY scope_name;
```

### Active Curations by Scope

```sql
CREATE VIEW active_curations_by_scope AS
SELECT 
    s.name as scope_name,
    s.display_name as scope_display_name,
    g.approved_symbol,
    g.hgnc_id,
    c.computed_verdict,
    c.computed_scores,
    cur_schema.name as methodology_name,
    ac.activated_at,
    activator.name as activated_by_name,
    creator.name as curator_name
FROM active_curations ac
JOIN curations c ON ac.curation_id = c.id
JOIN genes g ON ac.gene_id = g.id
JOIN scopes s ON ac.scope_id = s.id
JOIN curation_schemas cur_schema ON c.curation_schema_id = cur_schema.id
LEFT JOIN users activator ON ac.activated_by = activator.id
LEFT JOIN users creator ON c.created_by = creator.id
ORDER BY s.name, g.approved_symbol;
```

## Performance Considerations

### JSONB Query Optimization

```sql
-- Efficient JSONB queries using indexes (scope-aware)
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM curations c
JOIN scopes s ON c.scope_id = s.id
WHERE s.name = 'kidney-genetics' 
  AND c.evidence_data @> '{"genetic_evidence": {"case_level_data": [{"points": 2.0}]}}';

-- Use functional indexes for common score queries
CREATE INDEX idx_curations_total_score_computed 
ON curations (((computed_scores->>'total_score')::numeric))
WHERE computed_scores->>'total_score' IS NOT NULL;

-- Scope-specific query optimization
CREATE INDEX idx_curations_scope_verdict_created 
ON curations (scope_id, computed_verdict, created_at DESC);
```

### Scope-Based Caching Strategy

The database design supports application-level caching optimized for scope-based workflows:

1. **Schema Definitions**: Cached after first load, invalidated on schema updates
2. **Scope Configurations**: Cached per scope with default schema preferences
3. **User Scope Access**: Cached per user session for permission checks
4. **Active Curations**: Cached per scope for fast active status lookups
5. **Draft States**: Cached temporarily for auto-save functionality
6. **Review Assignments**: Cached for pending review notifications

## Migration Strategy

### From ClinGen-Centric to Scope-Based Schema-Agnostic

1. **Create Scope Infrastructure**: New tables for scopes, gene-scope assignments, multi-stage workflow
2. **Establish Schema Repository**: Convert existing ClinGen logic to schema definitions
3. **Create Default Scope**: Set up initial clinical specialty (e.g., 'kidney-genetics')
4. **Migrate Gene Data**: Convert to scope-based assignments
5. **Transform Workflow**: Split existing curations into precurations and curations
6. **Implement Review System**: Add 4-eyes principle with review tracking
7. **Update Triggers**: Replace fixed scoring with scope-aware dynamic scoring
8. **Validate Continuity**: Ensure existing functionality is preserved

### Data Migration Script Example

```sql
-- Step 1: Create default scope for existing work
INSERT INTO scopes (name, display_name, description, is_active)
VALUES (
    'kidney-genetics',
    'Kidney Genetics',
    'Default scope for existing ClinGen kidney genetics curations',
    true
);

-- Step 2: Create ClinGen schema definitions
INSERT INTO curation_schemas (name, version, schema_type, field_definitions, scoring_configuration, workflow_states, ui_configuration, description)
VALUES 
(
    'ClinGen_SOP_v11_Precuration',
    '1.0.0',
    'precuration',
    '{"initial_assessment": {...}}',  -- ClinGen precuration fields
    '{}',  -- No scoring for precurations
    '{"states": ["draft", "in_review", "completed"]}',
    '{"layout": {...}}',
    'ClinGen SOP v11 Precuration Schema'
),
(
    'ClinGen_SOP_v11_Curation',
    '1.0.0',
    'curation',
    '{"genetic_evidence": {...}, "experimental_evidence": {...}}',  -- Full ClinGen fields
    '{"engine": "clingen_sop_v11", ...}',  -- ClinGen scoring config
    '{"states": ["draft", "pending_review", "completed"]}',
    '{"layout": {...}}',
    'ClinGen SOP v11 Curation Schema'
);

-- Step 3: Assign all existing genes to default scope
INSERT INTO gene_scope_assignments (gene_id, scope_id, assigned_at, is_active)
SELECT 
    g.id,
    s.id,
    NOW(),
    true
FROM genes g
CROSS JOIN scopes s
WHERE s.name = 'kidney-genetics';

-- Step 4: Create precurations from existing curation data
INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, evidence_data, status, is_draft, created_by, created_at)
SELECT 
    c.gene_id,
    s.id,
    ps.id,
    jsonb_extract_path(c.precuration_data, 'initial_assessment'),  -- Extract precuration subset
    'completed',
    false,
    c.created_by,
    c.created_at
FROM curations c  -- Old curations table
CROSS JOIN scopes s
JOIN curation_schemas ps ON ps.name = 'ClinGen_SOP_v11_Precuration'
WHERE s.name = 'kidney-genetics'
  AND c.precuration_data != '{}';

-- Step 5: Transform existing curations to new structure
INSERT INTO curations (gene_id, scope_id, curation_schema_id, precuration_id, evidence_data, computed_scores, computed_verdict, computed_summary, status, is_draft, created_by, created_at)
SELECT 
    old_c.gene_id,
    s.id,
    cs.id,
    p.id,
    old_c.curation_data,
    old_c.computed_scores,
    old_c.computed_verdict,
    old_c.computed_summary,
    'completed',
    false,
    old_c.created_by,
    old_c.created_at
FROM curations old_c  -- Old curations table
CROSS JOIN scopes s
JOIN curation_schemas cs ON cs.name = 'ClinGen_SOP_v11_Curation'
JOIN precurations p ON p.gene_id = old_c.gene_id AND p.scope_id = s.id
WHERE s.name = 'kidney-genetics'
  AND old_c.curation_data != '{}';

-- Step 6: Set active status for completed curations
INSERT INTO active_curations (gene_id, scope_id, curation_id, activated_at, activated_by)
SELECT 
    c.gene_id,
    c.scope_id,
    c.id,
    c.created_at,
    c.created_by
FROM curations c
WHERE c.status = 'completed' 
  AND c.computed_verdict IS NOT NULL;
```

## Conclusion

This database design provides the foundation for a **scope-based, schema-agnostic** curation platform that can adapt to any scientific methodology while maintaining:

- **Clinical Specialty Organization**: Scopes enable specialized teams to work efficiently
- **Quality Assurance**: 4-eyes principle ensures rigorous peer review
- **Workflow Flexibility**: Multi-stage pipeline supports complex curation processes
- **Methodology Freedom**: Schema-driven approach accommodates any curation approach
- **Data Integrity**: Complete audit trails with immutable provenance tracking
- **Performance**: Optimized indexing for scope-based queries and multi-curation management
- **Scalability**: Architecture supports unlimited scopes, methodologies, and concurrent workflows

The platform becomes truly **methodology-agnostic and workflow-comprehensive**: as flexible as science itself, as rigorous as clinical practice demands.