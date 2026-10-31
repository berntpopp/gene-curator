-- =============================================================================
-- 081: Optimistic lock on methodology schemas (#282)
-- =============================================================================
-- Two admins editing one schema: the later save of a stale copy overwrote the earlier
-- one. Every save now bumps lock_version; a save sent with an older lock_version is
-- refused with 409 (crud.optimistic_lock.claim_version). Idempotent; records itself.
-- =============================================================================

ALTER TABLE curation_schemas
    ADD COLUMN IF NOT EXISTS lock_version INTEGER NOT NULL DEFAULT 0;

INSERT INTO schema_migrations (filename)
VALUES ('081_curation_schema_lock_version.sql')
ON CONFLICT DO NOTHING;
