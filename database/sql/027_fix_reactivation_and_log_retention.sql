-- =============================================================================
-- 027: Fix re-activation uniqueness, log retention, missing columns
-- =============================================================================
-- Idempotent: safe to run on a fresh build and on an existing database.
--
-- (a) curation_schemas / workflow_pairs: ensure updated_at exists (seed upserts set it).
-- (b) active_curations: UNIQUE(gene_id, scope_id) made it impossible to activate a second
--     curation for a gene-scope after archiving the first. Only the non-archived row must be
--     unique, so replace the constraint with a partial unique index.
-- (c) cleanup_old_logs(): the old version compared the partition *start* to the cutoff, so
--     it dropped partitions that still held rows inside the retention window, and it ignored
--     the requested retention. Drop a monthly partition only once its whole month is older
--     than the cutoff. A DEFAULT partition guarantees log writes never fail for dates with
--     no monthly partition; it is never dropped.
-- (d) curation_schemas.use_dynamic_form (was in migrations/, which initdb ignores).
-- =============================================================================

-- (a)
ALTER TABLE curation_schemas ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE workflow_pairs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- (b)
ALTER TABLE active_curations DROP CONSTRAINT IF EXISTS active_curations_gene_id_scope_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_curation_gene_scope_current
    ON active_curations (gene_id, scope_id)
    WHERE archived_at IS NULL;

-- (c)
CREATE TABLE IF NOT EXISTS system_logs_default PARTITION OF system_logs DEFAULT;

DROP FUNCTION IF EXISTS cleanup_old_logs();

CREATE OR REPLACE FUNCTION cleanup_old_logs(retention_days integer DEFAULT 90)
RETURNS void AS $$
DECLARE
    partition_name TEXT;
    partition_start DATE;
BEGIN
    FOR partition_name, partition_start IN
        SELECT
            tablename,
            to_date(substring(tablename from '^system_logs_(\d{4}_\d{2})$'), 'YYYY_MM')
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename ~ '^system_logs_\d{4}_\d{2}$'
    LOOP
        IF (partition_start + INTERVAL '1 month')::date <= CURRENT_DATE - retention_days THEN
            EXECUTE format('DROP TABLE IF EXISTS %I', partition_name);
            RAISE NOTICE 'Dropped old partition: %', partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- (d) Non-ClinGen schemas already render with DynamicForm: enable the flag only when the
-- column is first created, so a re-run never overrides an operator's choice.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'curation_schemas' AND column_name = 'use_dynamic_form'
    ) THEN
        ALTER TABLE curation_schemas
            ADD COLUMN use_dynamic_form BOOLEAN NOT NULL DEFAULT false;
        UPDATE curation_schemas SET use_dynamic_form = true
        WHERE name NOT ILIKE '%clingen%' AND name NOT ILIKE '%sop%';
    END IF;
END;
$$;

COMMENT ON COLUMN curation_schemas.use_dynamic_form IS
    'When true, use DynamicForm instead of ClinGenCurationForm for this schema';
