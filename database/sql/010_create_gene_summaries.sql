-- Migration 010: Create gene_summaries table
-- ClinGen SOP v11 - Pre-computed aggregations for fast public queries
-- Date: 2025-10-14

BEGIN;

-- Create gene_summaries table
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
    last_computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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

-- Create trigger to mark gene summary as stale when curations change
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

COMMENT ON TABLE gene_summaries IS 'Pre-computed aggregations of gene curations across scopes for fast public queries';
COMMENT ON COLUMN gene_summaries.classification_summary IS 'JSONB object with counts by classification (definitive, strong, moderate, etc.)';
COMMENT ON COLUMN gene_summaries.scope_summaries IS 'JSONB array of per-scope summary objects with classification and scores';
COMMENT ON COLUMN gene_summaries.is_stale IS 'Marked TRUE when curations change; recomputed by background job';
COMMENT ON FUNCTION mark_gene_summary_stale() IS 'Auto-mark gene summaries as stale when curations are modified';

COMMIT;
