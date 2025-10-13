-- Gene Curator Database Schema
-- Methodology-Agnostic Curation Platform with Scope-Based Multi-Stage Workflow
-- PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set search path
SET search_path TO public;

-- ========================================
-- ENUM TYPES FOR METHODOLOGY-AGNOSTIC ARCHITECTURE
-- ========================================

-- Enhanced user roles for scope-based RBAC
CREATE TYPE user_role_new AS ENUM ('viewer', 'curator', 'reviewer', 'admin', 'scope_admin');

-- Workflow stage tracking for multi-stage pipeline
CREATE TYPE workflow_stage AS ENUM ('entry', 'precuration', 'curation', 'review', 'active');

-- Review status for 4-eyes principle
CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'needs_revision');

-- Curation status within multi-stage workflow
CREATE TYPE curation_status AS ENUM ('draft', 'submitted', 'in_review', 'approved', 'rejected', 'active', 'archived');

-- Schema types for workflow pairing
CREATE TYPE schema_type AS ENUM ('precuration', 'curation', 'combined');

-- ========================================
-- CORE METHODOLOGY-AGNOSTIC TABLES
-- ========================================

-- Scopes Table (Clinical Specialties as First-Class Entities)
CREATE TABLE scopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,              -- kidney-genetics, cardio-genetics, etc.
    display_name VARCHAR(255) NOT NULL,             -- "Kidney Genetics", "Cardio Genetics"
    description TEXT,
    institution VARCHAR(255),                       -- Owning institution
    is_active BOOLEAN DEFAULT true,
    default_workflow_pair_id UUID,                  -- Will reference workflow_pairs(id)
    
    -- Configuration
    scope_config JSONB DEFAULT '{}',                -- Scope-specific configuration
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,                                -- Will reference users(id)
    
    CONSTRAINT valid_scope_name CHECK (name ~ '^[a-z0-9-]+$')
);

-- Enhanced Users Table with Scope Assignment
CREATE TABLE users_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role_new NOT NULL DEFAULT 'viewer',
    institution VARCHAR(255),
    assigned_scopes UUID[],                         -- Array of scope IDs user can access
    
    -- Enhanced profile
    orcid_id VARCHAR(50),                          -- ORCID for scientific attribution
    expertise_areas TEXT[],                        -- Areas of expertise
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_orcid CHECK (orcid_id IS NULL OR orcid_id ~ '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$')
);

-- Schema Repository for Methodology Definitions
CREATE TABLE curation_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    schema_type schema_type NOT NULL,
    
    -- Complete schema definition
    field_definitions JSONB NOT NULL,
    validation_rules JSONB NOT NULL DEFAULT '{}',
    scoring_configuration JSONB,
    workflow_states JSONB NOT NULL,
    ui_configuration JSONB NOT NULL,
    
    -- Inheritance support
    based_on_schema_id UUID REFERENCES curation_schemas(id),
    
    -- Metadata
    description TEXT,
    institution VARCHAR(255),
    created_by UUID,                               -- Will reference users_new(id)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    -- Schema validation checksum
    schema_hash VARCHAR(64) NOT NULL,
    
    UNIQUE(name, version)
);

-- Workflow Pairs (Precuration + Curation Schema Combinations)
CREATE TABLE workflow_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    
    precuration_schema_id UUID REFERENCES curation_schemas(id),
    curation_schema_id UUID REFERENCES curation_schemas(id),
    
    -- How data flows between stages
    data_mapping JSONB NOT NULL DEFAULT '{}',
    
    -- Workflow configuration
    workflow_config JSONB DEFAULT '{}',
    
    -- Metadata
    description TEXT,
    created_by UUID,                               -- Will reference users_new(id)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(name, version)
);

-- Enhanced Genes Table (Scope Assignment Ready)
CREATE TABLE genes_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hgnc_id VARCHAR(50) UNIQUE NOT NULL,
    approved_symbol VARCHAR(100) NOT NULL,
    previous_symbols TEXT[],                       -- Array of previous gene symbols
    alias_symbols TEXT[],                          -- Array of alias symbols
    chromosome VARCHAR(10),
    location VARCHAR(50),                          -- Chromosomal location
    
    -- Gene details (preserves current flexibility)
    details JSONB DEFAULT '{}',
    
    -- Provenance tracking
    record_hash VARCHAR(64) NOT NULL UNIQUE,
    previous_hash VARCHAR(64),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,                               -- Will reference users_new(id)
    updated_by UUID,                               -- Will reference users_new(id)
    
    CONSTRAINT valid_hgnc_id CHECK (hgnc_id ~* '^HGNC:[0-9]+$')
);

