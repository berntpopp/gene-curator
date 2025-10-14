-- =============================================================================
-- Row Level Security (RLS) Setup
-- =============================================================================
-- Description: RLS functions and policies for scope-based multi-tenancy
-- Source: Consolidated from migrations 004, 005, 006
-- Author: Claude Code (Automated Migration Squashing)
-- Date: 2025-10-14
-- Security: All functions use STABLE SECURITY DEFINER for safety and performance
-- =============================================================================
--
-- CRITICAL DESIGN DECISIONS:
--
-- 1. Function Ownership (BYPASSRLS required):
--    All RLS helper functions MUST be owned by a role with BYPASSRLS privilege
--    (e.g., dev_user). This prevents infinite recursion when policies call
--    functions that query tables with RLS policies. SECURITY DEFINER functions
--    run with owner's privileges, so BYPASSRLS allows them to query without
--    triggering RLS recursion. This is the standard PostgreSQL pattern.
--
-- 2. SELECT Policy Creator Check:
--    The scope SELECT policy includes `created_by = get_current_user_uuid()`
--    because INSERT with RETURNING triggers SELECT policy evaluation. Without
--    the creator check, INSERT...RETURNING fails since membership doesn't exist
--    yet at creation time. This allows users to immediately see scopes they
--    create before the membership record is established.
--
-- 3. Membership INSERT Policy:
--    Allows scope creators to add themselves as initial admin by checking if
--    they're the scope creator. This breaks the chicken-and-egg problem where
--    scope creation requires admin membership, but admin membership requires
--    scope existence. Creator check: (user_id = get_current_user_uuid() AND
--    EXISTS (SELECT 1 FROM scopes WHERE created_by = get_current_user_uuid()))
--
-- =============================================================================

-- =============================================================================
-- PART 1: RLS HELPER FUNCTIONS (from 004_rls_functions.sql)
-- =============================================================================

-- Function to get current user UUID (with validation)
-- SECURITY: Safely cast current_setting to UUID, handles invalid input
-- PERFORMANCE: STABLE allows PostgreSQL to cache result across rows
CREATE OR REPLACE FUNCTION get_current_user_uuid()
RETURNS UUID AS $$
DECLARE
    user_uuid UUID;
BEGIN
    -- Safely cast current_setting to UUID
    -- Returns NULL if setting doesn't exist or is invalid
    user_uuid := CAST(current_setting('app.current_user_id', TRUE) AS UUID);
    RETURN user_uuid;
EXCEPTION
    WHEN OTHERS THEN
        -- Invalid UUID or setting not found
        RAISE WARNING 'Invalid or missing app.current_user_id: %', SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_current_user_uuid() IS 'Safely retrieve current user UUID from session variable (STABLE for caching)';

-- Function to check if user is application admin
-- SECURITY: Checks application_role column
-- PERFORMANCE: STABLE SQL function (faster than plpgsql)
CREATE OR REPLACE FUNCTION is_application_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM users_new
        WHERE id = get_current_user_uuid()
        AND role = 'admin'
        AND is_active = true
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_application_admin() IS 'Check if current user is application administrator (STABLE for caching)';

