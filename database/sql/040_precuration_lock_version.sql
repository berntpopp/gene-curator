-- =============================================================================
-- 040: optimistic locking for precurations (release blocker)
-- =============================================================================
-- curations got lock_version in 008, but nothing ever compared it, and precurations had none:
-- with two tabs open the stale save silently overwrote the newer one. The API now compares and
-- increments in one `UPDATE ... WHERE id = ? AND lock_version = ?`; this adds the column and the
-- same safety-net trigger curations have (any other UPDATE also bumps the version, so a stale
-- tab cannot save over a submit, approve or reject either).
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

ALTER TABLE precurations
    ADD COLUMN IF NOT EXISTS lock_version INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN precurations.lock_version IS 'Optimistic locking version number (auto-incremented on update)';

DROP TRIGGER IF EXISTS trigger_increment_lock_version ON precurations;
CREATE TRIGGER trigger_increment_lock_version
    BEFORE UPDATE ON precurations
    FOR EACH ROW
    EXECUTE FUNCTION increment_lock_version();

INSERT INTO schema_migrations (filename)
VALUES ('040_precuration_lock_version.sql')
ON CONFLICT DO NOTHING;
