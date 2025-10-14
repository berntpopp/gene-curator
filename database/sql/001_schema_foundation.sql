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

-- Application-level roles (2 values: admin, user)
-- admin: Full platform access
-- user: Scope-based access via scope_memberships
CREATE TYPE application_role AS ENUM ('admin', 'user');

COMMENT ON TYPE application_role IS 'Application-level roles: admin (full platform access) and user (scope-based access)';

-- Scope-level roles (4 values: admin, curator, reviewer, viewer)
-- admin: Manage scope (invite/remove members, assign genes)
-- curator: Create/edit curations
-- reviewer: Review curations (4-eyes principle)
-- viewer: Read-only access
CREATE TYPE scope_role AS ENUM ('admin', 'curator', 'reviewer', 'viewer');

COMMENT ON TYPE scope_role IS 'Scope-level roles: admin (manage scope), curator (create/edit), reviewer (review only), viewer (read-only)';

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
    is_public BOOLEAN DEFAULT false,                -- Public scopes visible to all authenticated users
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
    role application_role NOT NULL DEFAULT 'user',
    institution VARCHAR(255),
    assigned_scopes UUID[],                         -- DEPRECATED: Use scope_memberships table instead
    
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
CREATE TABLE genes (
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
    gene_id UUID NOT NULL,                         -- Will reference genes(id)
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
-- SCOPE MEMBERSHIPS (CORE MULTI-TENANCY)
-- ========================================

-- Core multi-tenancy table: user roles within scopes
CREATE TABLE scope_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Scope and user relationship
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,

    -- Scope-specific role (NOT application role)
    role scope_role NOT NULL,

    -- Invitation tracking
    invited_by UUID REFERENCES users_new(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,  -- NULL = pending invitation
    invitation_status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, rejected

    -- Team membership (for future team-based collaboration)
    team_id UUID,  -- Will reference teams(id) when teams table is created

    -- Metadata
    notes TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL,

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(scope_id, user_id),
    CHECK (invitation_status IN ('pending', 'accepted', 'rejected'))
);

COMMENT ON TABLE scope_memberships IS 'Core multi-tenancy table: user roles within scopes';
COMMENT ON COLUMN scope_memberships.role IS 'Scope-specific role: admin, curator, reviewer, or viewer';
COMMENT ON COLUMN scope_memberships.accepted_at IS 'NULL indicates pending invitation, non-NULL indicates accepted membership';
COMMENT ON COLUMN scope_memberships.invitation_status IS 'Invitation status: pending, accepted, or rejected';
COMMENT ON COLUMN scope_memberships.is_active IS 'Allow soft deletion of memberships';
COMMENT ON COLUMN scope_memberships.team_id IS 'Future: team-based collaboration within scopes';

-- ========================================
-- MULTI-STAGE WORKFLOW TABLES
-- ========================================

-- Precurations Table (Multiple per Gene-Scope)
CREATE TABLE precurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL,                         -- Will reference genes(id)
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
CREATE TABLE curations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id UUID NOT NULL,                         -- Will reference genes(id)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    precuration_id UUID,                           -- Will reference precurations(id)
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
    curation_id UUID NOT NULL,                     -- Will reference curations(id)
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
    gene_id UUID NOT NULL,                         -- Will reference genes(id)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    curation_id UUID NOT NULL,                     -- Will reference curations(id)
    
    -- Activation details
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_by UUID,                             -- Will reference users_new(id)
    
    -- Previous active curation (for audit trail)
    replaced_curation_id UUID,                     -- Will reference curations(id)
    
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
CREATE TABLE audit_log (
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
CREATE INDEX idx_scopes_public ON scopes(is_public) WHERE is_public = true;

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
CREATE INDEX idx_genes_hgnc_id ON genes(hgnc_id);
CREATE INDEX idx_genes_symbol ON genes(approved_symbol);
CREATE INDEX idx_genes_chromosome ON genes(chromosome);
CREATE INDEX idx_genes_details_gin ON genes USING GIN (details);
CREATE INDEX idx_genes_created_by ON genes(created_by);

-- Gene-scope assignments indexes
CREATE INDEX idx_gene_scope_assignments_gene ON gene_scope_assignments(gene_id);
CREATE INDEX idx_gene_scope_assignments_scope ON gene_scope_assignments(scope_id);
CREATE INDEX idx_gene_scope_assignments_curator ON gene_scope_assignments(assigned_curator_id);
CREATE INDEX idx_gene_scope_assignments_active ON gene_scope_assignments(is_active) WHERE is_active = true;
CREATE INDEX idx_gene_scope_assignments_workflow_pair ON gene_scope_assignments(workflow_pair_id);

-- Scope memberships indexes (CRITICAL for RLS performance)
CREATE INDEX idx_scope_memberships_scope ON scope_memberships(scope_id);
CREATE INDEX idx_scope_memberships_user ON scope_memberships(user_id);
CREATE INDEX idx_scope_memberships_role ON scope_memberships(role);
CREATE INDEX idx_scope_memberships_active ON scope_memberships(is_active) WHERE is_active = true;
CREATE INDEX idx_scope_memberships_pending ON scope_memberships(accepted_at) WHERE accepted_at IS NULL;

-- CRITICAL: Composite index for permission checks (prevents N+1 queries)
-- This index is used by RLS policies and permission check functions
CREATE INDEX idx_scope_memberships_user_scope_active
ON scope_memberships(user_id, scope_id, role)
WHERE is_active = true AND accepted_at IS NOT NULL;

COMMENT ON INDEX idx_scope_memberships_user_scope_active IS 'CRITICAL: Composite index for RLS permission checks (prevents N+1 queries)';

-- Precurations indexes
CREATE INDEX idx_precurations_gene_scope ON precurations(gene_id, scope_id);
CREATE INDEX idx_precurations_scope ON precurations(scope_id);
CREATE INDEX idx_precurations_status ON precurations(status);
CREATE INDEX idx_precurations_workflow_stage ON precurations(workflow_stage);
CREATE INDEX idx_precurations_creator ON precurations(created_by);
CREATE INDEX idx_precurations_draft ON precurations(is_draft) WHERE is_draft = true;
CREATE INDEX idx_precurations_evidence_gin ON precurations USING GIN (evidence_data);
CREATE INDEX idx_precurations_schema ON precurations(precuration_schema_id);

-- Curations indexes
CREATE INDEX idx_curations_gene_scope ON curations(gene_id, scope_id);
CREATE INDEX idx_curations_scope ON curations(scope_id);
CREATE INDEX idx_curations_precuration ON curations(precuration_id);
CREATE INDEX idx_curations_status ON curations(status);
CREATE INDEX idx_curations_workflow_stage ON curations(workflow_stage);
CREATE INDEX idx_curations_creator ON curations(created_by);
CREATE INDEX idx_curations_draft ON curations(is_draft) WHERE is_draft = true;
CREATE INDEX idx_curations_workflow_pair ON curations(workflow_pair_id);
CREATE INDEX idx_curations_verdict ON curations(computed_verdict) WHERE computed_verdict IS NOT NULL;
CREATE INDEX idx_curations_evidence_gin ON curations USING GIN (evidence_data);
CREATE INDEX idx_curations_scores_gin ON curations USING GIN (computed_scores);

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
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_scope ON audit_log(scope_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);
CREATE INDEX idx_audit_log_workflow_stage ON audit_log(workflow_stage);
CREATE INDEX idx_audit_log_schema ON audit_log(schema_id);

-- Schema selections indexes
CREATE INDEX idx_schema_selections_user_scope ON schema_selections(user_id, scope_id);
CREATE INDEX idx_schema_selections_institution_scope ON schema_selections(institution, scope_id);
CREATE INDEX idx_schema_selections_workflow_pair ON schema_selections(preferred_workflow_pair_id);

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE scopes IS 'Clinical specialties as first-class entities (kidney-genetics, cardio-genetics, etc.)';
COMMENT ON TABLE users_new IS 'Enhanced users with application roles (admin/user) and scope-based access via scope_memberships';
COMMENT ON COLUMN users_new.role IS 'Application-level role: admin (platform access) or user (scope-based access)';
COMMENT ON COLUMN users_new.assigned_scopes IS 'DEPRECATED: Use scope_memberships table for scope assignments';
COMMENT ON TABLE curation_schemas IS 'Repository of methodology definitions (ClinGen, GenCC, custom)';
COMMENT ON TABLE workflow_pairs IS 'Precuration + curation schema combinations for complete workflows';
COMMENT ON TABLE gene_scope_assignments IS 'Many-to-many relationship between genes and clinical scopes';
COMMENT ON TABLE precurations IS 'Multiple precurations per gene-scope with schema-driven fields';
COMMENT ON TABLE curations IS 'Multiple curations per gene-scope with scoring engine integration';
COMMENT ON TABLE reviews IS '4-eyes principle implementation with mandatory independent review';
COMMENT ON TABLE active_curations IS 'One active curation per gene-scope with archive management';
COMMENT ON TABLE audit_log IS 'Complete audit trail for multi-stage workflow with scope context';
COMMENT ON TABLE schema_selections IS 'User and institutional preferences for schema selection';