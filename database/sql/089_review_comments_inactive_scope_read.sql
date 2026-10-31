-- =============================================================================
-- 089: Members of an inactive scope read its review comments (read-only, not hidden)
-- =============================================================================
-- An inactive scope's curations stay readable to its members (the API keeps scope.view);
-- 037's SELECT policy required an active scope, so the comment list came back empty.
-- Only SELECT changes: can_view_review_comments (still active-only) keeps guarding the
-- author's UPDATE, and INSERT stays on can_write_review_comments. Idempotent; records itself.
-- =============================================================================

CREATE OR REPLACE FUNCTION can_read_review_comments(curation_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM curations c
        WHERE c.id = curation_uuid AND is_scope_member(c.scope_id)
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

DROP POLICY IF EXISTS review_item_comments_select_policy ON review_item_comments;
CREATE POLICY review_item_comments_select_policy ON review_item_comments
    FOR SELECT USING (can_read_review_comments(curation_id));

INSERT INTO schema_migrations (filename)
VALUES ('089_review_comments_inactive_scope_read.sql')
ON CONFLICT DO NOTHING;