-- Function to check scope membership (OPTIMIZED for caching)
-- SECURITY: Validates user is active member with accepted invitation
-- PERFORMANCE: STABLE allows query plan caching, prevents N+1 queries
CREATE OR REPLACE FUNCTION is_scope_member(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE scope_id = scope_uuid
        AND user_id = get_current_user_uuid()
        AND is_active = true
        AND accepted_at IS NOT NULL
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_scope_member(UUID) IS 'Check if current user is member of given scope (STABLE for query caching)';

-- Function to check scope admin role
-- SECURITY: Checks for 'admin' role within specific scope
-- PERFORMANCE: STABLE function with composite index support
CREATE OR REPLACE FUNCTION is_scope_admin(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE scope_id = scope_uuid
        AND user_id = get_current_user_uuid()
        AND role = 'admin'
        AND is_active = true
        AND accepted_at IS NOT NULL
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_scope_admin(UUID) IS 'Check if current user is admin of given scope (STABLE for caching)';

-- Function to get user role in scope
-- SECURITY: Returns user's role or NULL if not a member
-- PERFORMANCE: STABLE with LIMIT 1 for early termination
CREATE OR REPLACE FUNCTION get_user_scope_role(scope_uuid UUID)
RETURNS scope_role AS $$
    SELECT role FROM scope_memberships
    WHERE scope_id = scope_uuid
    AND user_id = get_current_user_uuid()
    AND is_active = true
    AND accepted_at IS NOT NULL
    LIMIT 1
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_user_scope_role(UUID) IS 'Get current users role in given scope, NULL if not a member (STABLE for caching)';

-- Function to check if user can curate in scope
-- SECURITY: Checks if user has curator or admin role
-- PERFORMANCE: Uses get_user_scope_role for consistency
CREATE OR REPLACE FUNCTION can_curate_in_scope(scope_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    user_role scope_role;
BEGIN
    user_role := get_user_scope_role(scope_uuid);
    RETURN user_role IN ('admin', 'curator');
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION can_curate_in_scope(UUID) IS 'Check if user can curate (create/edit) in given scope';

-- Function to check if user can review in scope
-- SECURITY: Checks if user has reviewer or admin role
-- PERFORMANCE: Uses get_user_scope_role for consistency
CREATE OR REPLACE FUNCTION can_review_in_scope(scope_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    user_role scope_role;
BEGIN
    user_role := get_user_scope_role(scope_uuid);
    RETURN user_role IN ('admin', 'reviewer');
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION can_review_in_scope(UUID) IS 'Check if user can review in given scope';

-- =============================================================================
-- PART 2: ENABLE RLS (from 005_enable_rls.sql)
-- =============================================================================

-- IMPORTANT: FORCE ROW LEVEL SECURITY
-- FORCE ROW LEVEL SECURITY prevents superusers and table owners from bypassing
-- RLS policies. This is CRITICAL for multi-tenant security. Without FORCE,
-- a superuser could accidentally or maliciously access all tenant data.

-- Enable RLS on Core Tables

-- Scopes: Multi-tenant isolation for curation scopes
ALTER TABLE scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE scopes FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- Scope Memberships: User-scope relationships with roles
ALTER TABLE scope_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_memberships FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- Gene Scope Assignments: Gene assignments within scopes
ALTER TABLE gene_scope_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gene_scope_assignments FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- Enable RLS on Curation Workflow Tables

-- Precurations: Pre-curation work within scopes
ALTER TABLE precurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE precurations FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- Curations: Curation work within scopes
ALTER TABLE curations ENABLE ROW LEVEL SECURITY;
ALTER TABLE curations FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- Reviews: Review workflow within scopes
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- Active Curations: Active curations within scopes
ALTER TABLE active_curations ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_curations FORCE ROW LEVEL SECURITY;  -- Prevents superuser bypass

-- =============================================================================
-- PART 3: RLS POLICIES (from 006_rls_policies.sql)
-- =============================================================================

-- =====================
-- SCOPE POLICIES
-- =====================

-- Policy: SELECT scopes - Users can see scopes they're members of or public scopes
-- IMPORTANT: Must include created_by check for RETURNING clause to work in INSERT statements
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        is_application_admin()              -- App admins see all scopes
        OR is_public = true                  -- Public scopes visible to all authenticated users
        OR is_scope_member(id)               -- Members see their scopes (STABLE function)
        OR created_by = get_current_user_uuid()  -- Creators see their own scopes (required for RETURNING)
    );

COMMENT ON POLICY scope_select_policy ON scopes IS 'Users can see scopes they created, are members of, public scopes, or all if admin. Creator check required for INSERT...RETURNING to work.';

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

-- =====================
-- SCOPE MEMBERSHIP POLICIES
-- =====================

-- Policy: SELECT memberships - Users can see memberships for their scopes
CREATE POLICY membership_select_policy ON scope_memberships
    FOR SELECT
    USING (
        is_application_admin()           -- App admins see all memberships
        OR is_scope_member(scope_id)     -- Scope members see scope memberships
        OR user_id = get_current_user_uuid()  -- Users see their own memberships
    );

COMMENT ON POLICY membership_select_policy ON scope_memberships IS 'Users can see memberships for scopes they belong to, or their own memberships';

-- Policy: INSERT memberships - Scope admins can invite, creators can add themselves
CREATE POLICY membership_insert_policy ON scope_memberships
    FOR INSERT
    WITH CHECK (
        is_application_admin()      -- Application admins can add anyone
        OR is_scope_admin(scope_id) -- Scope admins can invite to their scope
        OR (user_id = get_current_user_uuid() AND EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = scope_id
            AND s.created_by = get_current_user_uuid()
        ))  -- Scope creators can add themselves as initial admin
    );

COMMENT ON POLICY membership_insert_policy ON scope_memberships IS 'Scope admins can invite members, scope creators can add themselves as initial admin';

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

-- =====================
-- GENE ASSIGNMENT POLICIES
-- =====================

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

-- =====================
-- PRECURATION POLICIES
-- =====================

-- Policy: SELECT precurations - Members can see precurations for their scopes
CREATE POLICY precuration_select_policy ON precurations
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = precurations.scope_id AND s.is_public = true
        )
    );

