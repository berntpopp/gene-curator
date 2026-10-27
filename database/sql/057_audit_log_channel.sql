-- =============================================================================
-- 057: audit_log records the channel and client of a write (#462)
-- =============================================================================
-- Writes made through the MCP server run with app.channel = 'mcp' and app.client = the
-- token name (set transaction-locally by the API, app/mcp/audit.py). This BEFORE INSERT
-- trigger copies them into change_metadata of every audit_log row, whichever trigger or
-- statement writes it; rows from other channels are unchanged. Values come only from
-- the API (inbound X-GC-* headers are stripped), never from the client.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION audit_log_stamp_channel()
RETURNS TRIGGER AS $$
DECLARE
    -- After a set_config in this session the setting reads '' instead of NULL
    channel TEXT := NULLIF(current_setting('app.channel', true), '');
BEGIN
    IF channel IS NOT NULL THEN
        NEW.change_metadata := COALESCE(NEW.change_metadata, '{}'::jsonb)
            || jsonb_build_object(
                'channel', channel,
                'client', NULLIF(current_setting('app.client', true), '')
            );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_audit_log_channel ON audit_log;
CREATE TRIGGER trigger_audit_log_channel
    BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_stamp_channel();

INSERT INTO schema_migrations (filename)
VALUES ('057_audit_log_channel.sql')
ON CONFLICT DO NOTHING;
