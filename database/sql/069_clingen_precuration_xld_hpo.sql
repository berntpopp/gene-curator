-- =============================================================================
-- 069: ClinGen Precuration labels X-linked dominant with its own HPO term (Wave 8 monkey r2)
-- =============================================================================
-- 016 labelled XLD "X-linked Dominant (HP:0001417)", but HP:0001417 is X-linked
-- inheritance; X-linked dominant is HP:0001423. The other seeded MOI pairs are right
-- (AD HP:0000006, AR HP:0000007, XLR HP:0001419, SD HP:0032113, MT HP:0001427).
-- Published versions are immutable: when the working copy still equals its latest
-- version, a new version with the corrected label is published. The stored value stays
-- "XLD", so evidence and pins are untouched. Edited working copies are skipped.
-- Idempotent (the old label is then gone) and self-recording.
-- =============================================================================

DO $migration$
DECLARE
    s curation_schemas%ROWTYPE;
    latest methodology_versions%ROWTYPE;
    snap JSONB;
BEGIN
    SELECT * INTO s FROM curation_schemas
        WHERE id = 'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b' FOR UPDATE;
    IF s.id IS NULL THEN
        RETURN;
    END IF;
    SELECT * INTO latest FROM methodology_versions
        WHERE schema_id = s.id ORDER BY version DESC LIMIT 1;
    IF latest.id IS NULL
       OR methodology_snapshot(s) IS DISTINCT FROM latest.snapshot
       OR position('"X-linked Dominant (HP:0001417)"' IN latest.snapshot::text) = 0 THEN
        RETURN;
    END IF;
    snap := replace(
        latest.snapshot::text,
        '"X-linked Dominant (HP:0001417)"',
        '"X-linked Dominant (HP:0001423)"'
    )::jsonb;
    INSERT INTO methodology_versions
        (schema_id, version, snapshot, created_by, derived_from_version_id)
    VALUES (s.id, latest.version + 1, snap, s.created_by, latest.id);
    UPDATE curation_schemas SET field_definitions = snap->'field_definitions'
        WHERE id = s.id;
    RAISE NOTICE '069: published ClinGen Precuration v%', latest.version + 1;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('069_clingen_precuration_xld_hpo.sql')
ON CONFLICT DO NOTHING;
