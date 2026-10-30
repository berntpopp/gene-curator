-- =============================================================================
-- 074: Scope option, approvals only from a signed-in person (#560)
-- =============================================================================
-- approvals_require_session (off by default): when on, approving a precuration or a
-- curation needs a browser session; personal access tokens, MCP OAuth tokens and MCP
-- calls may still comment, request changes and reject. Enforced in the API
-- (core.deps.require_signed_in_approver). Idempotent; records itself.
-- =============================================================================

ALTER TABLE scopes
    ADD COLUMN IF NOT EXISTS approvals_require_session BOOLEAN NOT NULL DEFAULT false;

INSERT INTO schema_migrations (filename)
VALUES ('074_approvals_require_session.sql')
ON CONFLICT DO NOTHING;
