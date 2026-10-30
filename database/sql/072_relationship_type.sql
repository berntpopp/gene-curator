-- =============================================================================
-- 072: Relationship type: Mendelian or susceptibility (#539)
-- =============================================================================
-- A precuration's evidence_data.relationship_type (flat or under entity_definition) is
-- 'mendelian' (default; also when absent or anything else) or 'susceptibility'. The
-- entity_key gets a '|SUSCEPTIBILITY' suffix only for susceptibility, so a Mendelian and a
-- susceptibility curation of one gene, MONDO id and MOI are separate entities, and every
-- existing key stays byte-identical. Curations copy the key from their precuration (067).
-- PostgreSQL 15 cannot change a generation expression in place: the column and the
-- open-draft index on it are recreated once (skipped when the expression already has it);
-- curation and active-curation key copies follow a precuration key that gained the suffix.
-- ClinGen Precuration gets a Relationship type field after MOI, as a new methodology
-- version when the working copy equals its latest version (as 070). Idempotent.
-- =============================================================================

DO $migration$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_attrdef d
        JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE d.adrelid = 'precurations'::regclass AND a.attname = 'entity_key'
          AND pg_get_expr(d.adbin, d.adrelid) LIKE '%relationship_type%'
    ) THEN
        RETURN;
    END IF;
    DROP INDEX IF EXISTS uq_precurations_open_draft;
    ALTER TABLE precurations DROP COLUMN IF EXISTS entity_key;
    ALTER TABLE precurations ADD COLUMN entity_key TEXT GENERATED ALWAYS AS (
        CASE WHEN upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mondo_id'), ''), evidence_data -> 'entity_definition' ->> 'mondo_id', '')), '_', ':')) = '' THEN '' ELSE upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mondo_id'), ''), evidence_data -> 'entity_definition' ->> 'mondo_id', '')), '_', ':')) || '|' || upper(CASE replace(replace(replace(replace(lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mode_of_inheritance'), ''), evidence_data -> 'entity_definition' ->> 'mode_of_inheritance', ''))), ' ', ''), '_', ''), '-', ''), 'inheritance', '') WHEN 'autosomaldominant' THEN 'ad' WHEN 'hp:0000006' THEN 'ad' WHEN 'autosomalrecessive' THEN 'ar' WHEN 'hp:0000007' THEN 'ar' WHEN 'xlinked' THEN 'xl' WHEN 'hp:0001417' THEN 'xl' WHEN 'xlinkeddominant' THEN 'xld' WHEN 'hp:0001423' THEN 'xld' WHEN 'xlinkedrecessive' THEN 'xlr' WHEN 'hp:0001419' THEN 'xlr' WHEN 'ylinked' THEN 'yl' WHEN 'hp:0001450' THEN 'yl' WHEN 'semidominant' THEN 'sd' WHEN 'hp:0032113' THEN 'sd' WHEN 'mitochondrial' THEN 'mt' WHEN 'hp:0001427' THEN 'mt' ELSE replace(replace(replace(replace(lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mode_of_inheritance'), ''), evidence_data -> 'entity_definition' ->> 'mode_of_inheritance', ''))), ' ', ''), '_', ''), '-', ''), 'inheritance', '') END) || CASE WHEN lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'relationship_type'), ''), evidence_data -> 'entity_definition' ->> 'relationship_type', ''))) = 'susceptibility' THEN '|SUSCEPTIBILITY' ELSE '' END END
    ) STORED;
    CREATE UNIQUE INDEX uq_precurations_open_draft
        ON precurations (gene_id, scope_id, created_by, entity_key) WHERE status = 'draft';
    -- Copies follow a precuration whose key gained the suffix (evidence that already said
    -- susceptibility); a copy the entity indexes refuse keeps its key, with a notice.
    BEGIN
        UPDATE curations c SET entity_key = p.entity_key
            FROM precurations p
            WHERE c.precuration_id = p.id AND c.entity_key <> ''
              AND p.entity_key = c.entity_key || '|SUSCEPTIBILITY';
        UPDATE active_curations ac SET entity_key = c.entity_key
            FROM curations c
            WHERE ac.curation_id = c.id AND ac.entity_key <> ''
              AND c.entity_key = ac.entity_key || '|SUSCEPTIBILITY';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '072: curation keys not re-keyed (an entity index refused it); re-key them by hand';
    END;
END
$migration$;

DO $migration$
DECLARE
    s curation_schemas%ROWTYPE;
    latest methodology_versions%ROWTYPE;
    path TEXT[];
    snap JSONB;
BEGIN
    SELECT * INTO s FROM curation_schemas
        WHERE id = 'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b' FOR UPDATE;
    IF s.id IS NULL THEN
        RETURN;
    END IF;
    SELECT * INTO latest FROM methodology_versions
        WHERE schema_id = s.id ORDER BY version DESC LIMIT 1;
    IF latest.id IS NULL OR methodology_snapshot(s) IS DISTINCT FROM latest.snapshot
       OR jsonb_path_exists(latest.snapshot, '$.** ? (@.id == "relationship_type")') THEN
        RETURN;
    END IF;
    SELECT ARRAY['field_definitions', 'sections', (sec.i - 1)::text,
                 'fields', (fld.j - 1)::text]
        INTO path
        FROM jsonb_array_elements(latest.snapshot -> 'field_definitions' -> 'sections')
             WITH ORDINALITY sec(sc, i),
             jsonb_array_elements(sec.sc -> 'fields') WITH ORDINALITY fld(f, j)
        WHERE fld.f ->> 'id' = 'mode_of_inheritance';
    IF path IS NULL THEN
        RETURN;
    END IF;
    snap := jsonb_insert(latest.snapshot, path, jsonb_build_object(
        'id', 'relationship_type',
        'label', 'Relationship type',
        'type', 'select',
        'required', false,
        'default', 'mendelian',
        'options', jsonb_build_array(
            jsonb_build_object('value', 'mendelian', 'label', 'Mendelian'),
            jsonb_build_object('value', 'susceptibility', 'label', 'Susceptibility (risk allele)')
        ),
        'help_text', 'Susceptibility: a low-penetrance or risk relationship ("disease, susceptibility to")'
    ), true);
    INSERT INTO methodology_versions
        (schema_id, version, snapshot, created_by, derived_from_version_id)
    VALUES (s.id, latest.version + 1, snap, s.created_by, latest.id);
    UPDATE curation_schemas SET field_definitions = snap->'field_definitions'
        WHERE id = s.id;
    RAISE NOTICE '072: published ClinGen Precuration v%', latest.version + 1;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('072_relationship_type.sql')
ON CONFLICT DO NOTHING;
