-- Migration: 022_fix_scope_cascade_delete.sql
-- Description: Fix foreign key constraints and column constraints for proper scope cascade delete
--
-- This migration updates:
-- 1. Foreign key constraints on tables that reference scopes
-- 2. Makes audit_log.change_type nullable to match SQLAlchemy model
--
-- Author: Claude Code
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- Fix audit_log foreign key constraint
-- ============================================================================
-- The audit_log table tracks changes across the system. When a scope is deleted,
-- we want to preserve the audit records but set the scope_id to NULL.

ALTER TABLE audit_log
    DROP CONSTRAINT IF EXISTS audit_log_scope_id_fkey;

ALTER TABLE audit_log
    ADD CONSTRAINT audit_log_scope_id_fkey
    FOREIGN KEY (scope_id) REFERENCES scopes(id) ON DELETE SET NULL;

COMMENT ON CONSTRAINT audit_log_scope_id_fkey ON audit_log IS
    'SET NULL on scope delete to preserve audit trail';

-- ============================================================================
-- Fix audit_log.change_type constraint
-- ============================================================================
-- The SQLAlchemy model defines change_type as Optional[str], but the database
-- has a NOT NULL constraint. This causes issues with the audit trigger which
-- doesn't populate this field. Make it nullable to match the model.

ALTER TABLE audit_log
    ALTER COLUMN change_type DROP NOT NULL;

-- ============================================================================
-- Fix schema_selections foreign key constraint
-- ============================================================================
-- Schema selections are scope-specific preferences. When a scope is deleted,
-- the associated schema selections should also be removed.

ALTER TABLE schema_selections
    DROP CONSTRAINT IF EXISTS schema_selections_scope_id_fkey;

ALTER TABLE schema_selections
    ADD CONSTRAINT schema_selections_scope_id_fkey
    FOREIGN KEY (scope_id) REFERENCES scopes(id) ON DELETE CASCADE;

COMMENT ON CONSTRAINT schema_selections_scope_id_fkey ON schema_selections IS
    'CASCADE delete schema selections when scope is deleted';

COMMIT;

-- Verification query (optional, for manual testing)
-- SELECT
--     tc.table_name,
--     tc.constraint_name,
--     rc.delete_rule
-- FROM information_schema.table_constraints tc
-- JOIN information_schema.referential_constraints rc
--     ON tc.constraint_name = rc.constraint_name
-- WHERE tc.constraint_type = 'FOREIGN KEY'
--     AND tc.constraint_name LIKE '%scope%';
