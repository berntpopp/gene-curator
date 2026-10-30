-- =============================================================================
-- 065: LLM second view: cited findings, proposals and reviewer decisions (#464, #465)
-- =============================================================================
-- A run's validated output is kept as advisory data only: cited findings (llm_findings)
-- and the engine's scores and class for the evidence the model proposed (llm_runs
-- proposed_*). Nothing here writes a curation, a review or a workflow state.
-- Scope reviewers (and admins) request runs, read them and accept or dismiss findings;
-- the curation's own curator cannot decide on findings about their work.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

ALTER TABLE llm_runs ADD COLUMN IF NOT EXISTS proposed_scores JSONB;
ALTER TABLE llm_runs ADD COLUMN IF NOT EXISTS proposed_verdict TEXT;

CREATE TABLE IF NOT EXISTS llm_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES llm_runs(id) ON DELETE CASCADE,
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    citations TEXT[] NOT NULL CHECK (cardinality(citations) > 0),
    decision TEXT CHECK (decision IN ('accepted', 'dismissed')),
    decided_by UUID REFERENCES users(id),
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_llm_findings_curation ON llm_findings (curation_id, created_at);

-- Reviewers request and read runs; scope settings tell their UI whether the feature is on.
DROP POLICY IF EXISTS llm_runs_select_policy ON llm_runs;
CREATE POLICY llm_runs_select_policy ON llm_runs
    FOR SELECT USING (is_application_admin() OR can_review_in_scope(scope_id));
DROP POLICY IF EXISTS llm_runs_insert_policy ON llm_runs;
CREATE POLICY llm_runs_insert_policy ON llm_runs
    FOR INSERT WITH CHECK (
        status = 'queued'
        AND created_by = get_current_user_uuid()
        AND (is_application_admin() OR can_review_in_scope(scope_id))
    );
DROP POLICY IF EXISTS scope_llm_settings_select_policy ON scope_llm_settings;
CREATE POLICY scope_llm_settings_select_policy ON scope_llm_settings
    FOR SELECT USING (is_application_admin() OR can_review_in_scope(scope_id));

ALTER TABLE llm_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_findings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS llm_findings_select_policy ON llm_findings;
CREATE POLICY llm_findings_select_policy ON llm_findings
    FOR SELECT USING (is_application_admin() OR can_review_in_scope(scope_id));
-- Only the worker, as the run's creator, while the run is still running.
DROP POLICY IF EXISTS llm_findings_insert_policy ON llm_findings;
CREATE POLICY llm_findings_insert_policy ON llm_findings
    FOR INSERT WITH CHECK (
        decision IS NULL
        AND EXISTS (
            SELECT 1 FROM llm_runs r
            WHERE r.id = run_id AND r.status = 'running'
            AND r.created_by = get_current_user_uuid()
            AND r.curation_id = llm_findings.curation_id AND r.scope_id = llm_findings.scope_id
        )
    );
DROP POLICY IF EXISTS llm_findings_update_policy ON llm_findings;
CREATE POLICY llm_findings_update_policy ON llm_findings
    FOR UPDATE USING (
        (is_application_admin() OR can_review_in_scope(scope_id))
        AND NOT EXISTS (
            SELECT 1 FROM curations c
            WHERE c.id = curation_id AND c.created_by = get_current_user_uuid()
        )
    )
    WITH CHECK (decided_by = get_current_user_uuid());
-- Decisions are the only change: the finding itself is the model's output.
REVOKE UPDATE ON llm_findings FROM app_user;
GRANT UPDATE (decision, decided_by, decided_at) ON llm_findings TO app_user;

INSERT INTO schema_migrations (filename)
VALUES ('065_llm_second_view.sql')
ON CONFLICT DO NOTHING;
