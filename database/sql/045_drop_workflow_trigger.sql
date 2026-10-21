-- =============================================================================
-- 045: drop the competing workflow trigger (#268)
-- =============================================================================
-- trigger_manage_workflow_transitions (002) rewrote curations.workflow_stage, submitted_at,
-- approved_at and is_draft on status changes: a second state machine next to the workflow
-- engine, which now reads transitions from the pinned methodology version and sets these
-- columns itself. Idempotent; records itself in schema_migrations.
-- =============================================================================

DROP TRIGGER IF EXISTS trigger_manage_workflow_transitions ON curations;
DROP FUNCTION IF EXISTS manage_workflow_transitions();

-- The trigger set is_draft on reject; the engine now does, as the reviewer (038 guard + is_draft)
CREATE OR REPLACE FUNCTION guard_reviewer_updates()
RETURNS TRIGGER AS $$
DECLARE
    movable CONSTANT TEXT[] := ARRAY[
        'status', 'workflow_stage', 'updated_by', 'updated_at', 'approved_at', 'approved_by',
        'lock_version', 'auto_saved_at', 'computed_fields', 'is_draft'
    ];
    rejection CONSTANT TEXT[] := ARRAY['rejection_reason', 'rejected_at', 'rejected_by'];
BEGIN
    -- No app user: migrations and the owner role, which the reviewer policy never covers
    IF get_current_user_uuid() IS NULL
       OR is_application_admin()
       OR OLD.created_by = get_current_user_uuid()
       OR can_curate_in_scope(OLD.scope_id) THEN
        RETURN NEW;
    END IF;
    IF (to_jsonb(NEW) - movable) IS DISTINCT FROM (to_jsonb(OLD) - movable)
       OR (COALESCE(NEW.computed_fields, '{}'::jsonb) - rejection)
          IS DISTINCT FROM (COALESCE(OLD.computed_fields, '{}'::jsonb) - rejection) THEN
        RAISE EXCEPTION 'Reviewers can only move work through review' USING ERRCODE = '42501';
    END IF;
    IF OLD.status = 'active' AND NEW.status IS DISTINCT FROM 'archived' THEN
        RAISE EXCEPTION 'Reviewers can only archive active work' USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public, pg_temp;

INSERT INTO schema_migrations (filename)
VALUES ('045_drop_workflow_trigger.sql')
ON CONFLICT DO NOTHING;
