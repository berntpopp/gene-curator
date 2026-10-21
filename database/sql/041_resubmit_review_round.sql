-- =============================================================================
-- 041: a curator's resubmit reassigns the earlier reviewers (release blocker)
-- =============================================================================
-- After a reviewer requested changes, the author's resubmit gives every earlier reviewer a new
-- PENDING review (crud/review_round.py reassign_earlier_reviewers), inserted as the author.
-- review_insert_policy (005) allows only scope reviewers and platform admins, so the resubmit
-- failed with 403.
--
-- Rule: the curation's author may INSERT a bare PENDING review for someone who already reviewed
-- that same curation, while it is in review, assigned by themselves, with no decision fields.
-- Never for themselves (4-eyes).
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

-- A policy on reviews cannot query reviews itself (infinite recursion): definer function.
CREATE OR REPLACE FUNCTION has_reviewed_curation(curation_uuid UUID, reviewer_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM reviews WHERE curation_id = curation_uuid AND reviewer_id = reviewer_uuid
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

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
        AND EXISTS (
            SELECT 1 FROM curations c
            WHERE c.id = reviews.curation_id
              AND c.created_by = get_current_user_uuid()
              AND c.workflow_stage = 'review'
        )
        AND has_reviewed_curation(reviews.curation_id, reviews.reviewer_id)
    );

COMMENT ON POLICY review_reassign_insert_policy ON reviews IS 'The author re-requests a pending review from an earlier reviewer on resubmit';

INSERT INTO schema_migrations (filename)
VALUES ('041_resubmit_review_round.sql')
ON CONFLICT DO NOTHING;
