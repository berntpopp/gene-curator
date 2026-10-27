-- =============================================================================
-- 051: reviewer policy hardening (#394, #375)
-- =============================================================================
-- curation_review_archive_policy (038) checked can_review_in_scope but not that the scope is
-- active; every other reviewer policy does (can_review_work_of). The API already blocks the
-- path; this is defence in depth.
-- Per-item accepts (037): only the reviewer who accepted may withdraw (resolve) or restore it,
-- and only while they may still accept; the resolve policy covers queries only. Without this,
-- any reviewer or scope admin flipped another's accept unrecorded, and a demoted reviewer
-- flipped their own through the author policy.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

DROP POLICY IF EXISTS curation_review_archive_policy ON curations;
CREATE POLICY curation_review_archive_policy ON curations
    FOR UPDATE
    USING (
        can_review_in_scope(scope_id) AND status = 'active'
        AND EXISTS (SELECT 1 FROM scopes s WHERE s.id = curations.scope_id AND s.is_active)
    )
    WITH CHECK (
        can_review_in_scope(scope_id) AND status = 'archived'
        AND EXISTS (SELECT 1 FROM scopes s WHERE s.id = curations.scope_id AND s.is_active)
    );

DROP POLICY IF EXISTS review_item_comments_update_author_policy ON review_item_comments;
CREATE POLICY review_item_comments_update_author_policy ON review_item_comments
    FOR UPDATE
    USING (
        author_id = get_current_user_uuid() AND can_view_review_comments(curation_id)
        AND (kind = 'query' OR can_accept_review_items(curation_id))
    )
    WITH CHECK (
        author_id = get_current_user_uuid()
        AND (kind = 'query' OR can_accept_review_items(curation_id))
    );

DROP POLICY IF EXISTS review_item_comments_update_resolve_policy ON review_item_comments;
CREATE POLICY review_item_comments_update_resolve_policy ON review_item_comments
    FOR UPDATE
    USING (can_write_review_comments(curation_id) AND kind = 'query')
    WITH CHECK (can_write_review_comments(curation_id) AND kind = 'query');

INSERT INTO schema_migrations (filename)
VALUES ('051_reviewer_policy_hardening.sql')
ON CONFLICT DO NOTHING;
