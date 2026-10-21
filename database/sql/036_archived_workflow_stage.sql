-- =============================================================================
-- 036: terminal 'archived' workflow_stage (#323)
-- =============================================================================
-- Archived curations kept workflow_stage='active'. ALTER TYPE ... ADD VALUE would be the obvious
-- fix, but a value added in a transaction cannot be used in that transaction, and both
-- `make db-migrate` (one --single-transaction for all pending files) and the backfill below need
-- that. A freshly created type has no such limit, so the enum is rebuilt instead: dependent
-- view and partial index are dropped and recreated, columns re-typed, old type dropped.
-- Idempotent: skipped once the 'archived' label exists. Records itself below.
-- =============================================================================

DO $$
DECLARE
    view_def TEXT;
    fn RECORD;
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumtypid = 'workflow_stage'::regtype AND enumlabel = 'archived'
    ) THEN
        RETURN;
    END IF;

    view_def := pg_get_viewdef('review_compliance_dashboard'::regclass, true);
    DROP VIEW review_compliance_dashboard;
    DROP INDEX idx_curations_gene_public;

    ALTER TYPE workflow_stage RENAME TO workflow_stage_old;
    CREATE TYPE workflow_stage AS ENUM
        ('entry', 'precuration', 'curation', 'review', 'active', 'archived');

    ALTER TABLE precurations
        ALTER COLUMN workflow_stage DROP DEFAULT,
        ALTER COLUMN workflow_stage TYPE workflow_stage USING
            (CASE WHEN status = 'archived' THEN 'archived' ELSE workflow_stage::text END)::workflow_stage,
        ALTER COLUMN workflow_stage SET DEFAULT 'precuration';
    ALTER TABLE curations
        ALTER COLUMN workflow_stage DROP DEFAULT,
        ALTER COLUMN workflow_stage TYPE workflow_stage USING
            (CASE WHEN status = 'archived' THEN 'archived' ELSE workflow_stage::text END)::workflow_stage,
        ALTER COLUMN workflow_stage SET DEFAULT 'curation';
    ALTER TABLE audit_log
        ALTER COLUMN workflow_stage TYPE workflow_stage USING workflow_stage::text::workflow_stage;
    DROP TYPE workflow_stage_old;

    EXECUTE 'CREATE VIEW review_compliance_dashboard WITH (security_invoker = true) AS ' || view_def;
    COMMENT ON VIEW review_compliance_dashboard IS '4-eyes principle compliance monitoring and review management';
    CREATE INDEX idx_curations_gene_public
        ON curations(gene_id, scope_id)
        INCLUDE (computed_verdict, computed_scores, workflow_stage)
        WHERE workflow_stage = 'active';
    COMMENT ON INDEX idx_curations_gene_public IS 'Optimized index for public gene queries across scopes with covering data';

    -- The backfill is the USING clauses above (archived rows -> 'archived'); an UPDATE would fire
    -- the audit triggers, whose cached plans still point at the dropped type in this session.
    -- Touch their pg_proc rows so later statements in this session re-plan (plpgsql caches
    -- variables typed workflow_stage).
    FOR fn IN SELECT oid::regprocedure AS sig, procost FROM pg_proc
              WHERE prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
                AND prosrc ILIKE '%workflow_stage%'
    LOOP
        EXECUTE format('ALTER FUNCTION %s COST %s', fn.sig, fn.procost);
    END LOOP;
END $$;

INSERT INTO schema_migrations (filename)
VALUES ('036_archived_workflow_stage.sql')
ON CONFLICT DO NOTHING;
