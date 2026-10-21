-- =============================================================================
-- 037: per-item review comments (#279)
-- =============================================================================
-- Reviewers anchor comments to an evidence item (item_path, e.g. 'genetic.case_level[a].score');
-- the curation's curator replies and either side resolves them.
--
-- RLS (FORCE, no platform-admin bypass; only accepted, active memberships in an active scope):
--   SELECT  members of the curation's scope
--   INSERT  scope reviewers and admins, and the curation's creator when they are a scope curator
--           (author_id must be the caller); kind 'accepted' only for reviewers and admins who did not create the curation
--   UPDATE  author edits (policy 1); the same people who may insert may resolve (policy 2);
--           a trigger stops non-authors from touching anything but status, and nobody from
--           re-assigning authorship or the anchor
--   DELETE  no policy on purpose: the app never deletes comments, so deletes are denied
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS review_item_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curation_id UUID NOT NULL REFERENCES curations(id) ON DELETE CASCADE,
    review_id UUID REFERENCES reviews(id) ON DELETE SET NULL,
    item_path TEXT NOT NULL CHECK (char_length(item_path) BETWEEN 1 AND 500),
    body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 5000),
    author_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(10) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- kind 'query' is a question or reply; 'accepted' is the reviewer's per-item accept mark
-- (an open accepted row = currently accepted; resolving it withdraws the accept).
ALTER TABLE review_item_comments
    ADD COLUMN IF NOT EXISTS kind VARCHAR(10) NOT NULL DEFAULT 'query'
        CHECK (kind IN ('query', 'accepted'));

CREATE INDEX IF NOT EXISTS idx_review_item_comments_curation
    ON review_item_comments (curation_id, created_at);

-- Helpers read curations/memberships as their owner (BYPASSRLS, like the other RLS helpers).
CREATE OR REPLACE FUNCTION can_view_review_comments(curation_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1
        FROM curations c JOIN scopes s ON s.id = c.scope_id AND s.is_active
        WHERE c.id = curation_uuid AND is_scope_member(c.scope_id)
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION can_write_review_comments(curation_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1
        FROM curations c JOIN scopes s ON s.id = c.scope_id AND s.is_active
        WHERE c.id = curation_uuid
          AND (
              get_user_scope_role(c.scope_id) IN ('admin', 'reviewer')
              OR (get_user_scope_role(c.scope_id) = 'curator'
                  AND c.created_by = get_current_user_uuid())
          )
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

-- Accepting an item is a review decision: reviewers and scope admins only, never on their own
-- curation (a curator may reply).
CREATE OR REPLACE FUNCTION can_accept_review_items(curation_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1
        FROM curations c JOIN scopes s ON s.id = c.scope_id AND s.is_active
        WHERE c.id = curation_uuid
          AND get_user_scope_role(c.scope_id) IN ('admin', 'reviewer')
          AND c.created_by IS DISTINCT FROM get_current_user_uuid()  -- 4-eyes (D1), no admin exception
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

ALTER TABLE review_item_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_item_comments FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS review_item_comments_select_policy ON review_item_comments;
CREATE POLICY review_item_comments_select_policy ON review_item_comments
    FOR SELECT USING (can_view_review_comments(curation_id));

DROP POLICY IF EXISTS review_item_comments_insert_policy ON review_item_comments;
CREATE POLICY review_item_comments_insert_policy ON review_item_comments
    FOR INSERT WITH CHECK (
        author_id = get_current_user_uuid()
        AND can_write_review_comments(curation_id)
        AND (kind = 'query' OR can_accept_review_items(curation_id))
    );

DROP POLICY IF EXISTS review_item_comments_update_author_policy ON review_item_comments;
CREATE POLICY review_item_comments_update_author_policy ON review_item_comments
    FOR UPDATE
    USING (author_id = get_current_user_uuid() AND can_view_review_comments(curation_id))
    WITH CHECK (author_id = get_current_user_uuid());

DROP POLICY IF EXISTS review_item_comments_update_resolve_policy ON review_item_comments;
CREATE POLICY review_item_comments_update_resolve_policy ON review_item_comments
    FOR UPDATE
    USING (
        can_write_review_comments(curation_id)
        AND (kind = 'query' OR can_accept_review_items(curation_id))
    )
    WITH CHECK (
        can_write_review_comments(curation_id)
        AND (kind = 'query' OR can_accept_review_items(curation_id))
    );

CREATE OR REPLACE FUNCTION review_item_comments_guard()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.id <> OLD.id
       OR NEW.curation_id <> OLD.curation_id
       OR NEW.review_id IS DISTINCT FROM OLD.review_id
       OR NEW.item_path <> OLD.item_path
       OR NEW.kind <> OLD.kind
       OR NEW.author_id <> OLD.author_id
       OR NEW.created_at <> OLD.created_at THEN
        RAISE EXCEPTION 'review comment anchor and authorship are immutable'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NEW.body <> OLD.body AND OLD.author_id IS DISTINCT FROM get_current_user_uuid() THEN
        RAISE EXCEPTION 'only the author may edit a review comment'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_review_item_comments_guard ON review_item_comments;
CREATE TRIGGER trigger_review_item_comments_guard
    BEFORE UPDATE ON review_item_comments
    FOR EACH ROW EXECUTE FUNCTION review_item_comments_guard();

INSERT INTO schema_migrations (filename)
VALUES ('037_review_item_comments.sql')
ON CONFLICT DO NOTHING;
