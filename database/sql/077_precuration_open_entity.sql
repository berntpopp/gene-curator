-- =============================================================================
-- 077: One open precuration per disease entity, enforced in the database (#567)
-- =============================================================================
-- The API refused a second open precuration of a gene, scope and entity_key by a check
-- before insert, so concurrent creates by different curators could all pass. A partial
-- unique index now refuses them (statuses draft, submitted, in_review, rejected; '' names
-- no entity). The approved-but-uncurated case stays a check in crud.precuration_entity.
-- Existing duplicates stop the migration with their ids; nothing is deleted. Resolve them
-- by archiving all but one per group, then re-run. Idempotent; records itself.
-- =============================================================================

DO $migration$
DECLARE
    dupes TEXT;
BEGIN
    SELECT string_agg(format('gene %s, scope %s, entity %s: %s',
                             gene_id, scope_id, entity_key, ids), E'\n')
    INTO dupes
    FROM (
        SELECT gene_id, scope_id, entity_key,
               string_agg(id::text, ', ' ORDER BY created_at) AS ids
        FROM precurations
        WHERE entity_key <> ''
          AND status IN ('draft', 'submitted', 'in_review', 'rejected')
        GROUP BY gene_id, scope_id, entity_key
        HAVING count(*) > 1
    ) d;
    IF dupes IS NOT NULL THEN
        RAISE EXCEPTION E'077: open precurations share a disease entity:\n%', dupes
            USING HINT = 'Keep one per group and archive the others '
                '(UPDATE precurations SET status = ''archived'' WHERE id IN (...)), '
                'then re-run. List them with: SELECT gene_id, scope_id, entity_key, '
                'array_agg(id ORDER BY created_at) FROM precurations WHERE entity_key <> '''' '
                'AND status IN (''draft'', ''submitted'', ''in_review'', ''rejected'') '
                'GROUP BY 1, 2, 3 HAVING count(*) > 1;';
    END IF;
END
$migration$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_precurations_open_entity
    ON precurations (gene_id, scope_id, entity_key)
    WHERE entity_key <> ''
      AND status IN ('draft', 'submitted', 'in_review', 'rejected');

INSERT INTO schema_migrations (filename)
VALUES ('077_precuration_open_entity.sql')
ON CONFLICT DO NOTHING;
