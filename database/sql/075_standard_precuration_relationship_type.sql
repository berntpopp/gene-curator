-- =============================================================================
-- 075: Standard_Precuration gets the relationship type (W9 monkey round 1)
-- =============================================================================
-- 072 added Relationship type only to ClinGen Precuration, so the seeded
-- ClinGen_Complete_Workflow pair (precuration Standard_Precuration) could not record a
-- susceptibility entity. Standard_Precuration gets entity_definition.relationship_type
-- (read by the entity_key expression of 072) as a new methodology version when its working
-- copy equals its latest version (as 068). Existing versions, pins and evidence are
-- untouched. Custom or edited schemas are skipped. Idempotent and self-recording.
-- =============================================================================

DO $migration$
DECLARE
    s curation_schemas%ROWTYPE;
    latest methodology_versions%ROWTYPE;
    snap JSONB;
BEGIN
    SELECT * INTO s FROM curation_schemas
        WHERE name = 'Standard_Precuration' AND version = '1.0.0'
          AND schema_type::text = 'precuration' AND based_on_schema_id IS NULL
        FOR UPDATE;
    IF s.id IS NULL THEN
        RETURN;
    END IF;
    SELECT * INTO latest FROM methodology_versions
        WHERE schema_id = s.id ORDER BY version DESC LIMIT 1;
    IF latest.id IS NULL
       OR methodology_snapshot(s) IS DISTINCT FROM latest.snapshot
       OR jsonb_typeof(latest.snapshot #> '{field_definitions,entity_definition,properties}')
          IS DISTINCT FROM 'object'
       OR latest.snapshot #> '{field_definitions,entity_definition,properties,relationship_type}'
          IS NOT NULL THEN
        RETURN;
    END IF;
    snap := jsonb_set(
        latest.snapshot,
        '{field_definitions,entity_definition,properties,relationship_type}',
        jsonb_build_object(
            'type', 'enum',
            'label', 'Relationship type',
            'required', false,
            'default', 'mendelian',
            'options', jsonb_build_array(
                jsonb_build_object('value', 'mendelian', 'label', 'Mendelian'),
                jsonb_build_object('value', 'susceptibility', 'label', 'Susceptibility (risk allele)')
            ),
            'help_text', 'Susceptibility: a low-penetrance or risk relationship ("disease, susceptibility to")'
        )
    );
    INSERT INTO methodology_versions
        (schema_id, version, snapshot, created_by, derived_from_version_id)
    VALUES (s.id, latest.version + 1, snap, s.created_by, latest.id);
    UPDATE curation_schemas SET field_definitions = snap->'field_definitions'
        WHERE id = s.id;
    RAISE NOTICE '075: published Standard_Precuration v%', latest.version + 1;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('075_standard_precuration_relationship_type.sql')
ON CONFLICT DO NOTHING;
