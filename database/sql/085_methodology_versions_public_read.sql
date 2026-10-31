-- =============================================================================
-- 085: Anyone reads methodology versions, as anyone reads curation_schemas (Wave 10 follow-up)
-- =============================================================================
-- 042 let only signed-in users read methodology_versions, so the anonymous curation export
-- (docs/EXPORT.md) gave methodology.version = null. A version is an immutable snapshot of a
-- curation schema, and curation_schemas have no RLS, so the snapshot hides nothing.
-- Inserts stay platform-admin only; no UPDATE/DELETE policy (immutable). Idempotent; records
-- itself.
-- =============================================================================

DROP POLICY IF EXISTS methodology_versions_select_policy ON methodology_versions;
CREATE POLICY methodology_versions_select_policy ON methodology_versions
    FOR SELECT USING (true);

INSERT INTO schema_migrations (filename)
VALUES ('085_methodology_versions_public_read.sql')
ON CONFLICT DO NOTHING;
