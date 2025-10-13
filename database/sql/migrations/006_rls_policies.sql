-- =============================================================================
-- Migration 006: Row Level Security Policies (OPTIMIZED & SECURE)
-- =============================================================================
-- Description: Create RLS policies for all scope-sensitive tables
-- Author: Claude Code (Automated Migration)
-- Date: 2025-10-13
-- Dependencies: 001-005 (enums, users, scope_memberships, RLS functions, RLS enabled)
-- Performance: Uses STABLE functions from 004_rls_functions.sql for query caching
-- Security: Policies prevent cross-tenant data access
-- =============================================================================

-- =============================================================================
-- SCOPE RLS POLICIES (Core Multi-Tenancy)
-- =============================================================================

-- Policy: SELECT scopes - Users can see scopes they're members of or public scopes
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        is_application_admin()      -- App admins see all scopes
        OR is_public = true          -- Public scopes visible to all authenticated users
        OR is_scope_member(id)       -- Members see their scopes (STABLE function)
    );

COMMENT ON POLICY scope_select_policy ON scopes IS 'Users can see scopes they are members of, public scopes, or all scopes if application admin';

-- Policy: INSERT scopes - Any authenticated user can create a scope
CREATE POLICY scope_insert_policy ON scopes
    FOR INSERT
    WITH CHECK (
        created_by = get_current_user_uuid()  -- Must be creating for yourself
    );

COMMENT ON POLICY scope_insert_policy ON scopes IS 'Any user can create a scope (becomes admin automatically)';

-- Policy: UPDATE scopes - Only scope admins can update
CREATE POLICY scope_update_policy ON scopes
    FOR UPDATE
    USING (
        is_application_admin()      -- Application admins can update any scope
        OR is_scope_admin(id)       -- Scope admins can update their scope
    );

COMMENT ON POLICY scope_update_policy ON scopes IS 'Only scope admins can update scope details';

-- Policy: DELETE scopes - Only application admins can delete
CREATE POLICY scope_delete_policy ON scopes
    FOR DELETE
    USING (
        is_application_admin()      -- Only application admins can delete scopes
    );

COMMENT ON POLICY scope_delete_policy ON scopes IS 'Only application administrators can delete scopes';

-- =============================================================================
-- SCOPE MEMBERSHIP RLS POLICIES
-- =============================================================================

-- Policy: SELECT memberships - Users can see memberships for their scopes
CREATE POLICY membership_select_policy ON scope_memberships
    FOR SELECT
    USING (
        is_application_admin()           -- App admins see all memberships
        OR is_scope_member(scope_id)     -- Scope members see scope memberships
        OR user_id = get_current_user_uuid()  -- Users see their own memberships
    );

COMMENT ON POLICY membership_select_policy ON scope_memberships IS 'Users can see memberships for scopes they belong to, or their own memberships';

-- Policy: INSERT memberships - Only scope admins can invite
CREATE POLICY membership_insert_policy ON scope_memberships
    FOR INSERT
    WITH CHECK (
        is_application_admin()      -- Application admins can add anyone
        OR is_scope_admin(scope_id) -- Scope admins can invite to their scope
    );

COMMENT ON POLICY membership_insert_policy ON scope_memberships IS 'Only scope admins can invite members';

-- Policy: UPDATE memberships - Scope admins and users (for accepting invitations)
CREATE POLICY membership_update_policy ON scope_memberships
    FOR UPDATE
    USING (
        is_application_admin()                    -- Application admins can update any membership
        OR is_scope_admin(scope_id)               -- Scope admins can update memberships
        OR user_id = get_current_user_uuid()      -- Users can update their own (accept invitations)
    );

COMMENT ON POLICY membership_update_policy ON scope_memberships IS 'Scope admins can change roles, users can accept invitations';

-- Policy: DELETE memberships - Only scope admins
CREATE POLICY membership_delete_policy ON scope_memberships
    FOR DELETE
    USING (
        is_application_admin()      -- Application admins can remove anyone
        OR is_scope_admin(scope_id) -- Scope admins can remove members
    );

COMMENT ON POLICY membership_delete_policy ON scope_memberships IS 'Only scope admins can remove members';

-- =============================================================================
-- GENE SCOPE ASSIGNMENTS RLS POLICIES
-- =============================================================================

-- Policy: SELECT gene assignments - Users can see assignments for their scopes
CREATE POLICY gene_assignment_select_policy ON gene_scope_assignments
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
    );

COMMENT ON POLICY gene_assignment_select_policy ON gene_scope_assignments IS 'Users can see gene assignments for scopes they belong to';

