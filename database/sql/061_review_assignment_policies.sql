-- =============================================================================
-- 061: a curator assigns a peer reviewer to a curation in review (MCP study round 1, finding 4)
-- =============================================================================
-- POST /workflow/curation/{id}/assign-reviewer inserts a PENDING review as the caller.
-- review_insert_policy (005) allows only scope reviewers and platform admins, and 041 only
-- re-requests earlier reviewers, so a curator routing her submitted curation got a 500.
--
-- Rule (mirrors 041): the author or a scope curator/admin may INSERT a bare PENDING review,
-- assigned by themselves, with no decision fields and not dated ahead, while the curation is
-- in review, for an accepted, active reviewer/admin of its scope. Never for the author or
-- oneself (4-eyes). Idempotent; records itself in schema_migrations.
-- =============================================================================

-- scope_memberships RLS may hide other members' rows from the caller: definer function.
CREATE OR REPLACE FUNCTION is_scope_reviewer(scope_uuid UUID, reviewer_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        WHERE m.scope_id = scope_uuid
          AND m.user_id = reviewer_uuid
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND m.role IN ('admin', 'reviewer')
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

COMMENT ON FUNCTION is_scope_reviewer(UUID, UUID) IS 'Accepted, active reviewer/admin of the scope';

DROP POLICY IF EXISTS review_assign_insert_policy ON reviews;
CREATE POLICY review_assign_insert_policy ON reviews
    FOR INSERT
    WITH CHECK (
        reviews.status = 'pending'
        AND reviews.assigned_by = get_current_user_uuid()
        AND reviews.reviewer_id IS DISTINCT FROM get_current_user_uuid()
        AND reviews.recommendation IS NULL
        AND reviews.reviewed_at IS NULL
        AND reviews.comments IS NULL
        AND reviews.assigned_at <= clock_timestamp() + interval '1 minute'
        AND EXISTS (
            SELECT 1 FROM curations c
            WHERE c.id = reviews.curation_id
              AND (c.created_by = get_current_user_uuid() OR can_curate_in_scope(c.scope_id))
              AND c.created_by IS DISTINCT FROM reviews.reviewer_id
              AND c.status = 'in_review'
              AND is_scope_reviewer(c.scope_id, reviews.reviewer_id)
        )
    );

COMMENT ON POLICY review_assign_insert_policy ON reviews IS 'The author or a curator assigns a pending review to a scope reviewer';

INSERT INTO schema_migrations (filename)
VALUES ('061_review_assignment_policies.sql')
ON CONFLICT DO NOTHING;