-- Gene-Scope Assignments (Many-to-Many with Curator Assignment)
CREATE TABLE gene_scope_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL,                         -- Will reference genes_new(id)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    assigned_curator_id UUID,                      -- Will reference users_new(id)
    workflow_pair_id UUID REFERENCES workflow_pairs(id),
    
    -- Assignment details
    is_active BOOLEAN DEFAULT true,
    priority VARCHAR(20) DEFAULT 'normal',         -- high, normal, low
    due_date DATE,
    assignment_notes TEXT,
    
    -- Metadata
    assigned_by UUID,                              -- Will reference users_new(id)
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(gene_id, scope_id) -- One assignment per gene-scope combination
);

-- ========================================
-- MULTI-STAGE WORKFLOW TABLES
-- ========================================

-- Precurations Table (Multiple per Gene-Scope)
CREATE TABLE precurations_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL,                         -- Will reference genes_new(id)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    precuration_schema_id UUID NOT NULL REFERENCES curation_schemas(id),
    
    -- Status and workflow
    status curation_status NOT NULL DEFAULT 'draft',
    workflow_stage workflow_stage NOT NULL DEFAULT 'precuration',
    is_draft BOOLEAN DEFAULT true,
    
    -- Evidence data (schema-agnostic)
    evidence_data JSONB NOT NULL DEFAULT '{}',
    
    -- Computed results from schema
    computed_scores JSONB DEFAULT '{}',
    computed_fields JSONB DEFAULT '{}',
    
    -- Auto-save functionality
    auto_saved_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,                               -- Will reference users_new(id)
    updated_by UUID,                               -- Will reference users_new(id)
    
    -- Provenance tracking
    version_number INTEGER DEFAULT 1,
    record_hash VARCHAR(64) UNIQUE,
    previous_hash VARCHAR(64)
);

-- Curations Table (Multiple per Gene-Scope, Requires Precuration)
CREATE TABLE curations_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL,                         -- Will reference genes_new(id)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    precuration_id UUID,                           -- Will reference precurations_new(id)
    workflow_pair_id UUID NOT NULL REFERENCES workflow_pairs(id),
    
    -- Status and workflow
    status curation_status NOT NULL DEFAULT 'draft',
    workflow_stage workflow_stage NOT NULL DEFAULT 'curation',
    is_draft BOOLEAN DEFAULT true,
    
    -- Evidence data (schema-agnostic)
    evidence_data JSONB NOT NULL DEFAULT '{}',
    
    -- Computed results (updated by scoring engines)
    computed_scores JSONB DEFAULT '{}',
    computed_verdict VARCHAR(100),
    computed_summary TEXT,
    computed_fields JSONB DEFAULT '{}',
    
    -- Auto-save functionality
    auto_saved_at TIMESTAMPTZ,
    
    -- Submission and approval
    submitted_at TIMESTAMPTZ,
    submitted_by UUID,                             -- Will reference users_new(id)
    approved_at TIMESTAMPTZ,
    approved_by UUID,                              -- Will reference users_new(id)
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,                               -- Will reference users_new(id)
    updated_by UUID,                               -- Will reference users_new(id)
    
    -- Provenance tracking
    version_number INTEGER DEFAULT 1,
    record_hash VARCHAR(64) UNIQUE,
    previous_hash VARCHAR(64)
);

-- Reviews Table (4-Eyes Principle Implementation)
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curation_id UUID NOT NULL,                     -- Will reference curations_new(id)
    reviewer_id UUID NOT NULL,                     -- Will reference users_new(id)
    
    status review_status NOT NULL DEFAULT 'pending',
    
    -- Review content
    comments TEXT,
    feedback_data JSONB DEFAULT '{}',
    recommendation VARCHAR(50),                    -- approve, reject, needs_revision
    
    -- Review actions
    reviewed_at TIMESTAMPTZ,
    
    -- Metadata
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID,                              -- Will reference users_new(id)
    due_date DATE,
    
    -- Version tracking for iterative reviews
    review_round INTEGER DEFAULT 1
);

-- Active Curations Table (One Active per Gene-Scope)
CREATE TABLE active_curations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL,                         -- Will reference genes_new(id)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    curation_id UUID NOT NULL,                     -- Will reference curations_new(id)
    
    -- Activation details
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_by UUID,                             -- Will reference users_new(id)
    
    -- Previous active curation (for audit trail)
    replaced_curation_id UUID,                     -- Will reference curations_new(id)
    
    -- Archive information
    archived_at TIMESTAMPTZ,
    archived_by UUID,                              -- Will reference users_new(id)
    archive_reason TEXT,
    
    -- Ensure only one active curation per gene-scope
    UNIQUE(gene_id, scope_id) DEFERRABLE INITIALLY DEFERRED
);

-- ========================================
-- AUDIT AND TRACKING TABLES
-- ========================================

