-- =============================================================================
-- 086: Allow the workflow pairs a scope already uses (backfill for 082, #284)
-- =============================================================================
-- 082 restricted a scope with a default pair to that default plus its allowed list, but
-- did not backfill the list: after the upgrade, a scope whose curations (or precurations)
-- use another pair got 422 on new work with it. Allow, per scope with a default (always
-- allowed itself), every pair its curations use and the pairs of its precurations'
-- schemas, only those the allowed list may hold (active; global or the scope's own, as
-- _usable_pairs checks). Scopes without a default stay unrestricted (an allowed row would
-- restrict them). Data only; idempotent; records itself.
-- =============================================================================

INSERT INTO scope_workflow_pairs (scope_id, workflow_pair_id)
SELECT c.scope_id, wp.id
FROM curations c
JOIN scopes s ON s.id = c.scope_id AND s.default_workflow_pair_id IS NOT NULL
JOIN workflow_pairs wp
    ON wp.id = c.workflow_pair_id AND wp.is_active
    AND (wp.owner_scope_id IS NULL OR wp.owner_scope_id = c.scope_id)
UNION
SELECT p.scope_id, wp.id
FROM precurations p
JOIN scopes s ON s.id = p.scope_id AND s.default_workflow_pair_id IS NOT NULL
JOIN workflow_pairs wp
    ON wp.precuration_schema_id = p.precuration_schema_id AND wp.is_active
    AND (wp.owner_scope_id IS NULL OR wp.owner_scope_id = p.scope_id)
ON CONFLICT DO NOTHING;

INSERT INTO schema_migrations (filename)
VALUES ('086_backfill_allowed_workflow_pairs.sql')
ON CONFLICT DO NOTHING;
