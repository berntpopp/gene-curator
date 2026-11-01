-- 093: AI curation pipeline (#639). Agent accounts, a per-scope review policy and the kind of
-- each curation's approval. Every existing scope keeps today's behaviour (review_policy
-- 'human'), every existing user is a person, and every approved curation was approved by one.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_agent BOOLEAN NOT NULL DEFAULT FALSE;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_agent_not_admin') THEN
        ALTER TABLE users ADD CONSTRAINT users_agent_not_admin
            CHECK (NOT is_agent OR role::text <> 'admin');
    END IF;
END $$;
COMMENT ON COLUMN users.is_agent IS
    'AI agent account: token-only sign-in, never a platform admin or member manager (#639)';

ALTER TABLE scopes ADD COLUMN IF NOT EXISTS review_policy TEXT NOT NULL DEFAULT 'human';
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'scopes_review_policy_check') THEN
        ALTER TABLE scopes ADD CONSTRAINT scopes_review_policy_check
            CHECK (review_policy IN ('human', 'ai', 'ai_then_human'));
    END IF;
END $$;
COMMENT ON COLUMN scopes.review_policy IS
    'Who may approve: human (agents never), ai (agents may), ai_then_human (a person must too)';

ALTER TABLE curations ADD COLUMN IF NOT EXISTS approval_kind TEXT;
ALTER TABLE curations ADD COLUMN IF NOT EXISTS approval_model TEXT;
UPDATE curations SET approval_kind = 'human'
    WHERE approved_at IS NOT NULL AND approval_kind IS NULL;
COMMENT ON COLUMN curations.approval_kind IS
    'human when a person approved it, ai when only agent accounts did; NULL before approval';
COMMENT ON COLUMN curations.approval_model IS 'The approving agent''s model when approval_kind is ai';

-- A reviewer's approval also stamps the approval kind: 067's guard, with those two columns
CREATE OR REPLACE FUNCTION guard_reviewer_updates()
RETURNS TRIGGER AS $$
DECLARE
    movable CONSTANT TEXT[] := ARRAY[
        'status', 'workflow_stage', 'updated_by', 'updated_at', 'approved_at', 'approved_by',
        'lock_version', 'auto_saved_at', 'computed_fields', 'is_draft',
        'approval_kind', 'approval_model'
    ] || CASE WHEN TG_TABLE_NAME = 'precurations' THEN ARRAY['entity_key'] ELSE '{}' END;
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
VALUES ('093_ai_review_policy.sql')
ON CONFLICT DO NOTHING;