-- Enhanced Audit Log for Multi-Stage Workflow
CREATE TABLE audit_log_new (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,                     -- 'gene', 'precuration', 'curation', 'review', 'active_curation', 'scope'
    entity_id UUID NOT NULL,
    scope_id UUID REFERENCES scopes(id),
    operation TEXT NOT NULL,                       -- 'CREATE', 'UPDATE', 'SUBMIT', 'APPROVE', 'REJECT', 'ACTIVATE', 'ARCHIVE'
    changes JSONB,                                 -- Detailed change information
    user_id UUID,                                  -- Will reference users_new(id)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Additional context
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    
    -- Multi-stage workflow context
    workflow_stage workflow_stage,
    review_action review_status,
    previous_status TEXT,
    new_status TEXT,
    
    -- Schema context
    schema_id UUID REFERENCES curation_schemas(id),
    workflow_pair_id UUID REFERENCES workflow_pairs(id)
);

-- Schema Selection Preferences (User/Institution Schema Choices)
CREATE TABLE schema_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,                                  -- Will reference users_new(id) - NULL for institutional defaults
    scope_id UUID REFERENCES scopes(id),
    institution VARCHAR(255),                      -- For institutional defaults
    
    -- Preferred schemas
    preferred_workflow_pair_id UUID REFERENCES workflow_pairs(id),
    preferred_precuration_schema_id UUID REFERENCES curation_schemas(id),
    preferred_curation_schema_id UUID REFERENCES curation_schemas(id),
    
    -- Selection metadata
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one default per scope per user/institution
    UNIQUE(user_id, scope_id, is_default) DEFERRABLE INITIALLY DEFERRED,
    UNIQUE(institution, scope_id, is_default) DEFERRABLE INITIALLY DEFERRED
);

-- ========================================
-- INDEXES FOR SCOPE-BASED PERFORMANCE
-- ========================================

-- Scopes indexes
CREATE INDEX idx_scopes_name ON scopes(name);
CREATE INDEX idx_scopes_institution ON scopes(institution);
CREATE INDEX idx_scopes_active ON scopes(is_active) WHERE is_active = true;

-- Users indexes
CREATE INDEX idx_users_new_email ON users_new(email);
CREATE INDEX idx_users_new_role ON users_new(role);
CREATE INDEX idx_users_new_institution ON users_new(institution);
CREATE INDEX idx_users_new_assigned_scopes ON users_new USING GIN (assigned_scopes);
CREATE INDEX idx_users_new_active ON users_new(is_active) WHERE is_active = true;

-- Schema repository indexes
CREATE INDEX idx_curation_schemas_name_version ON curation_schemas(name, version);
CREATE INDEX idx_curation_schemas_type ON curation_schemas(schema_type);
CREATE INDEX idx_curation_schemas_institution ON curation_schemas(institution);
CREATE INDEX idx_curation_schemas_active ON curation_schemas(is_active) WHERE is_active = true;
CREATE INDEX idx_curation_schemas_field_definitions ON curation_schemas USING GIN (field_definitions);
CREATE INDEX idx_curation_schemas_scoring_config ON curation_schemas USING GIN (scoring_configuration);

-- Workflow pairs indexes
CREATE INDEX idx_workflow_pairs_name_version ON workflow_pairs(name, version);
CREATE INDEX idx_workflow_pairs_precuration_schema ON workflow_pairs(precuration_schema_id);
CREATE INDEX idx_workflow_pairs_curation_schema ON workflow_pairs(curation_schema_id);
CREATE INDEX idx_workflow_pairs_active ON workflow_pairs(is_active) WHERE is_active = true;

-- Genes indexes
CREATE INDEX idx_genes_new_hgnc_id ON genes_new(hgnc_id);
CREATE INDEX idx_genes_new_symbol ON genes_new(approved_symbol);
CREATE INDEX idx_genes_new_chromosome ON genes_new(chromosome);
CREATE INDEX idx_genes_new_details_gin ON genes_new USING GIN (details);
CREATE INDEX idx_genes_new_created_by ON genes_new(created_by);

-- Gene-scope assignments indexes
CREATE INDEX idx_gene_scope_assignments_gene ON gene_scope_assignments(gene_id);
CREATE INDEX idx_gene_scope_assignments_scope ON gene_scope_assignments(scope_id);
CREATE INDEX idx_gene_scope_assignments_curator ON gene_scope_assignments(assigned_curator_id);
CREATE INDEX idx_gene_scope_assignments_active ON gene_scope_assignments(is_active) WHERE is_active = true;
CREATE INDEX idx_gene_scope_assignments_workflow_pair ON gene_scope_assignments(workflow_pair_id);

