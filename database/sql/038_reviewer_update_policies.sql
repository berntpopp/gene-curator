-- =============================================================================
-- 038: scope reviewers can act on work under review (release blocker)
-- =============================================================================
-- The UPDATE policies on precurations and curations (005) allowed only platform admins, the
-- creator and scope curators/admins, so a scope reviewer approving a precuration or sending a
-- curation back from review updated 0 rows and the API failed with StaleDataError (500).
-- Approving a precuration also inserts the curation it creates, which needs curator rights.
--
-- Rule (no platform-admin bypass beyond the existing one, D1 kept: never one's own work):
--   a reviewer or scope admin, with an accepted active membership in an ACTIVE scope, may
--   UPDATE work that someone else authored while it is under review, and INSERT the curation
--   that approving a precuration creates (authored by the precuration's author), and archive
--   the previous active curation when approving a re-curation.
--   A BEFORE UPDATE guard limits that path to status/stage/approval columns.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION can_review_work_of(scope_uuid UUID, author UUID)
RETURNS BOOLEAN AS $$
    SELECT can_review_in_scope(scope_uuid)
       AND author IS DISTINCT FROM get_current_user_uuid()
       AND EXISTS (SELECT 1 FROM scopes WHERE id = scope_uuid AND is_active)
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

COMMENT ON FUNCTION can_review_work_of(UUID, UUID) IS 'Reviewer or scope admin of an active scope, and not the author (4-eyes)';

DROP POLICY IF EXISTS precuration_review_update_policy ON precurations;
CREATE POLICY precuration_review_update_policy ON precurations
    FOR UPDATE
    USING (can_review_work_of(scope_id, created_by) AND status IN ('submitted', 'in_review'))
    WITH CHECK (can_review_work_of(scope_id, created_by));

DROP POLICY IF EXISTS curation_review_update_policy ON curations;
CREATE POLICY curation_review_update_policy ON curations
    FOR UPDATE
    USING (
        can_review_work_of(scope_id, created_by)
        AND status IN ('submitted', 'in_review', 'approved')
    )
    WITH CHECK (can_review_work_of(scope_id, created_by));

-- Approving a re-curation archives the gene's previous ACTIVE curation in the same transaction
-- (crud/activation.py). Only active -> archived; the guard below also pins the new status,
-- because permissive WITH CHECKs OR together with the review policy above.
DROP POLICY IF EXISTS curation_review_archive_policy ON curations;
CREATE POLICY curation_review_archive_policy ON curations
    FOR UPDATE
    USING (can_review_in_scope(scope_id) AND status = 'active')
    WITH CHECK (can_review_in_scope(scope_id) AND status = 'archived');

-- The curation that approving a precuration creates, exactly as the approve path inserts it:
-- the only curation of a precuration approved in this transaction, a fresh draft with the
-- precuration's gene, author and workflow pair, nothing computed, submitted or approved.
-- ponytail: evidence_data is the Python-side prefill of the precuration's evidence and is not
-- re-derived here; the guard stops later edits.
-- A policy on curations cannot query curations itself (infinite recursion): definer function.
CREATE OR REPLACE FUNCTION precuration_has_curation(precuration_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM curations WHERE precuration_id = precuration_uuid)
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

DROP POLICY IF EXISTS curation_review_insert_policy ON curations;
CREATE POLICY curation_review_insert_policy ON curations
    FOR INSERT
    WITH CHECK (
        can_review_work_of(curations.scope_id, curations.created_by)
        AND curations.status = 'draft'
        AND curations.workflow_stage = 'curation'
        AND curations.is_draft
        AND COALESCE(curations.computed_scores, '{}'::jsonb) = '{}'::jsonb
        AND COALESCE(curations.computed_fields, '{}'::jsonb) = '{}'::jsonb
        AND curations.computed_verdict IS NULL
        AND curations.computed_summary IS NULL
        AND curations.submitted_at IS NULL AND curations.submitted_by IS NULL
        AND curations.approved_at IS NULL AND curations.approved_by IS NULL
        AND curations.precuration_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM precurations p
            JOIN workflow_pairs wp ON wp.precuration_schema_id = p.precuration_schema_id
            WHERE p.id = curations.precuration_id
              AND p.scope_id = curations.scope_id
              AND p.gene_id = curations.gene_id
              AND wp.id = curations.workflow_pair_id
              AND p.created_by IS NOT DISTINCT FROM curations.created_by
              AND p.status = 'approved'
        )
        AND NOT precuration_has_curation(curations.precuration_id)
    );

-- A reviewer moves work through review and may change nothing else (allowlist): not evidence,
-- scores, verdicts, gene, scope, authorship or links. Rejecting a precuration also records
-- rejection_* keys in computed_fields; an active curation may only be archived.
-- lock_version and auto_saved_at are set by their own triggers. Admins, authors and curators
-- are unaffected.
CREATE OR REPLACE FUNCTION guard_reviewer_updates()
RETURNS TRIGGER AS $$
DECLARE
    movable CONSTANT TEXT[] := ARRAY[
        'status', 'workflow_stage', 'updated_by', 'updated_at', 'approved_at', 'approved_by',
        'lock_version', 'auto_saved_at', 'computed_fields'
    ];
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

DROP TRIGGER IF EXISTS trigger_guard_reviewer_updates ON precurations;
CREATE TRIGGER trigger_guard_reviewer_updates
    BEFORE UPDATE ON precurations
    FOR EACH ROW EXECUTE FUNCTION guard_reviewer_updates();

DROP TRIGGER IF EXISTS trigger_guard_reviewer_updates ON curations;
CREATE TRIGGER trigger_guard_reviewer_updates
    BEFORE UPDATE ON curations
    FOR EACH ROW EXECUTE FUNCTION guard_reviewer_updates();

INSERT INTO schema_migrations (filename)
VALUES ('038_reviewer_update_policies.sql')
ON CONFLICT DO NOTHING;
