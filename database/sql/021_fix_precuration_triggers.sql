-- Migration 021: Fix precuration triggers
-- Fixes trigger functions that were incompatible with precurations table
-- Date: 2025-01-13

BEGIN;

-- ========================================
-- FIX 1: Content Hash Function for Precurations
-- ========================================
-- The generate_content_hash() function references precuration_id which
-- exists on curations but not on precurations table.
-- Create a separate function for precurations.

CREATE OR REPLACE FUNCTION generate_precuration_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.record_hash := encode(
        digest(
            COALESCE(NEW.gene_id::text, '') ||
            COALESCE(NEW.scope_id::text, '') ||
            COALESCE(NEW.precuration_schema_id::text, '') ||
            COALESCE(NEW.evidence_data::text, '') ||
            COALESCE(EXTRACT(epoch FROM NEW.created_at)::text, ''),
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop and recreate the precurations trigger with the new function
DROP TRIGGER IF EXISTS trigger_generate_precuration_hash ON precurations;
CREATE TRIGGER trigger_generate_precuration_hash
    BEFORE INSERT ON precurations
    FOR EACH ROW
    EXECUTE FUNCTION generate_precuration_content_hash();

-- ========================================
-- FIX 2: Audit Trail Function Missing change_type
-- ========================================
-- The log_schema_audit_trail() function doesn't include change_type
-- which is a NOT NULL column added in migration 012.

CREATE OR REPLACE FUNCTION log_schema_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    operation_type TEXT;
    change_type_value TEXT;
    entity_scope_id UUID;
    current_workflow_stage workflow_stage;
    previous_status TEXT;
    new_status TEXT;
    schema_context UUID;
    workflow_pair_context UUID;
BEGIN
    -- Determine operation type and change_type
    IF TG_OP = 'INSERT' THEN
        operation_type := 'CREATE';
        change_type_value := 'record_created';
    ELSIF TG_OP = 'UPDATE' THEN
        operation_type := 'UPDATE';
        -- Determine more specific change type based on what changed
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            change_type_value := 'status_changed';
        ELSIF OLD.evidence_data IS DISTINCT FROM NEW.evidence_data THEN
            change_type_value := 'evidence_updated';
        ELSIF OLD.workflow_stage IS DISTINCT FROM NEW.workflow_stage THEN
            change_type_value := 'workflow_transition';
        ELSE
            change_type_value := 'record_updated';
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        operation_type := 'DELETE';
        change_type_value := 'record_deleted';
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
    ELSIF TG_TABLE_NAME = 'active_curations' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
        current_workflow_stage := 'active';
    END IF;

    -- Insert audit record with change_type
    INSERT INTO audit_log (
        entity_type,
        entity_id,
        scope_id,
        operation,
        change_type,
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
        entity_scope_id,
        operation_type,
        change_type_value,
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

-- The triggers already exist and will use the updated function

COMMIT;
