-- =============================================================================
-- 029: One priority vocabulary for gene assignments (high / medium / low)
-- =============================================================================
-- The column default and old rows used 'normal' while the API only accepts 'medium'.
-- Idempotent: safe to run on a fresh build and on an existing database.
-- =============================================================================

UPDATE gene_scope_assignments SET priority = 'medium' WHERE priority = 'normal';
ALTER TABLE gene_scope_assignments ALTER COLUMN priority SET DEFAULT 'medium';

-- Record this file; schema_migrations only exists from 030 on, so skip it on a fresh build
-- (030 backfills the baseline) and register it when run later via `make db-migrate`.
DO $$
BEGIN
    IF to_regclass('public.schema_migrations') IS NOT NULL THEN
        INSERT INTO schema_migrations (filename) VALUES ('029_assignment_priority_medium.sql')
        ON CONFLICT DO NOTHING;
    END IF;
END
$$;
