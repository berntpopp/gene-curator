-- =============================================================================
-- 091: Risk alleles in one canonical form (KGDB end-to-end; #614)
-- =============================================================================
-- evidence_data.risk_allele (flat or under entity_definition) of precurations and
-- curations becomes what the API now stores: rs<digits> <BASE> for an rsID with its base
-- (lower-case rs, one space, upper-case A/C/G/T: 'RS17831251c' -> 'rs17831251 C'), any other
-- text trimmed with whitespace collapsed (backend/app/core/risk_allele.py). Precuration keys
-- follow (generated column); a curation or active-curation key copy that equals its
-- precuration's old key follows the new one. Open precurations the rewrite would merge into
-- one entity stop the migration with their ids (as 077 and 088); nothing is changed then.
-- Idempotent: canonical values are left alone. Records itself.
-- =============================================================================

CREATE OR REPLACE FUNCTION pg_temp.canonical_allele(v TEXT) RETURNS TEXT
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN m IS NOT NULL THEN 'rs' || m[1] || ' ' || upper(m[2])
        ELSE btrim(regexp_replace(v, '\s+', ' ', 'g'))
    END
    FROM (SELECT regexp_match(v, '^\s*[Rr][Ss]\s*(\d+)\s*([ACGTacgt])\s*$') AS m) x
$$;

CREATE OR REPLACE FUNCTION pg_temp.with_canonical_allele(e JSONB) RETURNS JSONB
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN jsonb_typeof(e2 -> 'entity_definition' -> 'risk_allele') = 'string'
        THEN jsonb_set(e2, '{entity_definition,risk_allele}', to_jsonb(
            pg_temp.canonical_allele(e2 -> 'entity_definition' ->> 'risk_allele')))
        ELSE e2 END
    FROM (SELECT CASE WHEN jsonb_typeof(e -> 'risk_allele') = 'string'
        THEN jsonb_set(e, '{risk_allele}', to_jsonb(pg_temp.canonical_allele(e ->> 'risk_allele')))
        ELSE e END AS e2) x
$$;

DO $migration$
DECLARE
    dupes TEXT;
BEGIN
    DROP TABLE IF EXISTS allele_fix;
    CREATE TEMP TABLE allele_fix ON COMMIT DROP AS
        SELECT id, gene_id, scope_id, status, created_at, entity_key AS old_key,
               pg_temp.with_canonical_allele(evidence_data) AS fixed
        FROM precurations
        WHERE pg_temp.with_canonical_allele(evidence_data) IS DISTINCT FROM evidence_data;
    IF NOT EXISTS (SELECT 1 FROM allele_fix)
       AND NOT EXISTS (
           SELECT 1 FROM curations
           WHERE pg_temp.with_canonical_allele(evidence_data) IS DISTINCT FROM evidence_data
       ) THEN
        RETURN;
    END IF;
    -- The key part the generated column will compute from the canonical value
    ALTER TABLE allele_fix ADD COLUMN new_key TEXT;
    UPDATE allele_fix SET new_key = CASE
        WHEN old_key ~ '\|SUSCEPTIBILITY\|' THEN regexp_replace(old_key, '[^|]*$', upper(replace(
            trim(COALESCE(NULLIF(trim(fixed ->> 'risk_allele'), ''),
                          fixed -> 'entity_definition' ->> 'risk_allele', '')), ' ', '')))
        ELSE old_key END;
    SELECT string_agg(format('gene %s, scope %s, entity %s: %s',
                             gene_id, scope_id, k, ids), E'\n')
    INTO dupes
    FROM (
        SELECT p.gene_id, p.scope_id, COALESCE(f.new_key, p.entity_key) AS k,
               string_agg(p.id::text, ', ' ORDER BY p.created_at) AS ids
        FROM precurations p LEFT JOIN allele_fix f ON f.id = p.id
        WHERE COALESCE(f.new_key, p.entity_key) <> ''
          AND p.status IN ('draft', 'submitted', 'in_review', 'rejected')
        GROUP BY 1, 2, 3
        HAVING count(*) > 1
    ) d;
    IF dupes IS NOT NULL THEN
        RAISE EXCEPTION E'091: open precurations would share a disease entity:\n%', dupes
            USING HINT = 'Keep one per group and archive the others '
                '(UPDATE precurations SET status = ''archived'' WHERE id IN (...)), '
                'or correct their risk_allele, then re-run.';
    END IF;
    UPDATE precurations p SET evidence_data = f.fixed FROM allele_fix f WHERE p.id = f.id;
    UPDATE curations SET evidence_data = pg_temp.with_canonical_allele(evidence_data)
        WHERE pg_temp.with_canonical_allele(evidence_data) IS DISTINCT FROM evidence_data;
    -- A copy the entity indexes refuse keeps its key, with a notice.
    BEGIN
        UPDATE active_curations ac SET entity_key = p.entity_key
            FROM curations c
            JOIN precurations p ON p.id = c.precuration_id
            JOIN allele_fix f ON f.id = p.id
            WHERE ac.curation_id = c.id AND ac.entity_key = f.old_key
              AND f.old_key <> p.entity_key;
        UPDATE curations c SET entity_key = p.entity_key
            FROM precurations p
            JOIN allele_fix f ON f.id = p.id
            WHERE c.precuration_id = p.id AND c.entity_key = f.old_key
              AND f.old_key <> p.entity_key;
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '091: curation keys not re-keyed (an entity index refused it); re-key them by hand';
    END;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('091_canonical_risk_allele.sql')
ON CONFLICT DO NOTHING;
