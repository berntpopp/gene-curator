-- =============================================================================
-- 035: reviews gets the audit columns its audit trigger reads
-- =============================================================================
-- trigger_audit_reviews runs log_schema_audit_trail(), which reads NEW.updated_by/created_by.
-- reviews never had them, so assigning a reviewer failed on real PostgreSQL with
-- 'record "new" has no field "updated_by"'. The other audited tables (curations, precurations,
-- active_curations) already have both columns.
-- Note: workflow_stage has no 'archived' value, so archived curations keep their last stage.
-- =============================================================================

ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id) ON DELETE SET NULL;

INSERT INTO schema_migrations (filename)
VALUES ('035_reviews_audit_columns.sql')
ON CONFLICT DO NOTHING;
