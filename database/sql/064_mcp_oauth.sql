-- =============================================================================
-- 064: MCP OAuth 2.1 with dynamic client registration (#462, phase 2)
-- =============================================================================
-- MCP clients (Claude Code, Claude.ai) register themselves (RFC 7591), send the user
-- to the consent page and exchange the authorization code (PKCE S256) for tokens.
-- The access token IS a personal access token row (056), so the API treats an OAuth
-- call exactly like a PAT call: RLS, scope roles, D1 and the account-operation block.
-- One grant row per authorization: pending (user_id NULL) until consent, then it holds
-- the hashed code, later the hashed refresh token. Refresh rotates the refresh token
-- and the access token's hash in place, so a grant is one row in the token list and
-- revoking that row there ends the grant. Only sha256 hashes are stored.
-- app_user still cannot UPDATE a PAT beyond revoked_at (056): rotation runs in the
-- SECURITY DEFINER function below, only for a grant's own token, with fixed lifetimes.
-- The token endpoint runs before the user is known, so it resolves a code or refresh
-- token hash through the SECURITY DEFINER function below, which returns only the owner.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret_hash CHAR(64),
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oauth_grants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    params JSONB NOT NULL,
    code_hash CHAR(64) UNIQUE,
    refresh_token_hash CHAR(64) UNIQUE,
    access_token_id UUID REFERENCES personal_access_tokens(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oauth_grants_user ON oauth_grants (user_id);

-- Registration is anonymous (RFC 7591): every role reads and registers clients
ALTER TABLE oauth_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE oauth_clients FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS oauth_clients_select_policy ON oauth_clients;
CREATE POLICY oauth_clients_select_policy ON oauth_clients FOR SELECT USING (true);
DROP POLICY IF EXISTS oauth_clients_insert_policy ON oauth_clients;
CREATE POLICY oauth_clients_insert_policy ON oauth_clients FOR INSERT WITH CHECK (true);

-- A pending request has no owner yet; consent binds it to the signed-in user
ALTER TABLE oauth_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE oauth_grants FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS oauth_grants_select_policy ON oauth_grants;
CREATE POLICY oauth_grants_select_policy ON oauth_grants
    FOR SELECT USING (user_id IS NULL OR user_id = get_current_user_uuid());
DROP POLICY IF EXISTS oauth_grants_insert_policy ON oauth_grants;
CREATE POLICY oauth_grants_insert_policy ON oauth_grants
    FOR INSERT WITH CHECK (user_id IS NULL);
DROP POLICY IF EXISTS oauth_grants_update_policy ON oauth_grants;
CREATE POLICY oauth_grants_update_policy ON oauth_grants
    FOR UPDATE USING (user_id IS NULL OR user_id = get_current_user_uuid())
    WITH CHECK (user_id = get_current_user_uuid());
DROP POLICY IF EXISTS oauth_grants_delete_policy ON oauth_grants;
CREATE POLICY oauth_grants_delete_policy ON oauth_grants
    FOR DELETE USING (user_id IS NULL OR user_id = get_current_user_uuid());

CREATE OR REPLACE FUNCTION oauth_grant_owner(p_hash TEXT)
RETURNS UUID AS $$
    SELECT g.user_id FROM oauth_grants g
    WHERE g.code_hash = p_hash OR g.refresh_token_hash = p_hash;
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION oauth_grant_owner(TEXT) FROM PUBLIC;

-- Refresh: swap the refresh token and give the grant's live access token a new hash
-- and an hour, scopes only narrowing. False (nothing changed) when the refresh token is
-- unknown, used, expired or its access token was revoked. Lifetimes match mcp/oauth.py.
CREATE OR REPLACE FUNCTION oauth_rotate_refresh_token(
    p_old_hash TEXT, p_new_hash TEXT, p_access_hash TEXT, p_access_prefix TEXT,
    p_scopes TEXT[]
) RETURNS BOOLEAN AS $$
DECLARE
    v_grant UUID;
    v_pat UUID;
BEGIN
    SELECT g.id, g.access_token_id INTO v_grant, v_pat
    FROM oauth_grants g
    JOIN personal_access_tokens t ON t.id = g.access_token_id
    WHERE g.refresh_token_hash = p_old_hash
      AND g.expires_at > NOW()
      AND t.revoked_at IS NULL
      AND p_scopes <@ t.scopes
    FOR UPDATE OF g, t;
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    UPDATE oauth_grants
    SET refresh_token_hash = p_new_hash, expires_at = NOW() + INTERVAL '30 days'
    WHERE id = v_grant;
    UPDATE personal_access_tokens
    SET token_hash = p_access_hash, token_prefix = p_access_prefix, scopes = p_scopes,
        expires_at = NOW() + INTERVAL '1 hour'
    WHERE id = v_pat;
    RETURN true;
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION oauth_rotate_refresh_token(TEXT, TEXT, TEXT, TEXT, TEXT[])
    FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        REVOKE UPDATE, DELETE ON oauth_clients FROM app_user;
        GRANT SELECT, INSERT ON oauth_clients TO app_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_grants TO app_user;
        GRANT EXECUTE ON FUNCTION oauth_grant_owner(TEXT) TO app_user;
        GRANT EXECUTE ON FUNCTION
            oauth_rotate_refresh_token(TEXT, TEXT, TEXT, TEXT, TEXT[]) TO app_user;
    END IF;
END $$;

INSERT INTO schema_migrations (filename)
VALUES ('064_mcp_oauth.sql')
ON CONFLICT DO NOTHING;
