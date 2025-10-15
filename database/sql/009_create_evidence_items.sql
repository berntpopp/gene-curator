-- Migration 009: Create evidence_items table
-- ClinGen SOP v11 - Extract evidence from JSONB to first-class table
-- Date: 2025-10-14

BEGIN;

-- Create evidence_items table
CREATE TABLE evidence_items (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign Keys
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    -- Evidence Data
    evidence_category VARCHAR(50) NOT NULL,  -- 'case_level', 'segregation', 'case_control', etc.
    evidence_type VARCHAR(50) NOT NULL,      -- 'genetic', 'experimental'
    evidence_data JSONB NOT NULL,            -- Full evidence structure

    -- Scoring
    computed_score NUMERIC(5,2),             -- Individual item score
    score_metadata JSONB,                    -- Scoring calculation details

    -- Validation Status
    validation_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'valid', 'invalid'
    validation_errors JSONB,
    validated_at TIMESTAMPTZ,

    -- Audit Fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,

    -- Soft Delete
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX idx_evidence_items_curation ON evidence_items(curation_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_evidence_items_category ON evidence_items(evidence_category) WHERE is_deleted = FALSE;
CREATE INDEX idx_evidence_items_type ON evidence_items(evidence_type) WHERE is_deleted = FALSE;
CREATE INDEX idx_evidence_items_created ON evidence_items(created_at DESC);

-- Composite index for common query pattern (curation + category)
CREATE INDEX idx_evidence_items_curation_category
    ON evidence_items(curation_id, evidence_category)
    WHERE is_deleted = FALSE;

-- Display index with all needed fields
CREATE INDEX idx_evidence_items_display
    ON evidence_items(curation_id, evidence_category, created_at DESC)
    INCLUDE (computed_score, validation_status)
    WHERE is_deleted = FALSE;

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_evidence_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
CREATE TRIGGER update_evidence_items_updated_at
    BEFORE UPDATE ON evidence_items
    FOR EACH ROW
    EXECUTE FUNCTION update_evidence_items_updated_at();

COMMENT ON TABLE evidence_items IS 'Individual evidence items extracted from JSONB arrays for better data integrity and queryability';
COMMENT ON COLUMN evidence_items.evidence_category IS 'Evidence category: case_level, segregation, case_control, expression, protein_function, models, rescue';
COMMENT ON COLUMN evidence_items.evidence_type IS 'Evidence type: genetic or experimental';
COMMENT ON COLUMN evidence_items.validation_status IS 'Validation status: pending, valid, or invalid';
COMMENT ON COLUMN evidence_items.is_deleted IS 'Soft delete flag to preserve audit trail';

COMMIT;
