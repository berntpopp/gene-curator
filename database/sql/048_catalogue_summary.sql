-- =============================================================================
-- 048: active_curations_summary reads the score keys the scorer stores (#431)
-- =============================================================================
-- 003 extracted computed_scores->>'genetic_evidence_score' and 'experimental_evidence_score',
-- keys nothing writes: the scorer stores '<section>_total' (genetic_evidence_total,
-- experimental_evidence_total) next to total_score, so both columns were always NULL.
-- Same columns as 003 otherwise. CREATE OR REPLACE keeps comment and grants but replaces the
-- view options, so 031's security_invoker is restated. Idempotent; records itself below.
-- =============================================================================

CREATE OR REPLACE VIEW active_curations_summary WITH (security_invoker = true) AS
SELECT
    ac.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    ac.scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,

    -- Active curation details
    ac.curation_id,
    c.computed_verdict,
    c.computed_summary,
    c.evidence_data,
    c.computed_scores,

    -- Workflow information
    wp.name as workflow_pair_name,
    cs.name as schema_name,
    cs.scoring_configuration->>'engine' as scoring_engine,

    -- Attribution
    creator.name as curator_name,
    approver.name as approver_name,
    ac.activated_at,
    activator.name as activator_name,

    -- Scores (extracted from computed_scores JSONB)
    (c.computed_scores->>'total_score')::numeric as total_score,
    (c.computed_scores->>'genetic_evidence_total')::numeric as genetic_score,
    (c.computed_scores->>'experimental_evidence_total')::numeric as experimental_score,

    -- Evidence counts
    jsonb_array_length(c.evidence_data->'genetic_evidence'->'case_level_data') as case_level_count,
    jsonb_array_length(c.evidence_data->'experimental_evidence'->'function') as functional_evidence_count,

    -- Time metrics
    EXTRACT(days FROM (ac.activated_at - c.created_at)) as total_curation_time_days,
    ac.activated_at as last_updated

FROM active_curations ac
JOIN genes g ON ac.gene_id = g.id
JOIN scopes s ON ac.scope_id = s.id
JOIN curations c ON ac.curation_id = c.id
JOIN workflow_pairs wp ON c.workflow_pair_id = wp.id
JOIN curation_schemas cs ON wp.curation_schema_id = cs.id
LEFT JOIN users creator ON c.created_by = creator.id
LEFT JOIN users approver ON c.approved_by = approver.id
LEFT JOIN users activator ON ac.activated_by = activator.id
WHERE ac.archived_at IS NULL
ORDER BY ac.activated_at DESC;

INSERT INTO schema_migrations (filename)
VALUES ('048_catalogue_summary.sql')
ON CONFLICT DO NOTHING;
