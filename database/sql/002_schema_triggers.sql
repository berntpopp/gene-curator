-- Schema-Agnostic Triggers and Constraints
-- Foreign Keys, Business Logic, and Automation

-- ========================================
-- FOREIGN KEY CONSTRAINTS
-- ========================================

-- Add foreign key constraints after all tables are created
ALTER TABLE scopes ADD CONSTRAINT fk_scopes_created_by 
    FOREIGN KEY (created_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE scopes ADD CONSTRAINT fk_scopes_default_workflow_pair 
    FOREIGN KEY (default_workflow_pair_id) REFERENCES workflow_pairs(id) ON DELETE SET NULL;

ALTER TABLE curation_schemas ADD CONSTRAINT fk_curation_schemas_created_by 
    FOREIGN KEY (created_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE workflow_pairs ADD CONSTRAINT fk_workflow_pairs_created_by 
    FOREIGN KEY (created_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE genes_new ADD CONSTRAINT fk_genes_new_created_by 
    FOREIGN KEY (created_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE genes_new ADD CONSTRAINT fk_genes_new_updated_by 
    FOREIGN KEY (updated_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE gene_scope_assignments ADD CONSTRAINT fk_gene_scope_assignments_gene 
    FOREIGN KEY (gene_id) REFERENCES genes_new(id) ON DELETE CASCADE;

ALTER TABLE gene_scope_assignments ADD CONSTRAINT fk_gene_scope_assignments_curator 
    FOREIGN KEY (assigned_curator_id) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE gene_scope_assignments ADD CONSTRAINT fk_gene_scope_assignments_assigned_by 
    FOREIGN KEY (assigned_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE precurations_new ADD CONSTRAINT fk_precurations_new_gene 
    FOREIGN KEY (gene_id) REFERENCES genes_new(id) ON DELETE CASCADE;

ALTER TABLE precurations_new ADD CONSTRAINT fk_precurations_new_created_by 
    FOREIGN KEY (created_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE precurations_new ADD CONSTRAINT fk_precurations_new_updated_by 
    FOREIGN KEY (updated_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE curations_new ADD CONSTRAINT fk_curations_new_gene 
    FOREIGN KEY (gene_id) REFERENCES genes_new(id) ON DELETE CASCADE;

ALTER TABLE curations_new ADD CONSTRAINT fk_curations_new_precuration 
    FOREIGN KEY (precuration_id) REFERENCES precurations_new(id) ON DELETE SET NULL;

ALTER TABLE curations_new ADD CONSTRAINT fk_curations_new_created_by 
    FOREIGN KEY (created_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE curations_new ADD CONSTRAINT fk_curations_new_updated_by 
    FOREIGN KEY (updated_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE curations_new ADD CONSTRAINT fk_curations_new_submitted_by 
    FOREIGN KEY (submitted_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE curations_new ADD CONSTRAINT fk_curations_new_approved_by 
    FOREIGN KEY (approved_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE reviews ADD CONSTRAINT fk_reviews_curation 
    FOREIGN KEY (curation_id) REFERENCES curations_new(id) ON DELETE CASCADE;

ALTER TABLE reviews ADD CONSTRAINT fk_reviews_reviewer 
    FOREIGN KEY (reviewer_id) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE reviews ADD CONSTRAINT fk_reviews_assigned_by 
    FOREIGN KEY (assigned_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE active_curations ADD CONSTRAINT fk_active_curations_gene 
    FOREIGN KEY (gene_id) REFERENCES genes_new(id) ON DELETE CASCADE;

ALTER TABLE active_curations ADD CONSTRAINT fk_active_curations_curation 
    FOREIGN KEY (curation_id) REFERENCES curations_new(id) ON DELETE CASCADE;

ALTER TABLE active_curations ADD CONSTRAINT fk_active_curations_activated_by 
    FOREIGN KEY (activated_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE active_curations ADD CONSTRAINT fk_active_curations_archived_by 
    FOREIGN KEY (archived_by) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE active_curations ADD CONSTRAINT fk_active_curations_replaced_curation 
    FOREIGN KEY (replaced_curation_id) REFERENCES curations_new(id) ON DELETE SET NULL;

ALTER TABLE audit_log_new ADD CONSTRAINT fk_audit_log_new_user 
    FOREIGN KEY (user_id) REFERENCES users_new(id) ON DELETE SET NULL;

ALTER TABLE schema_selections ADD CONSTRAINT fk_schema_selections_user 
    FOREIGN KEY (user_id) REFERENCES users_new(id) ON DELETE CASCADE;

-- ========================================
-- BUSINESS LOGIC CONSTRAINTS
-- ========================================

-- 4-Eyes Principle: Reviewer must be different from curation creator
-- NOTE: This will be enforced at the application level due to PostgreSQL subquery constraint limitations

-- Reviewer must have access to the scope
-- NOTE: This will be enforced at the application level due to PostgreSQL subquery constraint limitations

-- Curation creator must have scope access
-- NOTE: This will be enforced at the application level due to PostgreSQL subquery constraint limitations

-- Precuration creator must have scope access
-- NOTE: This will be enforced at the application level due to PostgreSQL subquery constraint limitations

-- Active curation must be approved
-- NOTE: This will be enforced at the application level due to PostgreSQL subquery constraint limitations

-- ========================================
-- SCHEMA-AWARE SCORING TRIGGERS
-- ========================================

-- Function to calculate scores using pluggable scoring engines
CREATE OR REPLACE FUNCTION calculate_schema_scores()
RETURNS TRIGGER AS $$
DECLARE
    schema_config JSONB;
    scoring_engine VARCHAR(100);
    scope_context JSONB;
    scoring_result JSONB;
BEGIN
    -- Skip scoring for draft curations
    IF NEW.is_draft = true THEN
        RETURN NEW;
    END IF;
    
    -- Get scope context and scoring configuration
    SELECT 
        cs.scoring_configuration,
        json_build_object(
            'scope_name', s.name,
            'scope_display_name', s.display_name,
            'institution', s.institution,
            'scope_config', s.scope_config
        )
    INTO schema_config, scope_context
    FROM curation_schemas cs
    JOIN workflow_pairs wp ON wp.curation_schema_id = cs.id
    JOIN scopes s ON s.id = NEW.scope_id
    WHERE wp.id = NEW.workflow_pair_id;
    
    -- Extract scoring engine name
    scoring_engine := schema_config->>'engine';
    
    -- For now, call placeholder scoring function
    -- Will be replaced with actual scoring engine registry
    NEW.computed_scores := json_build_object(
        'engine', scoring_engine,
        'calculated_at', NOW(),
        'scope_context', scope_context,
        'raw_scores', json_build_object()
    );
    
    -- Extract computed verdict (will be populated by actual scoring engines)
    NEW.computed_verdict := NEW.computed_scores->>'verdict';
    NEW.computed_summary := NEW.computed_scores->>'summary';
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply scoring trigger to curations
CREATE TRIGGER trigger_calculate_schema_scores
    BEFORE INSERT OR UPDATE ON curations_new
    FOR EACH ROW
    EXECUTE FUNCTION calculate_schema_scores();

-- ========================================
-- RECORD HASH GENERATION
-- ========================================

-- Function to generate content hash for provenance tracking
CREATE OR REPLACE FUNCTION generate_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.record_hash := encode(
        digest(
            COALESCE(NEW.gene_id::text, '') || 
            COALESCE(NEW.scope_id::text, '') ||
            COALESCE(NEW.precuration_id::text, '') ||
            COALESCE(NEW.evidence_data::text, '') ||
            COALESCE(EXTRACT(epoch FROM NEW.created_at)::text, ''),
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply hash generation to curations and precurations
CREATE TRIGGER trigger_generate_curation_hash
    BEFORE INSERT ON curations_new
    FOR EACH ROW
    EXECUTE FUNCTION generate_content_hash();

CREATE TRIGGER trigger_generate_precuration_hash
    BEFORE INSERT ON precurations_new
    FOR EACH ROW
    EXECUTE FUNCTION generate_content_hash();

-- ========================================
-- AUDIT TRAIL AUTOMATION
-- ========================================

-- Function to automatically log changes
CREATE OR REPLACE FUNCTION log_schema_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    operation_type TEXT;
    entity_scope_id UUID;
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
    IF TG_TABLE_NAME = 'curations_new' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
        current_workflow_stage := COALESCE(NEW.workflow_stage, OLD.workflow_stage);
        previous_status := OLD.status::text;
        new_status := NEW.status::text;
        workflow_pair_context := COALESCE(NEW.workflow_pair_id, OLD.workflow_pair_id);
    ELSIF TG_TABLE_NAME = 'precurations_new' THEN
        entity_scope_id := COALESCE(NEW.scope_id, OLD.scope_id);
        current_workflow_stage := COALESCE(NEW.workflow_stage, OLD.workflow_stage);
        previous_status := OLD.status::text;
        new_status := NEW.status::text;
        schema_context := COALESCE(NEW.precuration_schema_id, OLD.precuration_schema_id);
    ELSIF TG_TABLE_NAME = 'reviews' THEN
        -- Get scope from curation
        SELECT c.scope_id INTO entity_scope_id 
        FROM curations_new c 
        WHERE c.id = COALESCE(NEW.curation_id, OLD.curation_id);
        current_workflow_stage := 'review';
    END IF;
    
    -- Insert audit record
    INSERT INTO audit_log_new (
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
        entity_scope_id,
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

-- Apply audit triggers to key tables
CREATE TRIGGER trigger_audit_curations_new
    AFTER INSERT OR UPDATE OR DELETE ON curations_new
    FOR EACH ROW EXECUTE FUNCTION log_schema_audit_trail();

CREATE TRIGGER trigger_audit_precurations_new
    AFTER INSERT OR UPDATE OR DELETE ON precurations_new
    FOR EACH ROW EXECUTE FUNCTION log_schema_audit_trail();

CREATE TRIGGER trigger_audit_reviews
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW EXECUTE FUNCTION log_schema_audit_trail();

CREATE TRIGGER trigger_audit_active_curations
    AFTER INSERT OR UPDATE OR DELETE ON active_curations
    FOR EACH ROW EXECUTE FUNCTION log_schema_audit_trail();

-- ========================================
-- AUTO-SAVE FUNCTIONALITY
-- ========================================

-- Function to update auto-save timestamp
CREATE OR REPLACE FUNCTION update_auto_save_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update auto_saved_at for draft updates
    IF NEW.is_draft = true AND OLD.evidence_data IS DISTINCT FROM NEW.evidence_data THEN
        NEW.auto_saved_at := NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply auto-save triggers
CREATE TRIGGER trigger_auto_save_curations
    BEFORE UPDATE ON curations_new
    FOR EACH ROW
    EXECUTE FUNCTION update_auto_save_timestamp();

CREATE TRIGGER trigger_auto_save_precurations
    BEFORE UPDATE ON precurations_new
    FOR EACH ROW
    EXECUTE FUNCTION update_auto_save_timestamp();

-- ========================================
-- WORKFLOW STATE MANAGEMENT
-- ========================================

-- Function to manage workflow state transitions
CREATE OR REPLACE FUNCTION manage_workflow_transitions()
RETURNS TRIGGER AS $$
BEGIN
    -- Handle status changes
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        CASE NEW.status
            WHEN 'submitted' THEN
                NEW.submitted_at := NOW();
                NEW.submitted_by := NEW.updated_by;
                NEW.is_draft := false;
                NEW.workflow_stage := 'review';
            WHEN 'approved' THEN
                NEW.approved_at := NOW();
                NEW.approved_by := NEW.updated_by;
                NEW.workflow_stage := 'active';
            WHEN 'rejected' THEN
                NEW.workflow_stage := 'curation';
                NEW.is_draft := true;
            ELSE
                -- Keep current workflow stage
        END CASE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply workflow management trigger
CREATE TRIGGER trigger_manage_workflow_transitions
    BEFORE UPDATE ON curations_new
    FOR EACH ROW
    EXECUTE FUNCTION manage_workflow_transitions();

-- ========================================
-- SCHEMA VALIDATION FUNCTIONS
-- ========================================

-- Function to validate schema structure
CREATE OR REPLACE FUNCTION validate_schema_structure(schema_definition JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check required top-level keys
    IF NOT (schema_definition ? 'field_definitions' AND 
            schema_definition ? 'workflow_states' AND 
            schema_definition ? 'ui_configuration') THEN
        RETURN false;
    END IF;
    
    -- Check field_definitions structure
    IF NOT jsonb_typeof(schema_definition->'field_definitions') = 'object' THEN
        RETURN false;
    END IF;
    
    -- Check workflow_states structure
    IF NOT jsonb_typeof(schema_definition->'workflow_states') = 'object' THEN
        RETURN false;
    END IF;
    
    -- Check ui_configuration structure
    IF NOT jsonb_typeof(schema_definition->'ui_configuration') = 'object' THEN
        RETURN false;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Function to generate schema hash
CREATE OR REPLACE FUNCTION generate_schema_hash()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate schema structure
    IF NOT validate_schema_structure(
        jsonb_build_object(
            'field_definitions', NEW.field_definitions,
            'validation_rules', NEW.validation_rules,
            'scoring_configuration', NEW.scoring_configuration,
            'workflow_states', NEW.workflow_states,
            'ui_configuration', NEW.ui_configuration
        )
    ) THEN
        RAISE EXCEPTION 'Invalid schema structure';
    END IF;
    
    -- Generate schema hash
    NEW.schema_hash := encode(
        digest(
            NEW.field_definitions::text ||
            NEW.validation_rules::text ||
            COALESCE(NEW.scoring_configuration::text, '') ||
            NEW.workflow_states::text ||
            NEW.ui_configuration::text,
            'sha256'
        ),
        'hex'
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply schema validation trigger
CREATE TRIGGER trigger_validate_schema
    BEFORE INSERT OR UPDATE ON curation_schemas
    FOR EACH ROW
    EXECUTE FUNCTION generate_schema_hash();