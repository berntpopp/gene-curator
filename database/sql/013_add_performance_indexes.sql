-- Migration 013: Add performance indexes for common query patterns
-- ClinGen SOP v11 - Optimize queries for public gene lookups and evidence display
-- Date: 2025-10-14

BEGIN;

-- Index for public gene queries (most common pattern)
-- Covers: gene_id, scope_id with classification, scores, stage
CREATE INDEX idx_curations_gene_public
    ON curations(gene_id, scope_id)
    INCLUDE (computed_verdict, computed_scores, workflow_stage)
    WHERE workflow_stage = 'active';

-- Index for public scopes (fast filtering)
CREATE INDEX IF NOT EXISTS idx_scopes_public
    ON scopes(is_public, is_active)
    WHERE is_public = TRUE AND is_active = TRUE;

COMMENT ON INDEX idx_curations_gene_public IS 'Optimized index for public gene queries across scopes with covering data';
COMMENT ON INDEX idx_scopes_public IS 'Fast filtering for public and active scopes';

COMMIT;
