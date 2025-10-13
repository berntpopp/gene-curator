-- =============================================================================
-- Migration 002: Users Table - Add Application Role
-- =============================================================================
-- Description: Add application_role column to users_new table (backward compatible)
-- Author: Claude Code (Automated Migration)
-- Date: 2025-10-13
-- Dependencies: 001_scope_centric_enums.sql
-- =============================================================================

-- Add new columns without breaking existing system
ALTER TABLE users_new
  ADD COLUMN IF NOT EXISTS application_role application_role DEFAULT 'user',
  ADD COLUMN IF NOT EXISTS migration_complete BOOLEAN DEFAULT false;

COMMENT ON COLUMN users_new.application_role IS 'Application-level role (admin or user)';
COMMENT ON COLUMN users_new.migration_complete IS 'Migration flag for tracking scope-centric refactor progress';

-- Migrate existing roles to application_role
-- Map old 5-role system (viewer, curator, reviewer, admin, scope_admin) to new 2-role system
UPDATE users_new SET
  application_role = CASE
    WHEN role IN ('admin', 'scope_admin') THEN 'admin'::application_role
    ELSE 'user'::application_role
  END
WHERE application_role IS NULL;

-- Add NOT NULL constraint after populating
ALTER TABLE users_new ALTER COLUMN application_role SET NOT NULL;

-- Create index for performance (application admins are frequently checked)
CREATE INDEX IF NOT EXISTS idx_users_application_role ON users_new(application_role) WHERE application_role = 'admin';

COMMENT ON INDEX idx_users_application_role IS 'Performance index for application admin checks';

-- =============================================================================
-- Verification Query
-- =============================================================================
-- Run this to verify migration:
--
-- SELECT
--   application_role,
--   COUNT(*) as user_count
-- FROM users_new
-- GROUP BY application_role
-- ORDER BY application_role;
-- =============================================================================
