-- =============================================================================
-- 063: widen evidence_items.evidence_category (MCP study round 2, finding 1)
-- =============================================================================
-- Categories are dotted evidence-table paths from the schema; paths over 50 characters
-- made the deprecated create_evidence_item endpoint fail with a 500 (varchar(50)).
-- Idempotent (re-widening is a no-op); records itself in schema_migrations.
-- =============================================================================

ALTER TABLE evidence_items ALTER COLUMN evidence_category TYPE VARCHAR(255);

INSERT INTO schema_migrations (filename)
VALUES ('063_evidence_category_length.sql')
ON CONFLICT DO NOTHING;
