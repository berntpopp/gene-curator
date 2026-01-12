-- =============================================================================
-- Test User Setup for RLS Testing
-- =============================================================================
-- Description: Creates a test user without BYPASSRLS privilege for proper RLS testing
-- Purpose: Ensures Row-Level Security policies are enforced during test execution
-- Author: Claude Code (Automated Implementation)
-- Date: 2025-10-14
-- =============================================================================

-- Create test user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'test_user') THEN
        CREATE ROLE test_user WITH
            LOGIN
            PASSWORD 'test_password'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOBYPASSRLS;

        RAISE NOTICE 'Created test_user role';
    ELSE
        -- Ensure existing user has correct attributes
        ALTER ROLE test_user WITH
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOBYPASSRLS;

        RAISE NOTICE 'Updated test_user role attributes';
    END IF;
END
$$;

-- Grant database connection
GRANT CONNECT ON DATABASE gene_curator_dev TO test_user;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO test_user;

-- Grant table permissions (ALL current tables)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO test_user;

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO test_user;

-- Grant function execution
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO test_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO test_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO test_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO test_user;

-- Verify test_user setup
SELECT
    rolname,
    rolsuper as is_superuser,
    rolbypassrls as bypasses_rls,
    rolcanlogin as can_login
FROM pg_roles
WHERE rolname = 'test_user';

-- =============================================================================
-- Verification Query
-- =============================================================================
--
-- To verify RLS enforcement with test_user:
--
-- SET ROLE test_user;
-- SELECT * FROM scopes;  -- Should be restricted by RLS
-- RESET ROLE;
--
-- =============================================================================

COMMENT ON ROLE test_user IS 'Non-BYPASSRLS user for RLS testing - ensures policies are properly enforced';
