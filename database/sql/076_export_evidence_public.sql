-- =============================================================================
-- 076: Scope option, export evidence to anonymous callers (#558)
-- =============================================================================
-- export_evidence_public (off by default): the curation export (docs/EXPORT.md) always
-- gives scope members a row's evidence, scores and summary; anonymous callers and
-- non-members get them only for a public scope with this on. Enforced in the API
-- (crud.curation_export). Idempotent; records itself.
-- =============================================================================

ALTER TABLE scopes
    ADD COLUMN IF NOT EXISTS export_evidence_public BOOLEAN NOT NULL DEFAULT false;

INSERT INTO schema_migrations (filename)
VALUES ('076_export_evidence_public.sql')
ON CONFLICT DO NOTHING;
