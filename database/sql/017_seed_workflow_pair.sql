-- Migration 017: Seed ClinGen SOP v11 Workflow Pair
-- Links precuration and curation schemas with data mapping
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- ClinGen Workflow Pair Definition
-- Uses ON CONFLICT DO UPDATE for idempotent seeding
-- ============================================================================

DO $$
DECLARE
    workflow_pair_id UUID := 'f1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c'::uuid;
    precuration_schema_id UUID := 'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b'::uuid;
    curation_schema_id UUID;
    admin_id UUID;
BEGIN
    -- Get admin user ID
    SELECT id INTO admin_id FROM users WHERE role = 'admin' LIMIT 1;

    IF admin_id IS NULL THEN
        RAISE EXCEPTION 'No admin user found. Please ensure an admin user exists before running this migration.';
    END IF;

    -- Get the ClinGen curation schema ID
    SELECT id INTO curation_schema_id
    FROM curation_schemas
    WHERE name = 'ClinGen Gene-Disease Validity SOP'
    AND schema_type = 'curation'
    AND is_active = true
    LIMIT 1;

    IF curation_schema_id IS NULL THEN
        RAISE NOTICE 'ClinGen curation schema not found. Workflow pair will be created without curation schema link.';
    END IF;

    -- Verify precuration schema exists
    IF NOT EXISTS (SELECT 1 FROM curation_schemas WHERE id = precuration_schema_id) THEN
        RAISE EXCEPTION 'Precuration schema % not found. Please run migration 016 first.', precuration_schema_id;
    END IF;

    -- Insert or update the workflow pair
    INSERT INTO workflow_pairs (
        id,
        name,
        version,
        precuration_schema_id,
        curation_schema_id,
        data_mapping,
        workflow_config,
        description,
        is_active,
        created_by,
        created_at
    ) VALUES (
        workflow_pair_id,
        'ClinGen Gene-Disease Validity',
        'SOP v11',
        precuration_schema_id,
        curation_schema_id,
        -- Data Mapping: How precuration data maps to curation fields
        jsonb_build_object(
            'precuration_to_curation', jsonb_build_object(
                'mondo_id', 'entity_definition.mondo_id',
                'disease_name', 'entity_definition.disease_name',
                'mode_of_inheritance', 'entity_definition.mode_of_inheritance',
                'disease_phenotypes', 'entity_definition.phenotypes',
                'lumping_splitting_decision', 'entity_definition.lumping_splitting.decision',
                'lumping_splitting_rationale', 'entity_definition.lumping_splitting.rationale',
                'affiliation', 'metadata.affiliation'
            )
        ),
        -- Workflow Configuration
        jsonb_build_object(
            'require_precuration', true,
            'require_review_for_precuration', true,
            'min_precuration_reviewers', 1,
            'auto_create_curation_on_approval', true,
            'four_eyes_principle', true,
            'allow_self_review', false
        ),
        'ClinGen Gene-Disease Validity workflow combining precuration and curation per SOP v11',
        true,
        admin_id,
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        version = EXCLUDED.version,
        precuration_schema_id = EXCLUDED.precuration_schema_id,
        curation_schema_id = COALESCE(EXCLUDED.curation_schema_id, workflow_pairs.curation_schema_id),
        data_mapping = EXCLUDED.data_mapping,
        workflow_config = EXCLUDED.workflow_config,
        description = EXCLUDED.description,
        is_active = EXCLUDED.is_active,
        updated_at = NOW();

    RAISE NOTICE '✅ ClinGen Workflow Pair (SOP v11) created/updated with ID: %', workflow_pair_id;
    RAISE NOTICE '   Precuration Schema ID: %', precuration_schema_id;
    RAISE NOTICE '   Curation Schema ID: %', COALESCE(curation_schema_id::text, 'NOT SET');
END $$;

-- Verify insertion
DO $$
DECLARE
    pair_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO pair_count
    FROM workflow_pairs
    WHERE name = 'ClinGen Gene-Disease Validity' AND version = 'SOP v11';

    IF pair_count = 1 THEN
        RAISE NOTICE '✅ ClinGen Workflow Pair verified successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to verify ClinGen Workflow Pair';
    END IF;
END $$;

COMMIT;
