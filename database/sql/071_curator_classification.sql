-- =============================================================================
-- 071: curator and final classification (#533)
-- =============================================================================
-- The curator may propose a classification other than the computed verdict, with a
-- rationale (required at submit when they differ). final = COALESCE(curator, computed),
-- derived in the API. Approval confirms it. Reviewers cannot change either column:
-- 038's guard allowlist does not list them. The audit trigger logs the whole row.
-- Idempotent; records itself below.
-- =============================================================================

ALTER TABLE curations ADD COLUMN IF NOT EXISTS curator_classification VARCHAR(100);
ALTER TABLE curations ADD COLUMN IF NOT EXISTS curator_classification_rationale TEXT;

INSERT INTO schema_migrations (filename)
VALUES ('071_curator_classification.sql')
ON CONFLICT DO NOTHING;
