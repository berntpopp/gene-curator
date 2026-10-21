-- =============================================================================
-- 041: a curator's resubmit reassigns the earlier reviewers (release blocker)
-- =============================================================================
-- After a reviewer requested changes, the author's resubmit gives every earlier reviewer a new
-- PENDING review (crud/review_round.py reassign_earlier_reviewers), inserted as the resubmitter.
-- review_insert_policy (005) allows only scope reviewers and platform admins, so the resubmit
-- failed with 403.
--
-- Rule: whoever may resubmit (the author or a scope curator/admin) may INSERT a bare PENDING
-- review, assigned by themselves, with no decision fields and not dated ahead, while the curation
-- is in review, for someone who already reviewed that same curation and still holds an accepted,
-- active reviewer/admin membership in its scope. Never for the author or oneself (4-eyes).
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

-- A policy on reviews cannot query reviews itself (infinite recursion): definer function.
CREATE OR REPLACE FUNCTION is_earlier_reviewer(curation_uuid UUID, reviewer_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM reviews WHERE curation_id = curation_uuid AND reviewer_id = reviewer_uuid
    ) AND EXISTS (
        SELECT 1 FROM curations c
        JOIN scope_memberships m ON m.scope_id = c.scope_id
        WHERE c.id = curation_uuid
          AND m.user_id = reviewer_uuid
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND m.role IN ('admin', 'reviewer')
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

COMMENT ON FUNCTION is_earlier_reviewer(UUID, UUID) IS 'Reviewed this curation before and is still an accepted, active reviewer/admin in its scope';

DROP POLICY IF EXISTS review_reassign_insert_policy ON reviews;
CREATE POLICY review_reassign_insert_policy ON reviews
    FOR INSERT
    WITH CHECK (
        reviews.status = 'pending'
        AND reviews.assigned_by = get_current_user_uuid()
        AND reviews.reviewer_id IS DISTINCT FROM get_current_user_uuid()
        AND reviews.recommendation IS NULL
        AND reviews.reviewed_at IS NULL
        AND reviews.comments IS NULL
        -- assigned_at is set app-side; a minute absorbs clock skew, a future date would keep
        -- the review in every later round
        AND reviews.assigned_at <= clock_timestamp() + interval '1 minute'
        AND EXISTS (
            SELECT 1 FROM curations c
            WHERE c.id = reviews.curation_id
              AND (c.created_by = get_current_user_uuid() OR can_curate_in_scope(c.scope_id))
              AND c.created_by IS DISTINCT FROM reviews.reviewer_id
              AND c.status = 'in_review'
        )
        AND is_earlier_reviewer(reviews.curation_id, reviews.reviewer_id)
    );

COMMENT ON POLICY review_reassign_insert_policy ON reviews IS 'On resubmit, the author or a curator re-requests a pending review from an earlier reviewer';

INSERT INTO schema_migrations (filename)
VALUES ('041_resubmit_review_round.sql')
ON CONFLICT DO NOTHING;
