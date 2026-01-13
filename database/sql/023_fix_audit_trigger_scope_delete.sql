-- Migration: 023_fix_audit_trigger_scope_delete.sql
-- Description: Fix audit trigger to handle scope cascade delete
--
-- Problem: When a scope is deleted, CASCADE deletes related curations/precurations.
-- The audit trigger fires for each deletion and tries to INSERT with the scope_id,
-- but the scope is being deleted in the same transaction, causing FK violation.
--
-- Solution: Check if scope exists before inserting, use NULL if scope is being deleted.
--
-- Author: Claude Code
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- Updated audit trail function that handles scope deletion
-- ============================================================================
CREATE OR REPLACE FUNCTION log_schema_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    operation_type TEXT;
    entity_scope_id UUID;
    validated_scope_id UUID;
    current_workflow_stage workflow_stage;
    previous_status TEXT;
    new_status TEXT;
    schema_context UUID;
    workflow_pair_context UUID;
BEGIN
    -- Determine operation type
    IF TG_OP = 'INSERT' THEN
        operation_type := 'CREATE';
    ELSIF TG_OP = 'UPDATE' THEN
        operation_type := 'UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        operation_type := 'DELETE';
    END IF;

    -- Extract context based on table
    IF TG_TABLE_NAME = 'curations' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
        current_workflow_stage := COALESCE(NEW.workflow_stage, OLD.workflow_stage);
        previous_status := OLD.status::text;
        new_status := NEW.status::text;
        workflow_pair_context := COALESCE(NEW.workflow_pair_id, OLD.workflow_pair_id);
    ELSIF TG_TABLE_NAME = 'precurations' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
        current_workflow_stage := COALESCE(NEW.workflow_stage, OLD.workflow_stage);
        previous_status := OLD.status::text;
        new_status := NEW.status::text;
        schema_context := COALESCE(NEW.precuration_schema_id, OLD.precuration_schema_id);
    ELSIF TG_TABLE_NAME = 'reviews' THEN
        -- Get scope from curation
        SELECT c.scope_id INTO entity_scope_id
        FROM curations c
        WHERE c.id = COALESCE(NEW.curation_id, OLD.curation_id);
        current_workflow_stage := 'review';
    END IF;

    -- Validate scope_id still exists (handles CASCADE delete scenario)
    -- If scope is being deleted in the same transaction, set to NULL
    IF entity_scope_id IS NOT NULL THEN
        SELECT id INTO validated_scope_id
        FROM scopes
        WHERE id = entity_scope_id;

        -- If scope not found, it's being deleted - set to NULL
        IF validated_scope_id IS NULL THEN
            entity_scope_id := NULL;
        END IF;
    END IF;

    -- Insert audit record
    INSERT INTO audit_log (
        entity_type,
        entity_id,
        scope_id,
        operation,
        changes,
        user_id,
        workflow_stage,
        previous_status,
        new_status,
        schema_id,
        workflow_pair_id
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        entity_scope_id,  -- Will be NULL if scope is being deleted
        operation_type,
        CASE
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)
            ELSE to_jsonb(NEW)
        END,
        COALESCE(NEW.updated_by, OLD.updated_by, NEW.created_by, OLD.created_by),
        current_workflow_stage,
        previous_status,
        new_status,
        schema_context,
        workflow_pair_context
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- Verification: The function now checks if the scope exists before inserting.
-- If the scope is being deleted (CASCADE), the scope_id will be set to NULL
-- instead of causing a foreign key violation.
