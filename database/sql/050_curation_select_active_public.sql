-- =============================================================================
-- 050: non-members see only ACTIVE curations of public scopes (#376)
-- =============================================================================
-- curation_select_policy (005) let any session, anonymous included, read every curation of a
-- public scope, drafts too. The app filters drafts (crud/scope_visibility), but an endpoint that
-- relies on RLS alone (GET /curations/{id}) leaked them. Members keep seeing all of their scope's
-- work; the existing platform-admin clause is unchanged.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

DROP POLICY IF EXISTS curation_select_policy ON curations;
CREATE POLICY curation_select_policy ON curations
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR (
            status = 'active'
            AND EXISTS (
                SELECT 1 FROM scopes s
                WHERE s.id = curations.scope_id AND s.is_public = true
            )
        )
    );

COMMENT ON POLICY curation_select_policy ON curations IS 'Members see their scopes'' curations; everyone sees active curations of public scopes';

INSERT INTO schema_migrations (filename)
VALUES ('050_curation_select_active_public.sql')
ON CONFLICT DO NOTHING;
