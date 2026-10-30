-- =============================================================================
-- 070: ClinGen Precuration offers X-linked and Undetermined MOI (#531)
-- =============================================================================
-- ClinGen GCI's MOI table has X-linked (HP:0001417) and Undetermined (HP:0000005);
-- the seeded schema had neither. XL is inserted before XLD and Undetermined before
-- Other; XLD and XLR stay, so stored values and pins are untouched.
-- Published versions are immutable: when the working copy still equals its latest
-- version, a new version with the two options is published. Edited working copies
-- are skipped. Idempotent (XL is then present) and self-recording.
-- =============================================================================

DO $migration$
DECLARE
    s curation_schemas%ROWTYPE;
    latest methodology_versions%ROWTYPE;
    path TEXT[];
    opts JSONB;
    snap JSONB;
BEGIN
    SELECT * INTO s FROM curation_schemas
        WHERE id = 'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b' FOR UPDATE;
    IF s.id IS NULL THEN
        RETURN;
    END IF;
    SELECT * INTO latest FROM methodology_versions
        WHERE schema_id = s.id ORDER BY version DESC LIMIT 1;
    IF latest.id IS NULL OR methodology_snapshot(s) IS DISTINCT FROM latest.snapshot THEN
        RETURN;
    END IF;
    SELECT ARRAY['field_definitions', 'sections', (sec.i - 1)::text,
                 'fields', (fld.j - 1)::text, 'options'], fld.f -> 'options'
        INTO path, opts
        FROM jsonb_array_elements(latest.snapshot -> 'field_definitions' -> 'sections')
             WITH ORDINALITY sec(sc, i),
             jsonb_array_elements(sec.sc -> 'fields') WITH ORDINALITY fld(f, j)
        WHERE fld.f ->> 'id' = 'mode_of_inheritance';
    IF opts IS NULL OR opts @> '[{"value": "XL"}]'
       OR NOT opts @> '[{"value": "XLD"}, {"value": "Other"}]' THEN
        RETURN;
    END IF;
    SELECT jsonb_agg(o ORDER BY ord) INTO opts FROM (
        SELECT e AS o, k * 2 AS ord FROM jsonb_array_elements(opts) WITH ORDINALITY x(e, k)
        UNION ALL
        SELECT CASE e ->> 'value'
                   WHEN 'XLD' THEN '{"value": "XL", "label": "X-linked (HP:0001417)"}'::jsonb
                   ELSE '{"value": "Undetermined", "label": "Undetermined (HP:0000005)"}'::jsonb
               END, k * 2 - 1
            FROM jsonb_array_elements(opts) WITH ORDINALITY x(e, k)
            WHERE e ->> 'value' IN ('XLD', 'Other')
    ) t;
    snap := jsonb_set(latest.snapshot, path, opts);
    INSERT INTO methodology_versions
        (schema_id, version, snapshot, created_by, derived_from_version_id)
    VALUES (s.id, latest.version + 1, snap, s.created_by, latest.id);
    UPDATE curation_schemas SET field_definitions = snap->'field_definitions'
        WHERE id = s.id;
    RAISE NOTICE '070: published ClinGen Precuration v%', latest.version + 1;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('070_clingen_precuration_moi_xl_undetermined.sql')
ON CONFLICT DO NOTHING;
