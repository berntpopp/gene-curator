-- =============================================================================
-- 054: close the remaining public-scope and inactive-scope leaks (#376, #394)
-- =============================================================================
-- precuration_select_policy (005) showed every precuration of a public scope to anyone, so
-- GET /genes/{id}/progress without scope_id counted outsiders' drafts. Non-members now see a
-- precuration only when an active curation of an active public scope (the 050 rule) was made
-- from it. curations policies query precurations, so a definer function avoids the recursion.
-- curation_update_policy (005) is permissive, so a creator, curator or scope admin could still
-- archive (or edit) curations of an inactive scope past 051. A RESTRICTIVE policy requires an
-- active scope for every UPDATE; deactivating a scope updates scopes, never curations.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION precuration_is_public(precuration_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM curations c JOIN scopes s ON s.id = c.scope_id
        WHERE c.precuration_id = precuration_uuid
          AND c.status = 'active' AND s.is_public AND s.is_active
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

COMMENT ON FUNCTION precuration_is_public(UUID) IS 'An active curation of an active public scope was made from this precuration';

DROP POLICY IF EXISTS precuration_select_policy ON precurations;
CREATE POLICY precuration_select_policy ON precurations
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR precuration_is_public(id)
    );

COMMENT ON POLICY precuration_select_policy ON precurations IS 'Members see their scopes'' precurations; others only those behind a visible active curation';

DROP POLICY IF EXISTS curation_active_scope_update_policy ON curations;
CREATE POLICY curation_active_scope_update_policy ON curations
    AS RESTRICTIVE
    FOR UPDATE
    USING (EXISTS (SELECT 1 FROM scopes s WHERE s.id = curations.scope_id AND s.is_active))
    WITH CHECK (EXISTS (SELECT 1 FROM scopes s WHERE s.id = curations.scope_id AND s.is_active));

COMMENT ON POLICY curation_active_scope_update_policy ON curations IS 'No curation of an inactive scope is updated, whoever asks';

INSERT INTO schema_migrations (filename)
VALUES ('054_public_precurations_and_inactive_scopes.sql')
ON CONFLICT DO NOTHING;
