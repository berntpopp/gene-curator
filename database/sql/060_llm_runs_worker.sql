-- =============================================================================
-- 060: LLM run worker: enqueue, claim and finish paths on llm_runs (#489, runtime slice)
-- =============================================================================
-- Enqueue: a scope admin (or platform admin, like the 057 SELECT policy) inserts a queued
-- run as themselves. started_at is set at claim, so stuck runs can be failed. Claim: llm_claim_run() moves one queued run to running with
-- FOR UPDATE SKIP LOCKED and returns only its id and creator; the worker then sets
-- app.current_user_id to that creator for everything else. Finish: the creator's context
-- may move its own running run to succeeded or failed, once; finished runs are final.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

ALTER TABLE llm_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;

DROP POLICY IF EXISTS llm_runs_insert_policy ON llm_runs;
CREATE POLICY llm_runs_insert_policy ON llm_runs
    FOR INSERT WITH CHECK (
        status = 'queued'
        AND created_by = get_current_user_uuid()
        AND (is_application_admin() OR is_scope_admin(scope_id))
    );

DROP POLICY IF EXISTS llm_runs_update_policy ON llm_runs;
CREATE POLICY llm_runs_update_policy ON llm_runs
    FOR UPDATE USING (status = 'running' AND created_by = get_current_user_uuid())
    WITH CHECK (
        status IN ('succeeded', 'failed') AND created_by = get_current_user_uuid()
    );

-- The worker has no user of its own; this returns only (id, creator) of the run it claimed.
-- Runs left running for 10 minutes (a crashed worker) fail first, releasing their cap
-- reservation; no call outlives that (timeouts are clamped to 60 s).
CREATE OR REPLACE FUNCTION llm_claim_run()
RETURNS TABLE (run_id UUID, run_by UUID) AS $$
    UPDATE llm_runs SET status = 'failed', error_code = 'interrupted', finished_at = now()
    WHERE status = 'running' AND started_at < now() - interval '10 minutes';

    UPDATE llm_runs SET status = 'running', started_at = now()
    WHERE id = (
        SELECT id FROM llm_runs
        WHERE status = 'queued' AND created_by IS NOT NULL
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING id, created_by
$$ LANGUAGE SQL VOLATILE SECURITY DEFINER SET search_path = public, pg_temp;
REVOKE ALL ON FUNCTION llm_claim_run() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION llm_claim_run() TO app_user;

INSERT INTO schema_migrations (filename)
VALUES ('060_llm_runs_worker.sql')
ON CONFLICT DO NOTHING;
