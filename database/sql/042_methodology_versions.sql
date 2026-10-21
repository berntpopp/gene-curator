-- =============================================================================
-- 042: immutable methodology versions; curations and precurations pin one (#265, slice 1)
-- =============================================================================
-- curation_schemas are edited in place, so a later edit silently changed how old work
-- renders and scores. A methodology version is a numbered snapshot of a schema's definition;
-- once published it can never change (enforced here, for every role). Every precuration and
-- curation is pinned at creation to the latest published version of its schema and can never
-- be re-pinned; later publishes leave existing rows alone.
-- Every schema gets a published v1: backfilled here, and created on insert from now on, so
-- new schemas can be curated at once. Existing rows are pinned to their schema's v1.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS methodology_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schema_id UUID NOT NULL REFERENCES curation_schemas(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version > 0),
    snapshot JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    published_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    derived_from_version_id UUID REFERENCES methodology_versions(id),
    CONSTRAINT uq_methodology_versions_schema_version UNIQUE (schema_id, version)
);

COMMENT ON TABLE methodology_versions IS 'Numbered snapshots of a curation schema; published rows are immutable';
COMMENT ON COLUMN methodology_versions.derived_from_version_id IS 'Version this one was derived from (provenance pointer only)';

-- Same keys as SNAPSHOT_KEYS in backend/app/crud/schema_repository.py
CREATE OR REPLACE FUNCTION methodology_snapshot(s curation_schemas)
RETURNS JSONB AS $$
    SELECT jsonb_build_object(
        'field_definitions', s.field_definitions,
        'validation_rules', s.validation_rules,
        'scoring_configuration', s.scoring_configuration,
        'workflow_states', s.workflow_states,
        'ui_configuration', s.ui_configuration
    )
$$ LANGUAGE SQL IMMUTABLE;

CREATE OR REPLACE FUNCTION methodology_version_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'published' THEN
        -- Deleting the schema itself cascades here; it only gets that far when nothing pins it.
        IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM curation_schemas WHERE id = OLD.schema_id) THEN
            RETURN OLD;
        END IF;
        RAISE EXCEPTION 'methodology version % is published and immutable', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_methodology_version_immutable ON methodology_versions;
CREATE TRIGGER trigger_methodology_version_immutable
    BEFORE UPDATE OR DELETE ON methodology_versions
    FOR EACH ROW
    EXECUTE FUNCTION methodology_version_immutable();

-- Backfill: one published v1 per existing schema
INSERT INTO methodology_versions (schema_id, version, snapshot, status, published_at, created_by)
SELECT s.id, 1, methodology_snapshot(s), 'published', NOW(), s.created_by
FROM curation_schemas s
ON CONFLICT (schema_id, version) DO NOTHING;

-- From now on every new schema starts with a published v1
CREATE OR REPLACE FUNCTION publish_initial_methodology_version()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO methodology_versions (schema_id, version, snapshot, status, published_at, created_by)
    VALUES (NEW.id, 1, methodology_snapshot(NEW), 'published', NOW(), NEW.created_by);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_publish_initial_methodology_version ON curation_schemas;
CREATE TRIGGER trigger_publish_initial_methodology_version
    AFTER INSERT ON curation_schemas
    FOR EACH ROW
    EXECUTE FUNCTION publish_initial_methodology_version();

-- Pin columns, backfilled to v1 of the row's schema
ALTER TABLE precurations
    ADD COLUMN IF NOT EXISTS methodology_version_id UUID REFERENCES methodology_versions(id);
ALTER TABLE curations
    ADD COLUMN IF NOT EXISTS methodology_version_id UUID REFERENCES methodology_versions(id);

UPDATE precurations p SET methodology_version_id = mv.id
FROM methodology_versions mv
WHERE p.methodology_version_id IS NULL
  AND mv.schema_id = p.precuration_schema_id AND mv.version = 1;

