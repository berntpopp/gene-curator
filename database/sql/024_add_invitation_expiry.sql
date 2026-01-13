-- ============================================================
-- Migration 024: Add invitation expiry support
-- ============================================================
--
-- Purpose: Add expires_at field to scope_memberships for GitHub-style
-- invitation workflow. Invitations will expire after a configurable
-- period (default 7 days).
--
-- Changes:
-- 1. Add expires_at column to scope_memberships
-- 2. Add index for efficient pending invitation queries
-- 3. Set default expiry for existing pending invitations
--
-- Author: Claude Code (Automated Implementation)
-- Created: 2025-01-13
-- ============================================================

-- Add expires_at column to scope_memberships
ALTER TABLE scope_memberships
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Set default for new rows (7 days from creation)
-- Note: We don't set server_default here as we want the application
-- to control the expiry dynamically

-- Update existing pending invitations to expire in 7 days from now
-- (gives existing pending invitations a grace period)
UPDATE scope_memberships
SET expires_at = NOW() + INTERVAL '7 days'
WHERE accepted_at IS NULL
  AND expires_at IS NULL
  AND is_active = TRUE;

-- Create index for efficient pending invitation queries
-- This helps when fetching user's pending invitations
CREATE INDEX IF NOT EXISTS idx_scope_memberships_user_pending_expires
ON scope_memberships(user_id, expires_at)
WHERE accepted_at IS NULL AND is_active = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN scope_memberships.expires_at IS 'Invitation expiration timestamp. NULL for accepted memberships, set during invitation creation.';

-- ============================================================
-- Verification query (for manual testing)
-- ============================================================
-- SELECT
--     id,
--     user_id,
--     scope_id,
--     invited_at,
--     accepted_at,
--     expires_at,
--     CASE
--         WHEN accepted_at IS NOT NULL THEN 'accepted'
--         WHEN expires_at < NOW() THEN 'expired'
--         ELSE 'pending'
--     END as status
-- FROM scope_memberships
-- WHERE is_active = TRUE;
