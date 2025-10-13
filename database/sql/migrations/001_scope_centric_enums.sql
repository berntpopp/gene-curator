-- =============================================================================
-- Migration 001: Scope-Centric Architecture - New Enums
-- =============================================================================
-- Description: Create new enum types for scope-centric multi-tenant architecture
-- Author: Claude Code (Automated Migration)
-- Date: 2025-10-13
-- Dependencies: None
-- =============================================================================

-- Create new application-level role enum (simplified from 5 roles to 2)
CREATE TYPE application_role AS ENUM ('admin', 'user');

COMMENT ON TYPE application_role IS 'Application-level roles: admin (full access) and user (scope-based access)';

-- Create new scope-level role enum (detailed permissions within scopes)
CREATE TYPE scope_role AS ENUM ('admin', 'curator', 'reviewer', 'viewer');

COMMENT ON TYPE scope_role IS 'Scope-level roles: admin (manage scope), curator (create/edit), reviewer (review only), viewer (read-only)';

-- =============================================================================
-- Verification Query
-- =============================================================================
-- Run this to verify enums were created:
--
-- SELECT typname, enumlabel FROM pg_enum
-- JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
-- WHERE typname IN ('application_role', 'scope_role')
-- ORDER BY typname, enumsortorder;
-- =============================================================================
