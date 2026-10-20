-- =============================================================================
-- 029: One priority vocabulary for gene assignments (high / medium / low)
-- =============================================================================
-- The column default and old rows used 'normal' while the API only accepts 'medium'.
-- Idempotent: safe to run on a fresh build and on an existing database.
-- =============================================================================

UPDATE gene_scope_assignments SET priority = 'medium' WHERE priority = 'normal';
ALTER TABLE gene_scope_assignments ALTER COLUMN priority SET DEFAULT 'medium';
