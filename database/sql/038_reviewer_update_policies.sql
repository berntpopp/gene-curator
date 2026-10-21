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
--   that approving a precuration creates (authored by the precuration's author).
--   A BEFORE UPDATE guard stops that path from changing evidence or ownership.
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

-- The curation that approving a precuration creates: a draft linked to that precuration,
-- authored by the precuration's author.
DROP POLICY IF EXISTS curation_review_insert_policy ON curations;
CREATE POLICY curation_review_insert_policy ON curations
    FOR INSERT
    WITH CHECK (
        can_review_work_of(curations.scope_id, curations.created_by)
        AND curations.status = 'draft'
        AND curations.precuration_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM precurations p
            WHERE p.id = curations.precuration_id
              AND p.scope_id = curations.scope_id
              AND p.created_by IS NOT DISTINCT FROM curations.created_by
              AND p.status IN ('submitted', 'in_review', 'approved')
        )
    );

-- A reviewer moves work through review; evidence, gene, scope, authorship and the precuration
-- link are not theirs to change. Admins, authors and curators are unaffected.
CREATE OR REPLACE FUNCTION guard_reviewer_updates()
RETURNS TRIGGER AS $$
DECLARE
    protected TEXT;
BEGIN
    -- No app user: migrations and the owner role, which the reviewer policy never covers
    IF get_current_user_uuid() IS NULL
       OR is_application_admin()
       OR OLD.created_by = get_current_user_uuid()
       OR can_curate_in_scope(OLD.scope_id) THEN
        RETURN NEW;
    END IF;
    FOREACH protected IN ARRAY ARRAY['evidence_data', 'gene_id', 'scope_id', 'created_by', 'precuration_id']
    LOOP
        IF (to_jsonb(NEW) -> protected) IS DISTINCT FROM (to_jsonb(OLD) -> protected) THEN
            RAISE EXCEPTION 'Reviewers cannot change %', protected USING ERRCODE = '42501';
        END IF;
    END LOOP;
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
