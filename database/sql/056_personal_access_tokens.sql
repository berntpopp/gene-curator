-- =============================================================================
-- 056: personal access tokens (#462, slice a)
-- =============================================================================
-- Per-user API tokens for MCP clients and scripts. Only the sha256 hash of the token is
-- stored; the plaintext is shown once at creation. A token acts as its owner (RLS and
-- scope roles apply unchanged); scopes may only narrow access. RLS: a user sees, creates
-- and revokes only their own tokens; nobody deletes (revocation sets revoked_at).
-- Authentication runs before the RLS user is known, so it resolves the token through the
-- SECURITY DEFINER function below, which only ever returns the owner of a live token.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS personal_access_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    token_prefix VARCHAR(16) NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{read,write}',
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT personal_access_tokens_scopes_check
        CHECK (scopes <@ ARRAY['read', 'write']::TEXT[] AND cardinality(scopes) > 0)
);

CREATE INDEX IF NOT EXISTS idx_personal_access_tokens_user
    ON personal_access_tokens (user_id, created_at);

ALTER TABLE personal_access_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE personal_access_tokens FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS personal_access_tokens_select_policy ON personal_access_tokens;
CREATE POLICY personal_access_tokens_select_policy ON personal_access_tokens
    FOR SELECT USING (user_id = get_current_user_uuid());
DROP POLICY IF EXISTS personal_access_tokens_insert_policy ON personal_access_tokens;
CREATE POLICY personal_access_tokens_insert_policy ON personal_access_tokens
    FOR INSERT WITH CHECK (user_id = get_current_user_uuid());
DROP POLICY IF EXISTS personal_access_tokens_update_policy ON personal_access_tokens;
CREATE POLICY personal_access_tokens_update_policy ON personal_access_tokens
    FOR UPDATE USING (user_id = get_current_user_uuid())
    WITH CHECK (user_id = get_current_user_uuid());

-- Returns the owner and scopes of a live (unrevoked, unexpired) token and stamps
-- last_used_at; returns no row otherwise.
CREATE OR REPLACE FUNCTION authenticate_personal_access_token(p_token_hash TEXT)
RETURNS TABLE (user_id UUID, scopes TEXT[]) AS $$
    UPDATE personal_access_tokens t
    SET last_used_at = NOW()
    WHERE t.token_hash = p_token_hash
      AND t.revoked_at IS NULL
      AND t.expires_at > NOW()
    RETURNING t.user_id, t.scopes;
$$ LANGUAGE SQL VOLATILE SECURITY DEFINER SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION authenticate_personal_access_token(TEXT) FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        GRANT SELECT, INSERT, UPDATE ON personal_access_tokens TO app_user;
        GRANT EXECUTE ON FUNCTION authenticate_personal_access_token(TEXT) TO app_user;
    END IF;
END $$;

INSERT INTO schema_migrations (filename)
VALUES ('056_personal_access_tokens.sql')
ON CONFLICT DO NOTHING;
