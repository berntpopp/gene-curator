-- Migration 018: Fix ClinGen Curation Schema - Remove Lumping/Splitting
-- Per ClinGen SOP v11: Lumping/Splitting belongs in PRECURATION only
-- Curation inherits disease entity from approved precuration (read-only)
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- Update ClinGen_SOP_v11 Curation Schema
-- Remove lumping_splitting_rationale from entity_definition
-- Entity definition fields should be populated from precuration (read-only)
-- ============================================================================

UPDATE curation_schemas
SET
    field_definitions = jsonb_set(
        field_definitions,
        '{entity_definition,properties}',
        '{
            "disease_name": {"type": "string", "required": true, "readonly": true, "help_text": "Inherited from precuration"},
            "mondo_id": {"type": "string", "required": true, "readonly": true, "validation": "mondo_id_format", "help_text": "Inherited from precuration"},
            "mode_of_inheritance": {"type": "string", "required": true, "readonly": true, "help_text": "Inherited from precuration"}
        }'::jsonb
    ),
    description = 'ClinGen Gene-Disease Validity SOP version 11 curation schema. Entity definition is inherited from approved precuration.',
    updated_at = NOW()
WHERE name = 'ClinGen_SOP_v11'
  AND version = '1.0.0'
  AND schema_type = 'curation';

RAISE NOTICE '✅ Updated ClinGen_SOP_v11 curation schema - removed lumping_splitting_rationale';

-- ============================================================================
-- Update Workflow Pair Data Mapping
-- Remove lumping_splitting mapping since curation doesn't have that field anymore
-- ============================================================================

UPDATE workflow_pairs
SET
    data_mapping = jsonb_set(
        data_mapping,
        '{precuration_to_curation}',
        '{
            "entity_definition.disease_name": "entity_definition.disease_name",
            "entity_definition.mondo_id": "entity_definition.mondo_id",
            "entity_definition.mode_of_inheritance": "entity_definition.mode_of_inheritance"
        }'::jsonb
    ),
    updated_at = NOW()
WHERE name = 'Standard_ClinGen' AND version = '1.0.0';

RAISE NOTICE '✅ Updated Standard_ClinGen workflow pair data mapping';

-- Also update the ClinGen Gene-Disease Validity workflow pair if it exists
UPDATE workflow_pairs
SET
    data_mapping = jsonb_set(
        data_mapping,
        '{precuration_to_curation}',
        '{
            "mondo_id": "entity_definition.mondo_id",
            "disease_name": "entity_definition.disease_name",
            "mode_of_inheritance": "entity_definition.mode_of_inheritance",
            "disease_phenotypes": "entity_definition.phenotypes"
        }'::jsonb
    ),
    updated_at = NOW()
WHERE name = 'ClinGen Gene-Disease Validity' AND version = 'SOP v11';

RAISE NOTICE '✅ Updated ClinGen Gene-Disease Validity workflow pair data mapping';

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    schema_check RECORD;
BEGIN
    -- Check that lumping_splitting_rationale is removed
    SELECT field_definitions->'entity_definition'->'properties' as props
    INTO schema_check
    FROM curation_schemas
    WHERE name = 'ClinGen_SOP_v11' AND version = '1.0.0' AND schema_type = 'curation';

    IF schema_check.props ? 'lumping_splitting_rationale' THEN
        RAISE EXCEPTION '❌ lumping_splitting_rationale still present in curation schema';
    ELSE
        RAISE NOTICE '✅ Verified: lumping_splitting_rationale removed from curation schema';
    END IF;
END $$;

COMMIT;
