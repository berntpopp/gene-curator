-- =============================================================================
-- 068: seeded MONDO fields use the MONDO lookup (Wave 8 monkey test, owner: urgent)
-- =============================================================================
-- Standard_Precuration (the precuration of the ClinGen, GenCC and qualitative pairs) and
-- the ClinGen_SOP_v11 curation stored mondo_id as a plain string, so the MONDO search and
-- the disease_name fill never appeared. ClinGen Precuration already sets
-- external_source "mondo" (the same component); the GenCC, qualitative and "ClinGen
-- Gene-Disease Validity SOP" curation schemas have no disease fields.
-- Published versions are immutable: each stock schema whose working copy still equals
-- its latest version gets a new version with "component": "MONDOAutocomplete" on
-- mondo_id; field keys are unchanged. Existing versions, pins and evidence are untouched;
-- new records pin the new version. Custom or derived schemas and edited working copies
-- are skipped. Idempotent (the component is then present) and self-recording.
-- =============================================================================

DO $migration$
DECLARE
    target RECORD;
    s curation_schemas%ROWTYPE;
    latest methodology_versions%ROWTYPE;
    snap JSONB;
    published TEXT[] := '{}';
BEGIN
    FOR target IN
        SELECT * FROM (VALUES
            ('Standard_Precuration', 'precuration'),
            ('ClinGen_SOP_v11', 'curation')
        ) t(name, schema_type)
    LOOP
        s := NULL;
        latest := NULL;
        SELECT * INTO s FROM curation_schemas
            WHERE name = target.name AND version = '1.0.0'
              AND schema_type::text = target.schema_type AND based_on_schema_id IS NULL
            FOR UPDATE;
        CONTINUE WHEN s.id IS NULL;
        SELECT * INTO latest FROM methodology_versions
            WHERE schema_id = s.id ORDER BY version DESC LIMIT 1;
        IF latest.id IS NULL
           OR methodology_snapshot(s) IS DISTINCT FROM latest.snapshot
           OR jsonb_typeof(latest.snapshot #> '{field_definitions,entity_definition,properties,mondo_id}')
              IS DISTINCT FROM 'object'
           OR latest.snapshot #> '{field_definitions,entity_definition,properties,mondo_id,component}'
              IS NOT NULL THEN
            CONTINUE;
        END IF;
        snap := jsonb_set(
            latest.snapshot,
            '{field_definitions,entity_definition,properties,mondo_id,component}',
            '"MONDOAutocomplete"'
        );
        INSERT INTO methodology_versions
            (schema_id, version, snapshot, created_by, derived_from_version_id)
        VALUES (s.id, latest.version + 1, snap, s.created_by, latest.id);
        UPDATE curation_schemas SET field_definitions = snap->'field_definitions'
            WHERE id = s.id;
        published := array_append(published, s.name || ' v' || (latest.version + 1)::text);
    END LOOP;
    RAISE NOTICE '068: published %', published;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('068_seeded_mondo_lookup.sql')
ON CONFLICT DO NOTHING;
