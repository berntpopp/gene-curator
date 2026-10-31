-- =============================================================================
-- 084: per-user saved views (#276)
-- =============================================================================
-- The catalogue matrix remembers which scope columns a user shows, and in what order,
-- across browsers. One row per user and view; value is the view's JSON state. RLS: a
-- user reads and writes only their own rows; nobody deletes (a reset saves an empty
-- view). Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_view_preferences (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    view VARCHAR(50) NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, view)
);

ALTER TABLE user_view_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_view_preferences FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_view_preferences_select_policy ON user_view_preferences;
CREATE POLICY user_view_preferences_select_policy ON user_view_preferences
    FOR SELECT USING (user_id = get_current_user_uuid());
DROP POLICY IF EXISTS user_view_preferences_insert_policy ON user_view_preferences;
CREATE POLICY user_view_preferences_insert_policy ON user_view_preferences
    FOR INSERT WITH CHECK (user_id = get_current_user_uuid());
DROP POLICY IF EXISTS user_view_preferences_update_policy ON user_view_preferences;
CREATE POLICY user_view_preferences_update_policy ON user_view_preferences
    FOR UPDATE USING (user_id = get_current_user_uuid())
    WITH CHECK (user_id = get_current_user_uuid());

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        -- 031's default privileges grant everything; the API never deletes.
        REVOKE DELETE ON user_view_preferences FROM app_user;
        GRANT SELECT, INSERT, UPDATE ON user_view_preferences TO app_user;
    END IF;
END $$;

INSERT INTO schema_migrations (filename)
VALUES ('084_user_view_preferences.sql')
ON CONFLICT DO NOTHING;