-- Precurations indexes
CREATE INDEX idx_precurations_new_gene_scope ON precurations_new(gene_id, scope_id);
CREATE INDEX idx_precurations_new_scope ON precurations_new(scope_id);
CREATE INDEX idx_precurations_new_status ON precurations_new(status);
CREATE INDEX idx_precurations_new_workflow_stage ON precurations_new(workflow_stage);
CREATE INDEX idx_precurations_new_creator ON precurations_new(created_by);
CREATE INDEX idx_precurations_new_draft ON precurations_new(is_draft) WHERE is_draft = true;
CREATE INDEX idx_precurations_new_evidence_gin ON precurations_new USING GIN (evidence_data);
CREATE INDEX idx_precurations_new_schema ON precurations_new(precuration_schema_id);

-- Curations indexes
CREATE INDEX idx_curations_new_gene_scope ON curations_new(gene_id, scope_id);
CREATE INDEX idx_curations_new_scope ON curations_new(scope_id);
CREATE INDEX idx_curations_new_precuration ON curations_new(precuration_id);
CREATE INDEX idx_curations_new_status ON curations_new(status);
CREATE INDEX idx_curations_new_workflow_stage ON curations_new(workflow_stage);
CREATE INDEX idx_curations_new_creator ON curations_new(created_by);
CREATE INDEX idx_curations_new_draft ON curations_new(is_draft) WHERE is_draft = true;
CREATE INDEX idx_curations_new_workflow_pair ON curations_new(workflow_pair_id);
CREATE INDEX idx_curations_new_verdict ON curations_new(computed_verdict) WHERE computed_verdict IS NOT NULL;
CREATE INDEX idx_curations_new_evidence_gin ON curations_new USING GIN (evidence_data);
CREATE INDEX idx_curations_new_scores_gin ON curations_new USING GIN (computed_scores);

-- Reviews indexes (4-eyes principle)
CREATE INDEX idx_reviews_curation ON reviews(curation_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id);
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_reviews_assigned ON reviews(assigned_at);
CREATE INDEX idx_reviews_reviewed ON reviews(reviewed_at) WHERE reviewed_at IS NOT NULL;

-- Active curations indexes
CREATE INDEX idx_active_curations_gene_scope ON active_curations(gene_id, scope_id);
CREATE INDEX idx_active_curations_scope ON active_curations(scope_id);
CREATE INDEX idx_active_curations_curation ON active_curations(curation_id);
CREATE INDEX idx_active_curations_activated ON active_curations(activated_at);
CREATE INDEX idx_active_curations_current ON active_curations(archived_at) WHERE archived_at IS NULL;

-- Audit log indexes
CREATE INDEX idx_audit_log_new_entity ON audit_log_new(entity_type, entity_id);
CREATE INDEX idx_audit_log_new_scope ON audit_log_new(scope_id);
CREATE INDEX idx_audit_log_new_user ON audit_log_new(user_id);
CREATE INDEX idx_audit_log_new_timestamp ON audit_log_new(timestamp);
CREATE INDEX idx_audit_log_new_operation ON audit_log_new(operation);
CREATE INDEX idx_audit_log_new_workflow_stage ON audit_log_new(workflow_stage);
CREATE INDEX idx_audit_log_new_schema ON audit_log_new(schema_id);

-- Schema selections indexes
CREATE INDEX idx_schema_selections_user_scope ON schema_selections(user_id, scope_id);
CREATE INDEX idx_schema_selections_institution_scope ON schema_selections(institution, scope_id);
CREATE INDEX idx_schema_selections_workflow_pair ON schema_selections(preferred_workflow_pair_id);

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE scopes IS 'Clinical specialties as first-class entities (kidney-genetics, cardio-genetics, etc.)';
COMMENT ON TABLE users_new IS 'Enhanced users with scope assignments and ORCID integration';
COMMENT ON TABLE curation_schemas IS 'Repository of methodology definitions (ClinGen, GenCC, custom)';
COMMENT ON TABLE workflow_pairs IS 'Precuration + curation schema combinations for complete workflows';
COMMENT ON TABLE gene_scope_assignments IS 'Many-to-many relationship between genes and clinical scopes';
COMMENT ON TABLE precurations_new IS 'Multiple precurations per gene-scope with schema-driven fields';
COMMENT ON TABLE curations_new IS 'Multiple curations per gene-scope with scoring engine integration';
COMMENT ON TABLE reviews IS '4-eyes principle implementation with mandatory independent review';
COMMENT ON TABLE active_curations IS 'One active curation per gene-scope with archive management';
COMMENT ON TABLE audit_log_new IS 'Complete audit trail for multi-stage workflow with scope context';
COMMENT ON TABLE schema_selections IS 'User and institutional preferences for schema selection';