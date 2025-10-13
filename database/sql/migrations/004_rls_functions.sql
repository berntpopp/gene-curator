-- =============================================================================
-- Migration 004: Secure RLS Helper Functions
-- =============================================================================
-- Description: Create secure, optimized helper functions for Row Level Security policies
-- Author: Claude Code (Automated Migration)
-- Date: 2025-10-13
-- Dependencies: 001-003 (enums, users, scope_memberships)
-- Security: All functions use STABLE SECURITY DEFINER for safety and performance
-- =============================================================================

-- =============================================================================
-- Function 1: Get Current User UUID (with validation)
-- =============================================================================
-- SECURITY: Safely cast current_setting to UUID, handles invalid input
-- PERFORMANCE: STABLE allows PostgreSQL to cache result across rows
-- =============================================================================

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

-- =============================================================================
-- Function 2: Check if user is application admin
-- =============================================================================
-- SECURITY: Checks application_role column added in migration 002
-- PERFORMANCE: STABLE SQL function (faster than plpgsql)
-- =============================================================================

CREATE OR REPLACE FUNCTION is_application_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM users_new
        WHERE id = get_current_user_uuid()
        AND application_role = 'admin'
        AND is_active = true
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_application_admin() IS 'Check if current user is application administrator (STABLE for caching)';

-- =============================================================================
-- Function 3: Check scope membership (OPTIMIZED for caching)
-- =============================================================================
-- SECURITY: Validates user is active member with accepted invitation
-- PERFORMANCE: STABLE allows query plan caching, prevents N+1 queries
-- =============================================================================

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

-- =============================================================================
-- Function 4: Check scope admin role
-- =============================================================================
-- SECURITY: Checks for 'admin' role within specific scope
-- PERFORMANCE: STABLE function with composite index support
-- =============================================================================

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

-- =============================================================================
-- Function 5: Get user role in scope
-- =============================================================================
-- SECURITY: Returns user's role or NULL if not a member
-- PERFORMANCE: STABLE with LIMIT 1 for early termination
-- =============================================================================

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

-- =============================================================================
-- Function 6: Check if user can curate in scope
-- =============================================================================
-- SECURITY: Checks if user has curator or admin role
-- PERFORMANCE: Uses get_user_scope_role for consistency
-- =============================================================================

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

-- =============================================================================
-- Function 7: Check if user can review in scope
-- =============================================================================
-- SECURITY: Checks if user has reviewer or admin role
-- PERFORMANCE: Uses get_user_scope_role for consistency
-- =============================================================================

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
-- Verification Query
-- =============================================================================
-- Run these to test functions (replace UUID with valid user_id):
--
-- SET LOCAL app.current_user_id = '550e8400-e29b-41d4-a716-446655440000';
--
-- SELECT
--   get_current_user_uuid() as current_user,
--   is_application_admin() as is_admin;
--
-- To test with a specific scope (replace UUID with valid scope_id):
--
-- SELECT
--   is_scope_member('scope-uuid-here') as is_member,
--   is_scope_admin('scope-uuid-here') as is_admin,
--   get_user_scope_role('scope-uuid-here') as role;
-- =============================================================================