UPDATE curations c SET methodology_version_id = mv.id
FROM workflow_pairs wp, methodology_versions mv
WHERE c.methodology_version_id IS NULL
  AND wp.id = c.workflow_pair_id
  AND mv.schema_id = wp.curation_schema_id AND mv.version = 1;

ALTER TABLE precurations ALTER COLUMN methodology_version_id SET NOT NULL;
ALTER TABLE curations ALTER COLUMN methodology_version_id SET NOT NULL;

COMMENT ON COLUMN precurations.methodology_version_id IS 'Methodology version pinned at creation; never changes';
COMMENT ON COLUMN curations.methodology_version_id IS 'Methodology version pinned at creation; never changes';

-- Pin at creation to the latest published version of the row's schema (any given value is ignored)
CREATE OR REPLACE FUNCTION pin_methodology_version()
RETURNS TRIGGER AS $$
DECLARE
    target_schema UUID;
BEGIN
    IF TG_TABLE_NAME = 'curations' THEN
        SELECT curation_schema_id INTO target_schema FROM workflow_pairs WHERE id = NEW.workflow_pair_id;
    ELSE
        target_schema := NEW.precuration_schema_id;
    END IF;
    NEW.methodology_version_id := (
        SELECT id FROM methodology_versions
        WHERE schema_id = target_schema AND status = 'published'
        ORDER BY version DESC
        LIMIT 1
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION reject_methodology_version_change()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '%.methodology_version_id is pinned at creation and cannot change', TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_pin_methodology_version ON precurations;
CREATE TRIGGER trigger_pin_methodology_version
    BEFORE INSERT ON precurations
    FOR EACH ROW EXECUTE FUNCTION pin_methodology_version();
DROP TRIGGER IF EXISTS trigger_pin_methodology_version ON curations;
CREATE TRIGGER trigger_pin_methodology_version
    BEFORE INSERT ON curations
    FOR EACH ROW EXECUTE FUNCTION pin_methodology_version();

DROP TRIGGER IF EXISTS trigger_methodology_version_pinned ON precurations;
CREATE TRIGGER trigger_methodology_version_pinned
    BEFORE UPDATE OF methodology_version_id ON precurations
    FOR EACH ROW
    WHEN (OLD.methodology_version_id IS DISTINCT FROM NEW.methodology_version_id)
    EXECUTE FUNCTION reject_methodology_version_change();
DROP TRIGGER IF EXISTS trigger_methodology_version_pinned ON curations;
CREATE TRIGGER trigger_methodology_version_pinned
    BEFORE UPDATE OF methodology_version_id ON curations
    FOR EACH ROW
    WHEN (OLD.methodology_version_id IS DISTINCT FROM NEW.methodology_version_id)
    EXECUTE FUNCTION reject_methodology_version_change();

-- RLS: every signed-in user reads; only platform admins write (the admin publish path).
-- Published rows stay immutable for admins too (trigger above); no other bypass.
ALTER TABLE methodology_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE methodology_versions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS methodology_versions_select_policy ON methodology_versions;
CREATE POLICY methodology_versions_select_policy ON methodology_versions
    FOR SELECT USING (get_current_user_uuid() IS NOT NULL);
DROP POLICY IF EXISTS methodology_versions_insert_policy ON methodology_versions;
CREATE POLICY methodology_versions_insert_policy ON methodology_versions
    FOR INSERT WITH CHECK (is_application_admin());
DROP POLICY IF EXISTS methodology_versions_update_policy ON methodology_versions;
CREATE POLICY methodology_versions_update_policy ON methodology_versions
    FOR UPDATE USING (is_application_admin()) WITH CHECK (is_application_admin());
DROP POLICY IF EXISTS methodology_versions_delete_policy ON methodology_versions;
CREATE POLICY methodology_versions_delete_policy ON methodology_versions
    FOR DELETE USING (is_application_admin());

INSERT INTO schema_migrations (filename)
VALUES ('042_methodology_versions.sql')
ON CONFLICT DO NOTHING;
