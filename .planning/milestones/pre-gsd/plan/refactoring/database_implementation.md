# Database Implementation - ClinGen SOP v11

**Parent Plan**: `IMPLEMENTATION_PLAN.md`
**Phase**: Phase 1 (Weeks 1-4)
**Owner**: Database Engineer + Backend Developer

---

## Overview

This document specifies all database changes required for ClinGen SOP v11 implementation with scope-centric design. All migrations must be backwards-compatible and include rollback scripts.

---

## New Tables

### 1. evidence_items

**Purpose**: Extract evidence from JSONB array to first-class table for better data integrity.

```sql
CREATE TABLE evidence_items (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign Keys
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    -- Evidence Data
    evidence_category VARCHAR(50) NOT NULL,  -- 'case_level', 'segregation', 'case_control', etc.
    evidence_type VARCHAR(50) NOT NULL,       -- 'genetic', 'experimental'
    evidence_data JSONB NOT NULL,             -- Full evidence structure

    -- Scoring
    computed_score NUMERIC(5,2),              -- Individual item score
    score_metadata JSONB,                     -- Scoring calculation details

    -- Validation Status
    validation_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'valid', 'invalid'
    validation_errors JSONB,
    validated_at TIMESTAMP WITH TIME ZONE,

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,

    -- Soft Delete
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_evidence_items_curation ON evidence_items(curation_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_evidence_items_category ON evidence_items(evidence_category) WHERE is_deleted = FALSE;
CREATE INDEX idx_evidence_items_type ON evidence_items(evidence_type) WHERE is_deleted = FALSE;
CREATE INDEX idx_evidence_items_created ON evidence_items(created_at DESC);

-- Composite index for common query
CREATE INDEX idx_evidence_items_curation_category
    ON evidence_items(curation_id, evidence_category)
    WHERE is_deleted = FALSE;

-- Trigger for updated_at
CREATE TRIGGER update_evidence_items_updated_at
    BEFORE UPDATE ON evidence_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Evidence Data Structure** (JSONB):
```json
{
  // Case-Level Evidence
  "variant_type": "predicted_null",
  "proband_count": 5,
  "segregation_count": 0,
  "de_novo": true,
  "functional_alteration": false,
  "pmids": ["12345678", "87654321"],
  "notes": "Clinical details...",

  // OR Segregation Evidence
  "family_count": 3,
  "lod_score": 4.5,
  "inheritance_pattern": "autosomal_dominant",
  "sequencing_method": "exome",

  // OR Experimental Evidence
  "experiment_type": "expression",
  "model_system": "patient_cells",
  "functional_effect": "loss_of_function",
  "rescue_observed": false
}
```

---

### 2. gene_summaries

**Purpose**: Pre-computed aggregations of gene curations across scopes for fast public queries.

```sql
CREATE TABLE gene_summaries (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign Key
    gene_id UUID NOT NULL UNIQUE REFERENCES genes(id) ON DELETE CASCADE,

    -- Aggregated Data
    total_scopes_curated INTEGER NOT NULL DEFAULT 0,
    public_scopes_count INTEGER NOT NULL DEFAULT 0,
    private_scopes_count INTEGER NOT NULL DEFAULT 0,

    -- Classification Summary
    classification_summary JSONB NOT NULL DEFAULT '{}',
    /*
    {
      "definitive": 2,      // Count by classification
      "strong": 1,
      "moderate": 0,
      "limited": 1,
      "no_known": 0,
      "disputed": 0,
      "refuted": 0
    }
    */

    -- Consensus (if applicable)
    consensus_classification VARCHAR(50),
    consensus_confidence NUMERIC(3,2),  -- 0.0 to 1.0
    has_conflicts BOOLEAN NOT NULL DEFAULT FALSE,

    -- Per-Scope Details
    scope_summaries JSONB NOT NULL DEFAULT '[]',
    /*
    [
      {
        "scope_id": "uuid",
        "scope_name": "kidney-genetics",
        "is_public": true,
        "classification": "definitive",
        "genetic_score": 10.5,
        "experimental_score": 4.0,
        "total_score": 14.5,
        "last_updated": "2025-10-14T12:00:00Z",
        "curator_count": 3,
        "evidence_count": 15
      }
    ]
    */

    -- Metadata
    last_computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    computation_version INTEGER NOT NULL DEFAULT 1,

    -- Cache Control
    is_stale BOOLEAN NOT NULL DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_gene_summaries_gene ON gene_summaries(gene_id);
CREATE INDEX idx_gene_summaries_public ON gene_summaries(public_scopes_count) WHERE public_scopes_count > 0;
CREATE INDEX idx_gene_summaries_stale ON gene_summaries(is_stale) WHERE is_stale = TRUE;
CREATE INDEX idx_gene_summaries_classification ON gene_summaries USING gin(classification_summary);

-- GIN index for JSONB queries on scope_summaries
CREATE INDEX idx_gene_summaries_scopes ON gene_summaries USING gin(scope_summaries);
```

**Update Trigger**: Mark as stale when curations change
```sql
CREATE OR REPLACE FUNCTION mark_gene_summary_stale()
RETURNS TRIGGER AS $$
BEGIN
    -- When curation is updated, mark gene summary as stale
    UPDATE gene_summaries
    SET is_stale = TRUE
    WHERE gene_id = COALESCE(NEW.gene_id, OLD.gene_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_curation_update_mark_stale
    AFTER INSERT OR UPDATE OR DELETE ON curations
    FOR EACH ROW
    EXECUTE FUNCTION mark_gene_summary_stale();
```

---

### 3. validation_cache

**Purpose**: Cache external validator results (HGNC, PubMed, HPO) to reduce API calls.

```sql
CREATE TABLE validation_cache (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Validator Info
    validator_name VARCHAR(50) NOT NULL,      -- 'hgnc', 'pubmed', 'hpo'
    input_value VARCHAR(500) NOT NULL,        -- Gene symbol, PMID, HPO term
    validator_input_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 of validator_name + input_value

    -- Validation Result
    is_valid BOOLEAN NOT NULL,
    validation_status VARCHAR(20) NOT NULL,   -- 'valid', 'invalid', 'error', 'not_found'
    validation_response JSONB NOT NULL,
    /*
    {
      "approved_symbol": "BRCA1",        // For HGNC
      "hgnc_id": "HGNC:1100",
      "alias_symbols": ["RNF53"],
      "previous_symbols": [],
      "status": "Approved",

      // OR for PubMed
      "title": "Article title",
      "authors": ["Smith J", "Doe A"],
      "journal": "Nature",
      "year": 2024,
      "doi": "10.1038/...",

      // OR for HPO
      "term_name": "Intellectual disability",
      "definition": "...",
      "synonyms": ["Mental retardation"]
    }
    */

    -- Suggestions (for invalid inputs)
    suggestions JSONB,
    /*
    {
      "did_you_mean": ["BRCA1", "BRCA2"],
      "confidence_scores": [0.95, 0.87]
    }
    */

    -- Error Info
    error_message TEXT,
    error_code VARCHAR(50),

    -- Cache Control
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 1,
    last_accessed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_validation_cache_hash ON validation_cache(validator_input_hash);
CREATE INDEX idx_validation_cache_validator ON validation_cache(validator_name, input_value);
CREATE INDEX idx_validation_cache_expiry ON validation_cache(expires_at);
CREATE INDEX idx_validation_cache_valid ON validation_cache(validator_name, is_valid);

-- Auto-cleanup expired entries (run daily)
CREATE INDEX idx_validation_cache_cleanup ON validation_cache(expires_at) WHERE expires_at < NOW();
```

**TTL Values**:
- HGNC: 30 days (gene symbols rarely change)
- PubMed: 90 days (publication metadata stable)
- HPO: 14 days (ontology updates monthly)

---

## Modified Tables

### 1. curations (add concurrency control)

```sql
-- Add optimistic locking
ALTER TABLE curations
ADD COLUMN lock_version INTEGER NOT NULL DEFAULT 0;

-- Create index
CREATE INDEX idx_curations_lock_version ON curations(id, lock_version);

-- Update trigger (increment lock_version on update)
CREATE OR REPLACE FUNCTION increment_lock_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.lock_version = OLD.lock_version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_lock_version
    BEFORE UPDATE ON curations
    FOR EACH ROW
    EXECUTE FUNCTION increment_lock_version();
```

**Migration Note**: Existing rows will have `lock_version = 0`. First update will set to 1.

---

### 2. audit_logs (enhance for detailed tracking)

```sql
-- Add detailed change tracking
ALTER TABLE audit_logs
ADD COLUMN change_type VARCHAR(50),           -- 'evidence_added', 'score_updated', 'status_changed'
ADD COLUMN old_values JSONB,                  -- Previous state snapshot
ADD COLUMN new_values JSONB,                  -- New state snapshot
ADD COLUMN change_metadata JSONB,             -- User agent, IP, client info
ADD COLUMN alcoa_metadata JSONB;              -- ALCOA+ compliance fields

-- Update existing rows (backfill)
UPDATE audit_logs
SET change_type = 'legacy_action',
    change_metadata = jsonb_build_object(
        'migrated', true,
        'original_action', action
    )
WHERE change_type IS NULL;

-- Make NOT NULL after backfill
ALTER TABLE audit_logs
ALTER COLUMN change_type SET NOT NULL;

-- Indexes
CREATE INDEX idx_audit_logs_change_type ON audit_logs(change_type);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, change_type, created_at DESC);

-- GIN index for JSONB searches
CREATE INDEX idx_audit_logs_old_values ON audit_logs USING gin(old_values);
CREATE INDEX idx_audit_logs_new_values ON audit_logs USING gin(new_values);
```

**ALCOA+ Metadata Structure**:
```json
{
  "attributable": {
    "user_id": "uuid",
    "user_name": "Jane Doe",
    "user_role": "curator",
    "timestamp": "2025-10-14T12:00:00Z"
  },
  "contemporaneous": true,
  "original": true,
  "accurate": {
    "validation_passed": true,
    "validation_errors": []
  },
  "complete": true,
  "consistent": true,
  "enduring": {
    "stored_location": "primary_db",
    "backup_verified": true
  },
  "available": {
    "access_granted": ["curator", "reviewer", "admin"],
    "retention_until": "2035-10-14"
  }
}
```

---

### 3. curation_schemas (add ClinGen SOP v11 schema)

**Seed Data**: Complete ClinGen SOP v11 schema will be inserted during migration.

See section "Seed Data" below for full schema definition.

---

## Indexes for Performance

### Critical Query Patterns

**Pattern 1**: Get all public curations for a gene across scopes
```sql
-- Optimized index
CREATE INDEX idx_curations_gene_public
    ON curations(gene_id, scope_id)
    INCLUDE (classification, computed_scores, stage)
    WHERE is_current = TRUE AND stage = 'active';

-- Also need scope index
CREATE INDEX idx_scopes_public
    ON scopes(is_public, is_active)
    WHERE is_public = TRUE AND is_active = TRUE;
```

**Pattern 2**: Get all evidence items for a curation
```sql
-- Already covered by idx_evidence_items_curation
-- Additional covering index for display
CREATE INDEX idx_evidence_items_display
    ON evidence_items(curation_id, evidence_category, created_at DESC)
    INCLUDE (computed_score, validation_status)
    WHERE is_deleted = FALSE;
```

**Pattern 3**: Check for concurrent modifications
```sql
-- Already covered by idx_curations_lock_version
```

**Pattern 4**: Validator cache lookup
```sql
-- Already covered by idx_validation_cache_hash (unique)
```

---

## Migration Scripts

### Migration 001: Add lock_version to curations

**File**: `backend/alembic/versions/001_add_lock_version.py`

```python
"""Add lock_version for optimistic locking

Revision ID: 001_clingen_lock_version
Revises: <previous>
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa

revision = '001_clingen_lock_version'
down_revision = '<previous_revision_id>'
branch_labels = None
depends_on = None

def upgrade():
    # Add lock_version column
    op.add_column('curations',
        sa.Column('lock_version', sa.Integer(), nullable=False, server_default='0')
    )

    # Create index
    op.create_index(
        'idx_curations_lock_version',
        'curations',
        ['id', 'lock_version']
    )

    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION increment_lock_version()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.lock_version = OLD.lock_version + 1;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER trigger_increment_lock_version
        BEFORE UPDATE ON curations
        FOR EACH ROW
        EXECUTE FUNCTION increment_lock_version();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trigger_increment_lock_version ON curations")
    op.execute("DROP FUNCTION IF EXISTS increment_lock_version()")
    op.drop_index('idx_curations_lock_version', table_name='curations')
    op.drop_column('curations', 'lock_version')
```

---

### Migration 002: Create evidence_items table

**File**: `backend/alembic/versions/002_create_evidence_items.py`

```python
"""Create evidence_items table

Revision ID: 002_clingen_evidence_items
Revises: 001_clingen_lock_version
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_clingen_evidence_items'
down_revision = '001_clingen_lock_version'
branch_labels = None
depends_on = None

def upgrade():
    # Create table
    op.create_table(
        'evidence_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('curation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('curations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('evidence_category', sa.String(50), nullable=False),
        sa.Column('evidence_type', sa.String(50), nullable=False),
        sa.Column('evidence_data', postgresql.JSONB, nullable=False),
        sa.Column('computed_score', sa.Numeric(5, 2)),
        sa.Column('score_metadata', postgresql.JSONB),
        sa.Column('validation_status', sa.String(20), server_default='pending'),
        sa.Column('validation_errors', postgresql.JSONB),
        sa.Column('validated_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT')),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'))
    )

    # Create indexes
    op.create_index('idx_evidence_items_curation', 'evidence_items', ['curation_id'],
                    postgresql_where=sa.text('is_deleted = FALSE'))
    op.create_index('idx_evidence_items_category', 'evidence_items', ['evidence_category'],
                    postgresql_where=sa.text('is_deleted = FALSE'))
    op.create_index('idx_evidence_items_type', 'evidence_items', ['evidence_type'],
                    postgresql_where=sa.text('is_deleted = FALSE'))
    op.create_index('idx_evidence_items_created', 'evidence_items', [sa.desc('created_at')])
    op.create_index('idx_evidence_items_curation_category', 'evidence_items', ['curation_id', 'evidence_category'],
                    postgresql_where=sa.text('is_deleted = FALSE'))

    # Create trigger for updated_at
    op.execute("""
        CREATE TRIGGER update_evidence_items_updated_at
        BEFORE UPDATE ON evidence_items
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS update_evidence_items_updated_at ON evidence_items")
    op.drop_table('evidence_items')
```

---

### Migration 003: Create gene_summaries table

**File**: `backend/alembic/versions/003_create_gene_summaries.py`

```python
"""Create gene_summaries table

Revision ID: 003_clingen_gene_summaries
Revises: 002_clingen_evidence_items
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_clingen_gene_summaries'
down_revision = '002_clingen_evidence_items'
branch_labels = None
depends_on = None

def upgrade():
    # Create table
    op.create_table(
        'gene_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('gene_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('genes.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('total_scopes_curated', sa.Integer, nullable=False, server_default='0'),
        sa.Column('public_scopes_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('private_scopes_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('classification_summary', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('consensus_classification', sa.String(50)),
        sa.Column('consensus_confidence', sa.Numeric(3, 2)),
        sa.Column('has_conflicts', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('scope_summaries', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('last_computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('computation_version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_stale', sa.Boolean, nullable=False, server_default='false')
    )

    # Create indexes
    op.create_index('idx_gene_summaries_gene', 'gene_summaries', ['gene_id'])
    op.create_index('idx_gene_summaries_public', 'gene_summaries', ['public_scopes_count'],
                    postgresql_where=sa.text('public_scopes_count > 0'))
    op.create_index('idx_gene_summaries_stale', 'gene_summaries', ['is_stale'],
                    postgresql_where=sa.text('is_stale = TRUE'))

    # GIN indexes for JSONB
    op.execute("CREATE INDEX idx_gene_summaries_classification ON gene_summaries USING gin(classification_summary)")
    op.execute("CREATE INDEX idx_gene_summaries_scopes ON gene_summaries USING gin(scope_summaries)")

    # Create trigger to mark stale on curation changes
    op.execute("""
        CREATE OR REPLACE FUNCTION mark_gene_summary_stale()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE gene_summaries
            SET is_stale = TRUE
            WHERE gene_id = COALESCE(NEW.gene_id, OLD.gene_id);

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_curation_update_mark_stale
        AFTER INSERT OR UPDATE OR DELETE ON curations
        FOR EACH ROW
        EXECUTE FUNCTION mark_gene_summary_stale();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trigger_curation_update_mark_stale ON curations")
    op.execute("DROP FUNCTION IF EXISTS mark_gene_summary_stale()")
    op.drop_table('gene_summaries')
```

---

### Migration 004: Create validation_cache table

**File**: `backend/alembic/versions/004_create_validation_cache.py`

```python
"""Create validation_cache table

Revision ID: 004_clingen_validation_cache
Revises: 003_clingen_gene_summaries
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004_clingen_validation_cache'
down_revision = '003_clingen_gene_summaries'
branch_labels = None
depends_on = None

def upgrade():
    # Create table
    op.create_table(
        'validation_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('validator_name', sa.String(50), nullable=False),
        sa.Column('input_value', sa.String(500), nullable=False),
        sa.Column('validator_input_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('is_valid', sa.Boolean, nullable=False),
        sa.Column('validation_status', sa.String(20), nullable=False),
        sa.Column('validation_response', postgresql.JSONB, nullable=False),
        sa.Column('suggestions', postgresql.JSONB),
        sa.Column('error_message', sa.Text),
        sa.Column('error_code', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('access_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )

    # Create indexes
    op.create_index('idx_validation_cache_hash', 'validation_cache', ['validator_input_hash'], unique=True)
    op.create_index('idx_validation_cache_validator', 'validation_cache', ['validator_name', 'input_value'])
    op.create_index('idx_validation_cache_expiry', 'validation_cache', ['expires_at'])
    op.create_index('idx_validation_cache_valid', 'validation_cache', ['validator_name', 'is_valid'])
    op.create_index('idx_validation_cache_cleanup', 'validation_cache', ['expires_at'],
                    postgresql_where=sa.text('expires_at < NOW()'))

def downgrade():
    op.drop_table('validation_cache')
```

---

### Migration 005: Enhance audit_logs

**File**: `backend/alembic/versions/005_enhance_audit_logs.py`

```python
"""Enhance audit_logs with detailed tracking

Revision ID: 005_clingen_audit_logs
Revises: 004_clingen_validation_cache
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_clingen_audit_logs'
down_revision = '004_clingen_validation_cache'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('audit_logs', sa.Column('change_type', sa.String(50)))
    op.add_column('audit_logs', sa.Column('old_values', postgresql.JSONB))
    op.add_column('audit_logs', sa.Column('new_values', postgresql.JSONB))
    op.add_column('audit_logs', sa.Column('change_metadata', postgresql.JSONB))
    op.add_column('audit_logs', sa.Column('alcoa_metadata', postgresql.JSONB))

    # Backfill existing rows
    op.execute("""
        UPDATE audit_logs
        SET change_type = 'legacy_action',
            change_metadata = jsonb_build_object(
                'migrated', true,
                'original_action', action
            )
        WHERE change_type IS NULL
    """)

    # Make NOT NULL
    op.alter_column('audit_logs', 'change_type', nullable=False)

    # Create indexes
    op.create_index('idx_audit_logs_change_type', 'audit_logs', ['change_type'])
    op.create_index('idx_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_logs_user_action', 'audit_logs', ['user_id', 'change_type', sa.desc('created_at')])

    # GIN indexes
    op.execute("CREATE INDEX idx_audit_logs_old_values ON audit_logs USING gin(old_values)")
    op.execute("CREATE INDEX idx_audit_logs_new_values ON audit_logs USING gin(new_values)")

def downgrade():
    op.drop_index('idx_audit_logs_new_values', table_name='audit_logs')
    op.drop_index('idx_audit_logs_old_values', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_entity', table_name='audit_logs')
    op.drop_index('idx_audit_logs_change_type', table_name='audit_logs')

    op.drop_column('audit_logs', 'alcoa_metadata')
    op.drop_column('audit_logs', 'change_metadata')
    op.drop_column('audit_logs', 'new_values')
    op.drop_column('audit_logs', 'old_values')
    op.drop_column('audit_logs', 'change_type')
```

---

### Migration 006: Add performance indexes

**File**: `backend/alembic/versions/006_add_performance_indexes.py`

```python
"""Add performance indexes for common queries

Revision ID: 006_clingen_performance_indexes
Revises: 005_clingen_audit_logs
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa

revision = '006_clingen_performance_indexes'
down_revision = '005_clingen_audit_logs'
branch_labels = None
depends_on = None

def upgrade():
    # Index for public gene queries
    op.execute("""
        CREATE INDEX idx_curations_gene_public
        ON curations(gene_id, scope_id)
        INCLUDE (classification, computed_scores, stage)
        WHERE is_current = TRUE AND stage = 'active'
    """)

    # Index for public scopes
    op.execute("""
        CREATE INDEX idx_scopes_public
        ON scopes(is_public, is_active)
        WHERE is_public = TRUE AND is_active = TRUE
    """)

    # Index for evidence display
    op.execute("""
        CREATE INDEX idx_evidence_items_display
        ON evidence_items(curation_id, evidence_category, created_at DESC)
        INCLUDE (computed_score, validation_status)
        WHERE is_deleted = FALSE
    """)

def downgrade():
    op.drop_index('idx_evidence_items_display', table_name='evidence_items')
    op.drop_index('idx_scopes_public', table_name='scopes')
    op.drop_index('idx_curations_gene_public', table_name='curations')
```

---

## Seed Data

### ClinGen SOP v11 Schema

**File**: `backend/alembic/versions/007_seed_clingen_schema.py`

```python
"""Seed ClinGen SOP v11 curation schema

Revision ID: 007_clingen_seed_schema
Revises: 006_clingen_performance_indexes
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json
from datetime import datetime
import uuid

revision = '007_clingen_seed_schema'
down_revision = '006_clingen_performance_indexes'
branch_labels = None
depends_on = None

def upgrade():
    # Get admin user ID for created_by
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM users WHERE email = 'admin@gene-curator.dev' LIMIT 1"))
    admin_id = result.fetchone()[0]

    schema_id = str(uuid.uuid4())

    # Full ClinGen SOP v11 schema
    schema_data = {
        "id": schema_id,
        "name": "ClinGen Gene-Disease Validity SOP",
        "version": "11.0",
        "description": "ClinGen Standard Operating Procedures for Gene-Disease Clinical Validity Curation (September 2024)",
        "schema_type": "curation",
        "institution": "ClinGen",
        "is_active": True,
        "created_by": str(admin_id),
        "field_definitions": {
            "genetic_evidence": {
                "label": "Genetic Evidence",
                "type": "array",
                "required": True,
                "items": {
                    "type": "object",
                    "properties": {
                        "evidence_category": {
                            "type": "select",
                            "options": ["case_level", "segregation", "case_control"],
                            "required": True
                        },
                        "variant_type": {
                            "type": "select",
                            "options": ["predicted_null", "missense", "other_variant_type"],
                            "required": True,
                            "condition": "evidence_category == 'case_level'"
                        },
                        "proband_count": {
                            "type": "integer",
                            "min": 0,
                            "required": True,
                            "condition": "evidence_category == 'case_level'"
                        },
                        "de_novo": {
                            "type": "boolean",
                            "default": False
                        },
                        "functional_alteration": {
                            "type": "boolean",
                            "default": False
                        },
                        "family_count": {
                            "type": "integer",
                            "min": 0,
                            "condition": "evidence_category == 'segregation'"
                        },
                        "lod_score": {
                            "type": "number",
                            "min": 0,
                            "condition": "evidence_category == 'segregation'"
                        },
                        "inheritance_pattern": {
                            "type": "select",
                            "options": ["autosomal_dominant", "autosomal_recessive", "x_linked"],
                            "required": True
                        },
                        "pmids": {
                            "type": "array",
                            "items": {"type": "string", "pattern": "^[0-9]+$"},
                            "required": True
                        },
                        "notes": {
                            "type": "textarea"
                        }
                    }
                }
            },
            "experimental_evidence": {
                "label": "Experimental Evidence",
                "type": "array",
                "required": False,
                "items": {
                    "type": "object",
                    "properties": {
                        "evidence_category": {
                            "type": "select",
                            "options": ["expression", "protein_function", "models", "rescue"],
                            "required": True
                        },
                        "model_system": {
                            "type": "select",
                            "options": ["patient_cells", "non_patient_cells", "animal_model", "non_human_model"],
                            "required": True
                        },
                        "functional_effect": {
                            "type": "select",
                            "options": ["loss_of_function", "gain_of_function", "altered_function"],
                            "required": True
                        },
                        "rescue_observed": {
                            "type": "boolean",
                            "default": False
                        },
                        "pmids": {
                            "type": "array",
                            "items": {"type": "string", "pattern": "^[0-9]+$"},
                            "required": True
                        },
                        "notes": {
                            "type": "textarea"
                        }
                    }
                }
            }
        },
        "validation_rules": {
            "genetic_evidence_required": {
                "rule": "len(genetic_evidence) > 0",
                "message": "At least one genetic evidence item is required"
            },
            "lod_score_consistency": {
                "rule": "if segregation: lod_score >= 0",
                "message": "LOD score must be non-negative for segregation evidence"
            },
            "pmid_format": {
                "rule": "all PMIDs must be numeric strings",
                "validator": "pubmed"
            }
        },
        "scoring_configuration": {
            "engine": "clingen",
            "genetic_evidence_rules": {
                "case_level_predicted_null": {
                    "base_score": 1.5,
                    "de_novo_bonus": 0.5,
                    "functional_alteration_bonus": 0.4,
                    "max_score": 12
                },
                "case_level_missense": {
                    "base_score": 0.1,
                    "de_novo_bonus": 0.4,
                    "functional_alteration_bonus": 0.4,
                    "max_score": 2
                },
                "segregation": {
                    "lod_scoring": True,
                    "max_score": 7,
                    "family_limit": 7
                },
                "case_control": {
                    "max_score": 6
                }
            },
            "experimental_evidence_rules": {
                "max_total_score": 6,
                "expression": {"max_score": 2},
                "protein_function": {"max_score": 2},
                "models": {"max_score": 4},
                "rescue": {"max_score": 2}
            },
            "classification_thresholds": {
                "definitive": 12,
                "strong": 7,
                "moderate": 2,
                "limited": 0.1,
                "no_known": 0,
                "disputed": -1,
                "refuted": -2
            }
        },
        "workflow_states": {
            "entry": {"label": "Entry", "color": "grey"},
            "precuration": {"label": "Precuration", "color": "blue"},
            "curation": {"label": "Curation", "color": "orange"},
            "review": {"label": "Review", "color": "purple"},
            "active": {"label": "Active", "color": "green"}
        },
        "ui_configuration": {
            "form_layout": "tabbed",
            "tabs": ["Genetic Evidence", "Experimental Evidence", "Scoring Summary"],
            "show_score_preview": True,
            "enable_auto_save": True,
            "validation_on_blur": True
        }
    }

    # Insert schema
    conn.execute(
        sa.text("""
            INSERT INTO curation_schemas
            (id, name, version, description, schema_type, institution, is_active,
             created_by, field_definitions, validation_rules, scoring_configuration,
             workflow_states, ui_configuration, created_at, updated_at)
            VALUES
            (:id, :name, :version, :description, :schema_type, :institution, :is_active,
             :created_by, :field_definitions, :validation_rules, :scoring_configuration,
             :workflow_states, :ui_configuration, NOW(), NOW())
        """),
        {
            "id": schema_data["id"],
            "name": schema_data["name"],
            "version": schema_data["version"],
            "description": schema_data["description"],
            "schema_type": schema_data["schema_type"],
            "institution": schema_data["institution"],
            "is_active": schema_data["is_active"],
            "created_by": schema_data["created_by"],
            "field_definitions": json.dumps(schema_data["field_definitions"]),
            "validation_rules": json.dumps(schema_data["validation_rules"]),
            "scoring_configuration": json.dumps(schema_data["scoring_configuration"]),
            "workflow_states": json.dumps(schema_data["workflow_states"]),
            "ui_configuration": json.dumps(schema_data["ui_configuration"])
        }
    )

    print(f"✅ ClinGen SOP v11 schema created with ID: {schema_id}")

def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM curation_schemas WHERE name = 'ClinGen Gene-Disease Validity SOP' AND version = '11.0'"))
```

---

## Data Migration Strategy

### Migrating Existing Evidence Data

If there are existing curations with evidence in JSONB, migrate to `evidence_items`:

**File**: `backend/alembic/versions/008_migrate_evidence_data.py`

```python
"""Migrate existing evidence from JSONB to evidence_items table

Revision ID: 008_clingen_migrate_evidence
Revises: 007_clingen_seed_schema
Create Date: 2025-10-14

"""
from alembic import op
import sqlalchemy as sa
import json
import uuid

revision = '008_clingen_migrate_evidence'
down_revision = '007_clingen_seed_schema'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    # Get all curations with evidence_data
    result = conn.execute(sa.text("""
        SELECT id, evidence_data, created_by
        FROM curations
        WHERE evidence_data IS NOT NULL
        AND jsonb_typeof(evidence_data) = 'object'
    """))

    migrated_count = 0

    for row in result:
        curation_id, evidence_data, created_by = row

        # Parse evidence_data
        evidence = json.loads(evidence_data) if isinstance(evidence_data, str) else evidence_data

        # Migrate genetic evidence
        if "genetic_evidence" in evidence and isinstance(evidence["genetic_evidence"], list):
            for item in evidence["genetic_evidence"]:
                conn.execute(sa.text("""
                    INSERT INTO evidence_items
                    (id, curation_id, created_by, evidence_category, evidence_type,
                     evidence_data, validation_status, created_at, updated_at)
                    VALUES
                    (:id, :curation_id, :created_by, :evidence_category, :evidence_type,
                     :evidence_data, 'migrated', NOW(), NOW())
                """), {
                    "id": str(uuid.uuid4()),
                    "curation_id": str(curation_id),
                    "created_by": str(created_by),
                    "evidence_category": item.get("evidence_category", "unknown"),
                    "evidence_type": "genetic",
                    "evidence_data": json.dumps(item)
                })
                migrated_count += 1

        # Migrate experimental evidence
        if "experimental_evidence" in evidence and isinstance(evidence["experimental_evidence"], list):
            for item in evidence["experimental_evidence"]:
                conn.execute(sa.text("""
                    INSERT INTO evidence_items
                    (id, curation_id, created_by, evidence_category, evidence_type,
                     evidence_data, validation_status, created_at, updated_at)
                    VALUES
                    (:id, :curation_id, :created_by, :evidence_category, :evidence_type,
                     :evidence_data, 'migrated', NOW(), NOW())
                """), {
                    "id": str(uuid.uuid4()),
                    "curation_id": str(curation_id),
                    "created_by": str(created_by),
                    "evidence_category": item.get("evidence_category", "unknown"),
                    "evidence_type": "experimental",
                    "evidence_data": json.dumps(item)
                })
                migrated_count += 1

    print(f"✅ Migrated {migrated_count} evidence items to evidence_items table")

def downgrade():
    # No downgrade - data remains in evidence_items
    pass
```

---

## Maintenance Tasks

### Auto-Cleanup Script for Expired Validation Cache

**File**: `backend/app/tasks/cleanup_validation_cache.py`

```python
"""Background task to cleanup expired validation cache entries"""

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import ValidationCache
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

def cleanup_expired_cache(db: Session) -> int:
    """Delete expired validation cache entries"""

    result = db.query(ValidationCache).filter(
        ValidationCache.expires_at < datetime.now()
    ).delete(synchronize_session=False)

    db.commit()

    logger.info(f"Cleaned up {result} expired validation cache entries")
    return result
```

**Cron**: Run daily at 2 AM
```bash
# In production, add to crontab or use Celery Beat
0 2 * * * cd /app && python -m app.tasks.cleanup_validation_cache
```

---

### Recompute Stale Gene Summaries

**File**: `backend/app/tasks/recompute_gene_summaries.py`

```python
"""Background task to recompute stale gene summaries"""

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import GeneSummary
from app.crud.gene_summary import gene_summary_crud
from app.core.logging import get_logger

logger = get_logger(__name__)

def recompute_stale_summaries(db: Session, batch_size: int = 100) -> int:
    """Recompute stale gene summaries in batches"""

    stale_summaries = db.query(GeneSummary).filter(
        GeneSummary.is_stale == True
    ).limit(batch_size).all()

    count = 0
    for summary in stale_summaries:
        try:
            gene_summary_crud.recompute_summary(db, gene_id=summary.gene_id)
            count += 1
        except Exception as e:
            logger.error(f"Failed to recompute summary for gene {summary.gene_id}", error=e)

    logger.info(f"Recomputed {count} gene summaries")
    return count
```

**Cron**: Run every hour
```bash
0 * * * * cd /app && python -m app.tasks.recompute_gene_summaries
```

---

## Testing Checklist

### Unit Tests
- [ ] Lock version increments on update
- [ ] Concurrent update detection (optimistic locking)
- [ ] Evidence item CRUD operations
- [ ] Gene summary aggregation logic
- [ ] Validation cache TTL calculation
- [ ] Audit log detailed tracking

### Integration Tests
- [ ] Evidence migration from JSONB to table
- [ ] Cross-scope gene summary queries
- [ ] Validation cache hit/miss behavior
- [ ] Trigger: Mark gene summary stale on curation change
- [ ] Trigger: Increment lock version on update

### Performance Tests
- [ ] Query performance: Get all public curations for gene (< 100ms)
- [ ] Query performance: Get gene summary with 10+ scopes (< 200ms)
- [ ] Validation cache lookup (< 10ms)
- [ ] Evidence item display for curation with 50+ items (< 150ms)

---

## Rollback Plan

All migrations include downgrade functions. To rollback:

```bash
# Rollback all ClinGen migrations
cd backend
alembic downgrade 006_clingen_performance_indexes  # Rollback to before ClinGen changes

# Or rollback one at a time
alembic downgrade -1
```

**Data Loss Warning**: Rolling back will delete:
- All evidence_items (unless you backup first)
- All gene_summaries
- All validation_cache entries
- Enhanced audit log fields

**Backup First**:
```bash
pg_dump -h localhost -p 5454 -U gene_curator -d gene_curator_dev > backup_before_rollback.sql
```

---

## Next Steps

1. **Review** this document with database engineer
2. **Create** feature branch: `feature/clingen-sop-v11-foundation`
3. **Run** migrations in development environment
4. **Verify** all indexes created successfully
5. **Test** query performance with sample data
6. **Move to** API implementation (see `api_implementation.md`)

---

**Document Status**: ✅ Ready for Implementation
**Estimated Effort**: 2-3 weeks (Phase 1)
**Dependencies**: None (foundation layer)
