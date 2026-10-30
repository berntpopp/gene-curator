-- =============================================================================
-- 073: LLM second view queued on submit, opt-in per scope (#464)
-- =============================================================================
-- auto_second_view_on_submit (off by default): a successful curation submit queues the
-- second view under the scope's caps. The run belongs to the admin who last saved the
-- scope settings (they opted in), so the 060/065 run, worker and finding policies apply
-- unchanged. The submitter may not read scope_llm_settings; this function tells them
-- only that owner, and only for a curation in review in a scope they curate in.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

ALTER TABLE scope_llm_settings
    ADD COLUMN IF NOT EXISTS auto_second_view_on_submit BOOLEAN NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION llm_auto_second_view_owner(p_curation_id UUID)
RETURNS UUID AS $$
    SELECT s.updated_by
    FROM curations c
    JOIN scope_llm_settings s ON s.scope_id = c.scope_id
    WHERE c.id = p_curation_id
      AND c.workflow_stage = 'review'
      AND s.enabled AND s.auto_second_view_on_submit
      AND (is_application_admin() OR can_curate_in_scope(c.scope_id))
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;
REVOKE ALL ON FUNCTION llm_auto_second_view_owner(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION llm_auto_second_view_owner(UUID) TO app_user;

INSERT INTO schema_migrations (filename)
VALUES ('073_llm_auto_second_view.sql')
ON CONFLICT DO NOTHING;
