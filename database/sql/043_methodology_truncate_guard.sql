-- =============================================================================
-- 043: block TRUNCATE of methodology versions (#265)
-- =============================================================================
-- 042's immutability trigger is row-level, and row triggers never fire on TRUNCATE, so the
-- owner could wipe every version (and via CASCADE every pinned curation, precuration and
-- review). A statement-level trigger closes that; TRUNCATE ... CASCADE from curation_schemas
-- is caught too. Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION methodology_versions_no_truncate()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'methodology versions are published and immutable; TRUNCATE is not allowed'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_methodology_versions_no_truncate ON methodology_versions;
CREATE TRIGGER trigger_methodology_versions_no_truncate
    BEFORE TRUNCATE ON methodology_versions
    FOR EACH STATEMENT
    EXECUTE FUNCTION methodology_versions_no_truncate();

INSERT INTO schema_migrations (filename)
VALUES ('043_methodology_truncate_guard.sql')
ON CONFLICT DO NOTHING;