-- Policy: INSERT gene assignments - Only scope curators and admins
CREATE POLICY gene_assignment_insert_policy ON gene_scope_assignments
    FOR INSERT
    WITH CHECK (
        is_application_admin()
        OR can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY gene_assignment_insert_policy ON gene_scope_assignments IS 'Only curators and admins can assign genes to scopes';

-- Policy: UPDATE gene assignments - Only scope curators and admins
CREATE POLICY gene_assignment_update_policy ON gene_scope_assignments
    FOR UPDATE
    USING (
        is_application_admin()
        OR can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY gene_assignment_update_policy ON gene_scope_assignments IS 'Only curators and admins can update gene assignments';

-- Policy: DELETE gene assignments - Only scope admins
CREATE POLICY gene_assignment_delete_policy ON gene_scope_assignments
    FOR DELETE
    USING (
        is_application_admin()
        OR is_scope_admin(scope_id)
    );

COMMENT ON POLICY gene_assignment_delete_policy ON gene_scope_assignments IS 'Only scope admins can delete gene assignments';

-- =============================================================================
-- CURATION RLS POLICIES (Precurations)
-- =============================================================================

-- Policy: SELECT precurations - Members can see precurations for their scopes
CREATE POLICY precuration_select_policy ON precurations_new
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = precurations_new.scope_id AND s.is_public = true
        )
    );

COMMENT ON POLICY precuration_select_policy ON precurations_new IS 'Users can see precurations for their scopes or public scopes';

-- Policy: INSERT precurations - Only curators and admins
CREATE POLICY precuration_insert_policy ON precurations_new
    FOR INSERT
    WITH CHECK (
        can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY precuration_insert_policy ON precurations_new IS 'Only curators and admins can create precurations';

-- Policy: UPDATE precurations - Creators, curators, and admins
CREATE POLICY precuration_update_policy ON precurations_new
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY precuration_update_policy ON precurations_new IS 'Creators and curators can update precurations';

-- =============================================================================
-- CURATION RLS POLICIES (Curations)
-- =============================================================================

-- Policy: SELECT curations - Members can see curations for their scopes
CREATE POLICY curation_select_policy ON curations_new
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = curations_new.scope_id AND s.is_public = true
        )
    );

COMMENT ON POLICY curation_select_policy ON curations_new IS 'Users can see curations for their scopes or public scopes';

-- Policy: INSERT curations - Only curators and admins
CREATE POLICY curation_insert_policy ON curations_new
    FOR INSERT
    WITH CHECK (
        can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY curation_insert_policy ON curations_new IS 'Only curators and admins can create curations';

-- Policy: UPDATE curations - Creators, curators, and admins
CREATE POLICY curation_update_policy ON curations_new
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY curation_update_policy ON curations_new IS 'Creators and curators can update curations';

-- =============================================================================
-- REVIEW RLS POLICIES
-- =============================================================================

-- Policy: SELECT reviews - Members can see reviews for their scopes
CREATE POLICY review_select_policy ON reviews
    FOR SELECT
    USING (
        is_application_admin()
        OR EXISTS (
            SELECT 1 FROM curations_new c
            WHERE c.id = reviews.curation_id
            AND is_scope_member(c.scope_id)
        )
    );

COMMENT ON POLICY review_select_policy ON reviews IS 'Users can see reviews for curations in their scopes';

-- Policy: INSERT reviews - Only reviewers and admins
CREATE POLICY review_insert_policy ON reviews
    FOR INSERT
    WITH CHECK (
        is_application_admin()
        OR EXISTS (
            SELECT 1 FROM curations_new c
            WHERE c.id = curation_id
            AND can_review_in_scope(c.scope_id)
        )
    );

COMMENT ON POLICY review_insert_policy ON reviews IS 'Only reviewers and admins can create reviews';

-- Policy: UPDATE reviews - Creators and admins
CREATE POLICY review_update_policy ON reviews
    FOR UPDATE
    USING (
        is_application_admin()
        OR reviewer_id = get_current_user_uuid()
    );

COMMENT ON POLICY review_update_policy ON reviews IS 'Reviewers can update their own reviews';

-- =============================================================================
-- Verification Query
-- =============================================================================
-- Run this to verify all policies were created:
--
-- SELECT
--   schemaname,
--   tablename,
--   policyname,
--   cmd,
--   qual IS NOT NULL as has_using,
--   with_check IS NOT NULL as has_with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
--   AND tablename IN ('scopes', 'scope_memberships', 'gene_scope_assignments',
--                     'precurations_new', 'curations_new', 'reviews')
-- ORDER BY tablename, policyname;
-- =============================================================================
