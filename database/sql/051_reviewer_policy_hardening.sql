-- =============================================================================
-- 051: reviewer policy hardening (#394)
-- =============================================================================
-- curation_review_archive_policy (038) checked can_review_in_scope but not that the scope is
-- active; every other reviewer policy does (can_review_work_of). The API already blocks the
-- path; this is defence in depth.
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

INSERT INTO schema_migrations (filename)
VALUES ('051_reviewer_policy_hardening.sql')
ON CONFLICT DO NOTHING;
