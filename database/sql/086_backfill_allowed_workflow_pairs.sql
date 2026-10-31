-- =============================================================================
-- 086: Allow the workflow pairs a scope already uses (backfill for 082, #284)
-- =============================================================================
-- 082 restricted a scope with a default pair to that default plus its allowed list, but
-- did not backfill the list: after the upgrade, a scope whose curations (or precurations)
-- use another pair got 422 on new work with it. Allow, per scope with a default, its
-- default, every pair its curations use and every active pair of its precurations'
-- schemas. Scopes without a default stay unrestricted (an allowed row would restrict
-- them). Data only; idempotent; records itself.
-- =============================================================================

INSERT INTO scope_workflow_pairs (scope_id, workflow_pair_id)
SELECT s.id, s.default_workflow_pair_id
FROM scopes s
WHERE s.default_workflow_pair_id IS NOT NULL
UNION
SELECT c.scope_id, c.workflow_pair_id
FROM curations c
JOIN scopes s ON s.id = c.scope_id AND s.default_workflow_pair_id IS NOT NULL
WHERE c.workflow_pair_id IS NOT NULL
UNION
SELECT p.scope_id, wp.id
FROM precurations p
JOIN scopes s ON s.id = p.scope_id AND s.default_workflow_pair_id IS NOT NULL
JOIN workflow_pairs wp
    ON wp.precuration_schema_id = p.precuration_schema_id AND wp.is_active
ON CONFLICT DO NOTHING;

INSERT INTO schema_migrations (filename)
VALUES ('086_backfill_allowed_workflow_pairs.sql')
ON CONFLICT DO NOTHING;
