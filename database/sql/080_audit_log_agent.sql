-- =============================================================================
-- 080: audit_log records the AI agent of an MCP write (#593)
-- =============================================================================
-- An MCP write tool may carry an optional, client-reported agent block {model, agent,
-- tools_used}. The API sets it transaction-locally as app.agent (JSON, app/mcp/audit.py),
-- only for in-process MCP calls. This replaces the 059 stamp so change_metadata also gets
-- agent = the block plus actedOnBehalfOf = the token's user (W3C PROV-O: the software
-- agent acts on behalf of the person). Without a block nothing changes.
-- Also adds curations.row_provenance: who added and last changed each evidence row
-- (app/services/row_provenance.py), kept beside evidence_data, never inside it.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION audit_log_stamp_channel()
RETURNS TRIGGER AS $$
DECLARE
    -- After a set_config in this session the setting reads '' instead of NULL
    channel TEXT := NULLIF(current_setting('app.channel', true), '');
    agent TEXT := NULLIF(current_setting('app.agent', true), '');
BEGIN
    IF channel IS NOT NULL THEN
        NEW.change_metadata := COALESCE(NEW.change_metadata, '{}'::jsonb)
            || jsonb_build_object(
                'channel', channel,
                'client', NULLIF(current_setting('app.client', true), '')
            );
        IF agent IS NOT NULL THEN
            NEW.change_metadata := NEW.change_metadata || jsonb_build_object(
                'agent', agent::jsonb || jsonb_build_object(
                    'actedOnBehalfOf',
                    NULLIF(current_setting('app.current_user_id', true), '')
                )
            );
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE curations ADD COLUMN IF NOT EXISTS row_provenance JSONB;

INSERT INTO schema_migrations (filename)
VALUES ('080_audit_log_agent.sql')
ON CONFLICT DO NOTHING;
