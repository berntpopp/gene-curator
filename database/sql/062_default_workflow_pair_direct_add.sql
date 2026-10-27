-- =============================================================================
-- 062: default workflow pair + direct member add (MCP study round 1, finding F6)
-- =============================================================================
-- (1) workflow_pairs.is_default: at most one row (partial unique index), seeded on the
--     ClinGen SOP v11 pair from 017; create_scope uses it when no pair is given.
-- (2) POST /scopes/{id}/members adds an existing user as an ACCEPTED member in one step
--     (platform or scope admin; the existing membership_insert_policy already covers it).
--     The added user gets a notification of a new type; invitation_status follows
--     accepted_at on INSERT too, as it already does on UPDATE.
-- (3) membership_update_policy lets a user update their own row; a trigger limits a
--     non-admin's own update to accepting (accepted_at/invitation_status) or declining
--     (is_active true -> false). Role and every other column stay as they are.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

ALTER TABLE workflow_pairs ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_pairs_single_default
    ON workflow_pairs ((true)) WHERE is_default;

UPDATE workflow_pairs SET is_default = true
WHERE id = 'f1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c'
  AND is_active
  AND NOT EXISTS (SELECT 1 FROM workflow_pairs WHERE is_default);

COMMENT ON COLUMN workflow_pairs.is_default IS 'Used by create_scope when no workflow pair is given; at most one';

ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'scope_membership_added';

-- update_invitation_status() reads OLD, which is NULL on INSERT: an accepted insert becomes 'accepted'.
DROP TRIGGER IF EXISTS scope_memberships_invitation_status_insert ON scope_memberships;
CREATE TRIGGER scope_memberships_invitation_status_insert
    BEFORE INSERT ON scope_memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_invitation_status();

CREATE OR REPLACE FUNCTION guard_own_membership_update()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id = get_current_user_uuid()
       AND NOT is_application_admin()
       AND NOT is_scope_admin(OLD.scope_id)
       AND (
           (to_jsonb(NEW) - ARRAY['accepted_at', 'invitation_status', 'is_active', 'updated_at'])
               IS DISTINCT FROM
           (to_jsonb(OLD) - ARRAY['accepted_at', 'invitation_status', 'is_active', 'updated_at'])
           OR (NEW.is_active AND NOT OLD.is_active)
       )
    THEN
        RAISE EXCEPTION 'A member may only accept or decline their own membership'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scope_memberships_guard_own_update ON scope_memberships;
CREATE TRIGGER scope_memberships_guard_own_update
    BEFORE UPDATE ON scope_memberships
    FOR EACH ROW
    EXECUTE FUNCTION guard_own_membership_update();

INSERT INTO schema_migrations (filename)
VALUES ('062_default_workflow_pair_direct_add.sql')
ON CONFLICT DO NOTHING;
