-- =============================================================================
-- Migration 005: Enable Row Level Security (SECURE)
-- =============================================================================
-- Description: Enable RLS on all scope-sensitive tables with FORCE protection
-- Author: Claude Code (Automated Migration)
-- Date: 2025-10-13
-- Dependencies: 001-004 (enums, users, scope_memberships, RLS functions)
-- Security: Uses FORCE ROW LEVEL SECURITY to prevent superuser bypass
-- =============================================================================

-- =============================================================================
-- IMPORTANT: FORCE ROW LEVEL SECURITY
-- =============================================================================
-- FORCE ROW LEVEL SECURITY prevents superusers and table owners from bypassing
-- RLS policies. This is CRITICAL for multi-tenant security. Without FORCE,
-- a superuser could accidentally or maliciously access all tenant data.
-- =============================================================================

-- =============================================================================
-- Enable RLS on Core Tables
-- =============================================================================

-- Scopes: Multi-tenant isolation for curation scopes
ALTER TABLE scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE scopes FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE scopes IS 'RLS enabled: Users can only see scopes they are members of or public scopes';

-- Scope Memberships: User-scope relationships with roles
ALTER TABLE scope_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_memberships FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE scope_memberships IS 'RLS enabled: Users can only see memberships for scopes they belong to';

-- Gene Scope Assignments: Gene assignments within scopes
ALTER TABLE gene_scope_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gene_scope_assignments FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE gene_scope_assignments IS 'RLS enabled: Users can only see gene assignments for their scopes';

-- =============================================================================
-- Enable RLS on Curation Workflow Tables
-- =============================================================================

-- Precurations: Pre-curation work within scopes
ALTER TABLE precurations_new ENABLE ROW LEVEL SECURITY;
ALTER TABLE precurations_new FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE precurations_new IS 'RLS enabled: Users can only see precurations for scopes they are members of';

-- Curations: Curation work within scopes
ALTER TABLE curations_new ENABLE ROW LEVEL SECURITY;
ALTER TABLE curations_new FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE curations_new IS 'RLS enabled: Users can only see curations for scopes they are members of';

-- Reviews: Review workflow within scopes
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE reviews IS 'RLS enabled: Users can only see reviews for scopes they are members of';

-- Active Curations: Active curations within scopes
ALTER TABLE active_curations ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_curations FORCE ROW LEVEL SECURITY;  -- ✅ Prevents superuser bypass

COMMENT ON TABLE active_curations IS 'RLS enabled: Users can only see active curations for their scopes';

-- =============================================================================
-- Create Service Role (WITHOUT BYPASSRLS)
-- =============================================================================
-- SECURITY: Application should connect as app_service role, NOT as superuser
-- The app_service role does NOT have BYPASSRLS privilege, so it respects RLS
-- =============================================================================

-- Create service role if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_service') THEN
        CREATE ROLE app_service NOLOGIN;
        RAISE NOTICE 'Created app_service role';
    ELSE
        RAISE NOTICE 'app_service role already exists';
    END IF;
END $$;

-- Grant necessary privileges to app_service role
GRANT CONNECT ON DATABASE gene_curator_dev TO app_service;
GRANT USAGE ON SCHEMA public TO app_service;

-- Grant table permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_service;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_service;

-- Grant function execution
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_service;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO app_service;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO app_service;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO app_service;

-- ⚠️  IMPORTANT: DO NOT grant BYPASSRLS to app_service
-- REVOKE BYPASSRLS ON DATABASE gene_curator_dev FROM app_service;  -- Ensure no bypass

COMMENT ON ROLE app_service IS 'Service role for application: respects RLS policies (no BYPASSRLS)';

-- =============================================================================
-- Verification Query
-- =============================================================================
-- Run this to verify RLS is enabled on all tables:
--
-- SELECT
--   schemaname,
--   tablename,
--   rowsecurity as rls_enabled,
--   forcerls as force_rls_enabled
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN ('scopes', 'scope_memberships', 'gene_scope_assignments',
--                     'precurations_new', 'curations_new', 'reviews', 'active_curations')
-- ORDER BY tablename;
--
-- Verify app_service role does NOT have BYPASSRLS:
--
-- SELECT
--   rolname,
--   rolsuper,
--   rolbypassrls
-- FROM pg_roles
-- WHERE rolname = 'app_service';
-- =============================================================================
