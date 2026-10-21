-- =============================================================================
-- 033: Curation authorship from approved precurations + one open draft per author
-- =============================================================================
-- Approval used to stamp the approver as created_by of the auto-created curation, which
-- let the real author self-approve (4-eyes) and hid the item from the real reviewer.
-- precurations.updated_by is the approver at approval time; curations.precuration_id links back.
-- Completed precurations (computed_fields.completed_by) are excluded: there the curation was
-- created by a user through the API and is correctly attributed.
-- Idempotent: after the fix no row matches, and the index is guarded.
-- =============================================================================

UPDATE curations c
SET created_by = p.created_by
FROM precurations p
WHERE c.precuration_id = p.id
  AND p.status = 'approved'
  AND NOT (COALESCE(p.computed_fields, '{}'::jsonb) ? 'completed_by')
  AND p.created_by IS NOT NULL
  AND c.created_by = p.updated_by
  AND c.created_by <> p.created_by;

-- Concurrent create requests could insert two open drafts; make it a constraint.
-- Existing duplicates are not auto-deleted (that is curator data): skip with a notice.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM precurations WHERE status = 'draft'
        GROUP BY gene_id, scope_id, created_by HAVING count(*) > 1
    ) THEN
        RAISE NOTICE 'Duplicate open precuration drafts exist; uq_precurations_open_draft not created. Archive the duplicates and re-run this file.';
    ELSE
        CREATE UNIQUE INDEX IF NOT EXISTS uq_precurations_open_draft
            ON precurations (gene_id, scope_id, created_by) WHERE status = 'draft';
    END IF;
END
$$;

INSERT INTO schema_migrations (filename)
VALUES ('033_precuration_authorship_and_draft_uniqueness.sql')
ON CONFLICT DO NOTHING;
