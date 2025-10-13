-- =============================================================================
-- Migration 003: Scope Memberships Table (Core Multi-Tenancy)
-- =============================================================================
-- Description: Create scope_memberships table for user-scope relationships with roles
-- Author: Claude Code (Automated Migration)
-- Date: 2025-10-13
-- Dependencies: 001_scope_centric_enums.sql, 002_users_migration_prep.sql
-- =============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core multi-tenancy table: user roles within scopes
CREATE TABLE scope_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Scope and user relationship
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,

    -- Scope-specific role (NOT application role)
    role scope_role NOT NULL,

    -- Invitation tracking
    invited_by UUID REFERENCES users_new(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,  -- NULL = pending invitation

    -- Team membership (for future team-based collaboration)
    team_id UUID,  -- Will reference teams(id) when teams table is created

    -- Metadata
    notes TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL,

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(scope_id, user_id)
);

COMMENT ON TABLE scope_memberships IS 'Core multi-tenancy table: user roles within scopes';
COMMENT ON COLUMN scope_memberships.role IS 'Scope-specific role: admin, curator, reviewer, or viewer';
COMMENT ON COLUMN scope_memberships.accepted_at IS 'NULL indicates pending invitation, non-NULL indicates accepted membership';
COMMENT ON COLUMN scope_memberships.is_active IS 'Allow soft deletion of memberships';
COMMENT ON COLUMN scope_memberships.team_id IS 'Future: team-based collaboration within scopes';

-- =============================================================================
-- Performance Indexes
-- =============================================================================

-- Basic indexes for foreign key lookups
CREATE INDEX idx_scope_memberships_scope ON scope_memberships(scope_id);
CREATE INDEX idx_scope_memberships_user ON scope_memberships(user_id);
CREATE INDEX idx_scope_memberships_role ON scope_memberships(role);

-- Partial indexes for common queries
CREATE INDEX idx_scope_memberships_active ON scope_memberships(is_active)
WHERE is_active = true;

CREATE INDEX idx_scope_memberships_pending ON scope_memberships(accepted_at)
WHERE accepted_at IS NULL;

-- CRITICAL: Composite index for permission checks (prevents N+1 queries)
-- This index is used by RLS policies and permission check functions
CREATE INDEX idx_scope_memberships_user_scope_active
ON scope_memberships(user_id, scope_id, role)
WHERE is_active = true AND accepted_at IS NOT NULL;

COMMENT ON INDEX idx_scope_memberships_user_scope_active IS 'CRITICAL: Composite index for RLS permission checks (prevents N+1 queries)';

-- =============================================================================
-- Trigger for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_scope_memberships_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER scope_memberships_updated_at
    BEFORE UPDATE ON scope_memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_scope_memberships_updated_at();

-- =============================================================================
-- Verification Query
-- =============================================================================
-- Run this to verify table creation and indexes:
--
-- SELECT
--   tablename,
--   indexname,
--   indexdef
-- FROM pg_indexes
-- WHERE tablename = 'scope_memberships'
-- ORDER BY indexname;
-- =============================================================================
