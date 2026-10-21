-- =============================================================================
-- 034: One active curation per gene+scope (repair + constraint)
-- =============================================================================
-- Activation used to archive only the active_curations pointer, leaving earlier curations at
-- status='active'. Keep the one the live pointer references (else the newest), archive the rest.
-- Idempotent: after the repair no row matches, and the index is guarded.
-- =============================================================================

-- The ActiveCuration model (and audit trigger) expect these columns; the table never had them,
-- so activation failed on real PostgreSQL.
ALTER TABLE active_curations
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id) ON DELETE SET NULL;

WITH ranked AS (
    SELECT c.id,
           row_number() OVER (
               PARTITION BY c.gene_id, c.scope_id
               ORDER BY (ac.curation_id IS NOT NULL) DESC, c.updated_at DESC, c.created_at DESC, c.id
           ) AS rn
    FROM curations c
    LEFT JOIN active_curations ac
           ON ac.curation_id = c.id AND ac.archived_at IS NULL
    WHERE c.status = 'active'
)
UPDATE curations c
SET status = 'archived'
FROM ranked r
WHERE c.id = r.id AND r.rn > 1;

-- Only a reliable timestamp is used: the activation record of the live pointer.
UPDATE curations c
SET approved_at = ac.activated_at,
    approved_by = COALESCE(c.approved_by, ac.activated_by)
FROM active_curations ac
WHERE ac.curation_id = c.id
  AND ac.archived_at IS NULL
  AND c.status = 'active'
  AND c.approved_at IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM curations WHERE status = 'active'
        GROUP BY gene_id, scope_id HAVING count(*) > 1
    ) THEN
        RAISE NOTICE 'Multiple active curations remain; uq_curations_one_active not created.';
    ELSE
        CREATE UNIQUE INDEX IF NOT EXISTS uq_curations_one_active
            ON curations (gene_id, scope_id) WHERE status = 'active';
    END IF;
END
$$;

INSERT INTO schema_migrations (filename)
VALUES ('034_single_active_curation.sql')
ON CONFLICT DO NOTHING;