COMMENT ON POLICY precuration_select_policy ON precurations IS 'Users can see precurations for their scopes or public scopes';

-- Policy: INSERT precurations - Only curators and admins
CREATE POLICY precuration_insert_policy ON precurations
    FOR INSERT
    WITH CHECK (
        can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY precuration_insert_policy ON precurations IS 'Only curators and admins can create precurations';

-- Policy: UPDATE precurations - Creators, curators, and admins
CREATE POLICY precuration_update_policy ON precurations
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY precuration_update_policy ON precurations IS 'Creators and curators can update precurations';

-- =====================
-- CURATION POLICIES
-- =====================

-- Policy: SELECT curations - Members can see curations for their scopes
CREATE POLICY curation_select_policy ON curations
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = curations.scope_id AND s.is_public = true
        )
    );

COMMENT ON POLICY curation_select_policy ON curations IS 'Users can see curations for their scopes or public scopes';

-- Policy: INSERT curations - Only curators and admins
CREATE POLICY curation_insert_policy ON curations
    FOR INSERT
    WITH CHECK (
        can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY curation_insert_policy ON curations IS 'Only curators and admins can create curations';

-- Policy: UPDATE curations - Creators, curators, and admins
CREATE POLICY curation_update_policy ON curations
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR can_curate_in_scope(scope_id)
    );

COMMENT ON POLICY curation_update_policy ON curations IS 'Creators and curators can update curations';

-- =====================
-- REVIEW POLICIES
-- =====================

-- Policy: SELECT reviews - Members can see reviews for their scopes
CREATE POLICY review_select_policy ON reviews
    FOR SELECT
    USING (
        is_application_admin()
        OR EXISTS (
            SELECT 1 FROM curations c
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
            SELECT 1 FROM curations c
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
-- Verification Queries
-- =============================================================================
--
-- Verify RLS helper functions exist:
--
-- SELECT proname, prosrc
-- FROM pg_proc
-- WHERE proname IN (
--     'get_current_user_uuid',
--     'is_application_admin',
--     'is_scope_member',
--     'is_scope_admin',
--     'can_curate_in_scope',
--     'can_review_in_scope'
-- )
-- ORDER BY proname;
--
-- Verify RLS is enabled on all tables:
--
-- SELECT
--   schemaname,
--   tablename,
--   rowsecurity as rls_enabled,
--   forcerls as force_rls_enabled
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN ('scopes', 'scope_memberships', 'gene_scope_assignments',
--                     'precurations', 'curations', 'reviews', 'active_curations')
-- ORDER BY tablename;
--
-- Verify RLS policies:
--
-- SELECT
--   schemaname,
--   tablename,
--   policyname,
--   cmd as operation,
--   qual IS NOT NULL as has_using,
--   with_check IS NOT NULL as has_with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- AND tablename IN ('scopes', 'scope_memberships', 'gene_scope_assignments',
--                    'precurations', 'curations', 'reviews')
-- ORDER BY tablename, policyname;
-- =============================================================================
