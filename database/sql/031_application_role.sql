-- =============================================================================
-- 031: Runtime role app_user, so row-level security actually applies (#156)
-- =============================================================================
-- POSTGRES_USER is a superuser and bypasses every policy (FORCE RLS only binds table
-- owners). The API connects as app_user: no superuser, no BYPASSRLS, not an owner.
-- Migrations keep running as POSTGRES_USER. Requires APP_DB_PASSWORD in psql's
-- environment (docker initdb, `make db-migrate`); there is no default password.
-- Idempotent: rerunning re-applies grants, policies and the password.
-- =============================================================================

\getenv app_password APP_DB_PASSWORD
\if :{?app_password}
\else
\set app_password ''
\endif
SELECT :'app_password' = '' AS app_password_missing \gset
\if :app_password_missing
DO $$ BEGIN RAISE EXCEPTION 'APP_DB_PASSWORD must be set to create the app_user role'; END $$;
\endif

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user;
    END IF;
END
$$;
ALTER ROLE app_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
SELECT format('ALTER ROLE app_user PASSWORD %L', :'app_password') \gexec

GRANT CONNECT ON DATABASE :"DBNAME" TO app_user;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
REVOKE ALL ON schema_migrations FROM app_user;
-- Tables created by later migrations (run as POSTGRES_USER) get the same grants.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- Views run with their owner's rights unless security_invoker is set, which would let
-- app_user read every scope through them. Later views need the same option.
DO $$
DECLARE
    v record;
BEGIN
    FOR v IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'v'
    LOOP
        EXECUTE format('ALTER VIEW %I SET (security_invoker = true)', v.relname);
    END LOOP;
END
$$;

-- The API sets app.current_user_id per transaction, so outside one the setting is ''
-- rather than missing: treat it as "no user" without a warning per query.
CREATE OR REPLACE FUNCTION get_current_user_uuid()
RETURNS UUID AS $$
DECLARE
    user_uuid UUID;
BEGIN
    user_uuid := CAST(NULLIF(current_setting('app.current_user_id', TRUE), '') AS UUID);
    RETURN user_uuid;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Invalid app.current_user_id: %', SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- active_curations had FORCE RLS but no policy: invisible to everyone but superusers.
DROP POLICY IF EXISTS active_curation_select_policy ON active_curations;
CREATE POLICY active_curation_select_policy ON active_curations
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = active_curations.scope_id AND s.is_public = true
        )
    );
-- Activation happens on approval (reviewer) or by curators/admins.
DROP POLICY IF EXISTS active_curation_insert_policy ON active_curations;
CREATE POLICY active_curation_insert_policy ON active_curations
    FOR INSERT
    WITH CHECK (
        is_application_admin() OR can_curate_in_scope(scope_id) OR can_review_in_scope(scope_id)
    );
DROP POLICY IF EXISTS active_curation_update_policy ON active_curations;
CREATE POLICY active_curation_update_policy ON active_curations
    FOR UPDATE
    USING (
        is_application_admin() OR can_curate_in_scope(scope_id) OR can_review_in_scope(scope_id)
    );

-- Pending invitees must read the scope's name for /me/invitations; membership rights
-- (is_scope_member) still require accepted_at, so they see nothing inside the scope.
DROP POLICY IF EXISTS scope_select_policy ON scopes;
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        is_application_admin()
        OR is_public = true
        OR is_scope_member(id)
        OR created_by = get_current_user_uuid()
        OR EXISTS (
            SELECT 1 FROM scope_memberships m
            WHERE m.scope_id = scopes.id
            AND m.user_id = get_current_user_uuid()
            AND m.is_active = true
            AND m.accepted_at IS NULL
        )
    );

-- Workflow transitions notify other users (reviewer, curator); reading stays own-only.
DROP POLICY IF EXISTS notifications_insert_policy ON notifications;
CREATE POLICY notifications_insert_policy ON notifications
    FOR INSERT
    WITH CHECK (get_current_user_uuid() IS NOT NULL);

-- Dropping log partitions needs the table owner; the endpoint is admin-only.
ALTER FUNCTION cleanup_old_logs(integer) SECURITY DEFINER SET search_path = public, pg_temp;

INSERT INTO schema_migrations (filename) VALUES ('031_application_role.sql')
ON CONFLICT (filename) DO NOTHING;
