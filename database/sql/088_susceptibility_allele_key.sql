-- =============================================================================
-- 088: Susceptibility entities are one named allele; undetermined and multifactorial MOI (#614)
-- =============================================================================
-- A susceptibility precuration's evidence_data.risk_allele (flat or under
-- entity_definition; rsID, haplotype or genotype) joins its entity_key as a fourth part,
-- MONDO|MOI|SUSCEPTIBILITY|ALLELE (trimmed, spaces removed, upper case), so two risk alleles
-- of one gene and disease are separate entities. Without an allele the key stays as 072 made
-- it, and Mendelian keys are byte-identical. MOI HP:0000005 keys as UNDETERMINED and
-- HP:0001426 as MULTIFACTORIAL, as those labels typed as text already did. Same expression as
-- ENTITY_KEY_SQL in backend/app/models/curation.py. PostgreSQL 15 cannot change a generation
-- expression in place: the column and both open-precuration indexes on it are recreated once
-- (skipped when the expression already has risk_allele); curation and active-curation key
-- copies that equal their precuration's old key follow the new one. Idempotent; records itself.
-- =============================================================================

DO $migration$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_attrdef d
        JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE d.adrelid = 'precurations'::regclass AND a.attname = 'entity_key'
          AND pg_get_expr(d.adbin, d.adrelid) LIKE '%risk_allele%'
    ) THEN
        RETURN;
    END IF;
    CREATE TEMP TABLE old_keys ON COMMIT DROP AS SELECT id, entity_key FROM precurations;
    DROP INDEX IF EXISTS uq_precurations_open_draft;
    DROP INDEX IF EXISTS uq_precurations_open_entity;
    ALTER TABLE precurations DROP COLUMN entity_key;
    ALTER TABLE precurations ADD COLUMN entity_key TEXT GENERATED ALWAYS AS (
        CASE WHEN upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mondo_id'), ''), evidence_data -> 'entity_definition' ->> 'mondo_id', '')), '_', ':')) = '' THEN '' ELSE upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mondo_id'), ''), evidence_data -> 'entity_definition' ->> 'mondo_id', '')), '_', ':')) || '|' || upper(CASE replace(replace(replace(replace(lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mode_of_inheritance'), ''), evidence_data -> 'entity_definition' ->> 'mode_of_inheritance', ''))), ' ', ''), '_', ''), '-', ''), 'inheritance', '') WHEN 'autosomaldominant' THEN 'ad' WHEN 'hp:0000006' THEN 'ad' WHEN 'autosomalrecessive' THEN 'ar' WHEN 'hp:0000007' THEN 'ar' WHEN 'xlinked' THEN 'xl' WHEN 'hp:0001417' THEN 'xl' WHEN 'xlinkeddominant' THEN 'xld' WHEN 'hp:0001423' THEN 'xld' WHEN 'xlinkedrecessive' THEN 'xlr' WHEN 'hp:0001419' THEN 'xlr' WHEN 'ylinked' THEN 'yl' WHEN 'hp:0001450' THEN 'yl' WHEN 'semidominant' THEN 'sd' WHEN 'hp:0032113' THEN 'sd' WHEN 'mitochondrial' THEN 'mt' WHEN 'hp:0001427' THEN 'mt' WHEN 'undetermined' THEN 'undetermined' WHEN 'hp:0000005' THEN 'undetermined' WHEN 'multifactorial' THEN 'multifactorial' WHEN 'hp:0001426' THEN 'multifactorial' ELSE replace(replace(replace(replace(lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mode_of_inheritance'), ''), evidence_data -> 'entity_definition' ->> 'mode_of_inheritance', ''))), ' ', ''), '_', ''), '-', ''), 'inheritance', '') END) || CASE WHEN lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'relationship_type'), ''), evidence_data -> 'entity_definition' ->> 'relationship_type', ''))) = 'susceptibility' THEN '|SUSCEPTIBILITY' || CASE WHEN upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'risk_allele'), ''), evidence_data -> 'entity_definition' ->> 'risk_allele', '')), ' ', '')) = '' THEN '' ELSE '|' || upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'risk_allele'), ''), evidence_data -> 'entity_definition' ->> 'risk_allele', '')), ' ', '')) END ELSE '' END END
    ) STORED;
    CREATE UNIQUE INDEX uq_precurations_open_draft
        ON precurations (gene_id, scope_id, created_by, entity_key) WHERE status = 'draft';
    CREATE UNIQUE INDEX uq_precurations_open_entity
        ON precurations (gene_id, scope_id, entity_key)
        WHERE entity_key <> ''
          AND status IN ('draft', 'submitted', 'in_review', 'rejected');
    -- A copy the entity indexes refuse keeps its key, with a notice.
    BEGIN
        UPDATE active_curations ac SET entity_key = p.entity_key
            FROM curations c
            JOIN precurations p ON p.id = c.precuration_id
            JOIN old_keys o ON o.id = p.id
            WHERE ac.curation_id = c.id AND ac.entity_key <> ''
              AND ac.entity_key = o.entity_key AND o.entity_key <> p.entity_key;
        UPDATE curations c SET entity_key = p.entity_key
            FROM precurations p
            JOIN old_keys o ON o.id = p.id
            WHERE c.precuration_id = p.id AND c.entity_key <> ''
              AND c.entity_key = o.entity_key AND o.entity_key <> p.entity_key;
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '088: curation keys not re-keyed (an entity index refused it); re-key them by hand';
    END;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('088_susceptibility_allele_key.sql')
ON CONFLICT DO NOTHING;
