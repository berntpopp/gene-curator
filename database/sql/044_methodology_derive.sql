-- =============================================================================
-- 044: derive a methodology from a published version (#265, #271)
-- =============================================================================
-- Derive creates a new schema from a version's snapshot; the schema's auto-published v1
-- records which version it came from. The API sets app.derived_from_version_id
-- transaction-locally (set_config(..., true)) right before the insert, so the value never
-- reaches a later transaction. Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION publish_initial_methodology_version()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO methodology_versions (schema_id, version, snapshot, created_by, derived_from_version_id)
    VALUES (
        NEW.id, 1, methodology_snapshot(NEW), NEW.created_by,
        NULLIF(current_setting('app.derived_from_version_id', true), '')::uuid
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

INSERT INTO schema_migrations (filename)
VALUES ('044_methodology_derive.sql')
ON CONFLICT DO NOTHING;
