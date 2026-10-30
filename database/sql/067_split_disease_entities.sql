-- =============================================================================
-- 067: Split disease entities (#530)
-- =============================================================================
-- The unit of curation is the gene-disease-MOI entity (ClinGen lumping/splitting): one open
-- and one active curation per (gene, scope, entity_key), and one open precuration draft per
-- author and entity. entity_key is the normalised MONDO id | MOI, '' without a MONDO id.
-- Precurations derive it from evidence_data (generated column; same expression as
-- ENTITY_KEY_SQL in backend/app/models/curation.py). Curations copy it once from their
-- precuration at creation. Existing curations take the key of their linked precuration
-- (backfill below); '' is left only without a MONDO id (unlinked or lumped: one per gene, as
-- before). Today every key is unique on (gene, scope), so the re-keyed indexes hold.
-- Idempotent: columns are guarded, indexes are dropped and recreated.
-- =============================================================================

ALTER TABLE precurations
    ADD COLUMN IF NOT EXISTS entity_key TEXT GENERATED ALWAYS AS (
        CASE WHEN upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mondo_id'), ''), evidence_data -> 'entity_definition' ->> 'mondo_id', '')), '_', ':')) = '' THEN '' ELSE upper(replace(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mondo_id'), ''), evidence_data -> 'entity_definition' ->> 'mondo_id', '')), '_', ':')) || '|' || upper(CASE replace(replace(replace(replace(lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mode_of_inheritance'), ''), evidence_data -> 'entity_definition' ->> 'mode_of_inheritance', ''))), ' ', ''), '_', ''), '-', ''), 'inheritance', '') WHEN 'autosomaldominant' THEN 'ad' WHEN 'hp:0000006' THEN 'ad' WHEN 'autosomalrecessive' THEN 'ar' WHEN 'hp:0000007' THEN 'ar' WHEN 'xlinked' THEN 'xl' WHEN 'hp:0001417' THEN 'xl' WHEN 'xlinkeddominant' THEN 'xld' WHEN 'hp:0001423' THEN 'xld' WHEN 'xlinkedrecessive' THEN 'xlr' WHEN 'hp:0001419' THEN 'xlr' WHEN 'ylinked' THEN 'yl' WHEN 'hp:0001450' THEN 'yl' WHEN 'semidominant' THEN 'sd' WHEN 'hp:0032113' THEN 'sd' WHEN 'mitochondrial' THEN 'mt' WHEN 'hp:0001427' THEN 'mt' ELSE replace(replace(replace(replace(lower(trim(COALESCE(NULLIF(trim(evidence_data ->> 'mode_of_inheritance'), ''), evidence_data -> 'entity_definition' ->> 'mode_of_inheritance', ''))), ' ', ''), '_', ''), '-', ''), 'inheritance', '') END) END
    ) STORED;
ALTER TABLE curations ADD COLUMN IF NOT EXISTS entity_key TEXT NOT NULL DEFAULT '';
ALTER TABLE active_curations ADD COLUMN IF NOT EXISTS entity_key TEXT NOT NULL DEFAULT '';

-- Backfill (once: only '' rows): the curation's linked precuration, then the pointer's curation
UPDATE curations c
SET entity_key = p.entity_key
FROM precurations p
WHERE c.precuration_id = p.id AND c.entity_key = '' AND p.entity_key <> '';
UPDATE active_curations ac
SET entity_key = c.entity_key
FROM curations c
WHERE ac.curation_id = c.id AND ac.entity_key = '' AND c.entity_key <> '';

DROP INDEX IF EXISTS uq_curations_one_active;
CREATE UNIQUE INDEX uq_curations_one_active
    ON curations (gene_id, scope_id, entity_key) WHERE status = 'active';

DROP INDEX IF EXISTS uq_active_curation_gene_scope_current;
CREATE UNIQUE INDEX uq_active_curation_gene_scope_current
    ON active_curations (gene_id, scope_id, entity_key) WHERE archived_at IS NULL;

-- Old (gene, scope, author) drafts are unique, so they stay unique with the entity added.
DROP INDEX IF EXISTS uq_precurations_open_draft;
CREATE UNIQUE INDEX uq_precurations_open_draft
    ON precurations (gene_id, scope_id, created_by, entity_key) WHERE status = 'draft';

-- New: the API refused a second open curation, but nothing enforced it. Duplicates are
-- curator data, so they are not touched: skip with a notice, as 033 does.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM curations WHERE status NOT IN ('active', 'archived')
        GROUP BY gene_id, scope_id, entity_key HAVING count(*) > 1
    ) THEN
        RAISE NOTICE 'Several open curations per gene and scope exist; uq_curations_one_open not created. Archive the duplicates and re-run this file.';
    ELSE
        CREATE UNIQUE INDEX IF NOT EXISTS uq_curations_one_open
            ON curations (gene_id, scope_id, entity_key)
            WHERE status NOT IN ('active', 'archived');
    END IF;
END
$$;

-- A BEFORE trigger sees a generated column as NULL in NEW, so the reviewer guard (045) would
-- read every precuration update as an entity_key change. There the key derives from
-- evidence_data, which the guard still compares; on curations reviewers cannot change it.
CREATE OR REPLACE FUNCTION guard_reviewer_updates()
RETURNS TRIGGER AS $$
DECLARE
    movable CONSTANT TEXT[] := ARRAY[
        'status', 'workflow_stage', 'updated_by', 'updated_at', 'approved_at', 'approved_by',
        'lock_version', 'auto_saved_at', 'computed_fields', 'is_draft'
    ] || CASE WHEN TG_TABLE_NAME = 'precurations' THEN ARRAY['entity_key'] ELSE '{}' END;
    rejection CONSTANT TEXT[] := ARRAY['rejection_reason', 'rejected_at', 'rejected_by'];
BEGIN
    -- No app user: migrations and the owner role, which the reviewer policy never covers
    IF get_current_user_uuid() IS NULL
       OR is_application_admin()
       OR OLD.created_by = get_current_user_uuid()
       OR can_curate_in_scope(OLD.scope_id) THEN
        RETURN NEW;
    END IF;
    IF (to_jsonb(NEW) - movable) IS DISTINCT FROM (to_jsonb(OLD) - movable)
       OR (COALESCE(NEW.computed_fields, '{}'::jsonb) - rejection)
          IS DISTINCT FROM (COALESCE(OLD.computed_fields, '{}'::jsonb) - rejection) THEN
        RAISE EXCEPTION 'Reviewers can only move work through review' USING ERRCODE = '42501';
    END IF;
    IF OLD.status = 'active' AND NEW.status IS DISTINCT FROM 'archived' THEN
        RAISE EXCEPTION 'Reviewers can only archive active work' USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public, pg_temp;

INSERT INTO schema_migrations (filename)
VALUES ('067_split_disease_entities.sql')
ON CONFLICT DO NOTHING;
