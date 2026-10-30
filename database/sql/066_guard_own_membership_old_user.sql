-- =============================================================================
-- 066: guard_own_membership_update() keys on OLD.user_id (Wave 7 follow-up)
-- =============================================================================
-- 062 tested NEW.user_id, so a member who also admins another scope could move their own
-- removed row there under another user_id and reactivate it past the guard. The row's
-- owner is OLD.user_id. Idempotent (CREATE OR REPLACE); records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION guard_own_membership_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.user_id = get_current_user_uuid()
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

INSERT INTO schema_migrations (filename)
VALUES ('066_guard_own_membership_old_user.sql')
ON CONFLICT DO NOTHING;
