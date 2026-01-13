-- Migration 016: Seed ClinGen SOP v11 Precuration Schema
-- ClinGen Gene-Disease Validity Precuration per SOP version 11
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- ClinGen Precuration Schema Definition
-- Uses ON CONFLICT DO UPDATE for idempotent seeding
-- ============================================================================

-- First, check if we need to create a deterministic UUID for the schema
-- Using a fixed UUID for the precuration schema to ensure consistent references
DO $$
DECLARE
    precuration_schema_id UUID := 'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b'::uuid;
    admin_id UUID;
BEGIN
    -- Get admin user ID
    SELECT id INTO admin_id FROM users WHERE role = 'admin' LIMIT 1;

    IF admin_id IS NULL THEN
        RAISE EXCEPTION 'No admin user found. Please ensure an admin user exists before running this migration.';
    END IF;

    -- Insert or update the precuration schema
    INSERT INTO curation_schemas (
        id,
        name,
        version,
        schema_type,
        description,
        institution,
        field_definitions,
        validation_rules,
        workflow_states,
        ui_configuration,
        scoring_configuration,
        schema_hash,
        is_active,
        created_by,
        created_at
    ) VALUES (
        precuration_schema_id,
        'ClinGen Precuration',
        'SOP v11',
        'precuration'::schema_type,
        'ClinGen Gene-Disease Validity Precuration Schema per SOP version 11',
        'ClinGen',
        -- Field Definitions (ClinGen SOP v11 Precuration Fields)
        jsonb_build_object(
            'sections', jsonb_build_array(
                jsonb_build_object(
                    'id', 'disease_entity',
                    'label', 'Disease Entity Definition',
                    'description', 'Establish the gene-disease pair to be curated',
                    'fields', jsonb_build_array(
                        jsonb_build_object(
                            'id', 'mondo_id',
                            'label', 'Mondo Disease ID',
                            'type', 'external_reference',
                            'required', true,
                            'external_source', 'mondo',
                            'placeholder', 'MONDO:0000001',
                            'help_text', 'Search for disease using Mondo Disease Ontology'
                        ),
                        jsonb_build_object(
                            'id', 'disease_name',
                            'label', 'Disease Name',
                            'type', 'text',
                            'required', true,
                            'help_text', 'Use dyadic naming: Gene-associated phenotype (e.g., SCN1A-related seizure disorder)'
                        ),
                        jsonb_build_object(
                            'id', 'disease_phenotypes',
                            'label', 'Key Phenotypes',
                            'type', 'array',
                            'item_type', 'external_reference',
                            'external_source', 'hpo',
                            'required', false,
                            'help_text', 'Add relevant HPO terms describing the phenotype'
                        )
                    )
                ),
                jsonb_build_object(
                    'id', 'inheritance',
                    'label', 'Mode of Inheritance',
                    'description', 'Specify the inheritance pattern for this gene-disease pair',
                    'fields', jsonb_build_array(
                        jsonb_build_object(
                            'id', 'mode_of_inheritance',
                            'label', 'Mode of Inheritance',
                            'type', 'select',
                            'required', true,
                            'options', jsonb_build_array(
                                jsonb_build_object('value', 'AD', 'label', 'Autosomal Dominant (HP:0000006)'),
                                jsonb_build_object('value', 'AR', 'label', 'Autosomal Recessive (HP:0000007)'),
                                jsonb_build_object('value', 'XLD', 'label', 'X-linked Dominant (HP:0001417)'),
                                jsonb_build_object('value', 'XLR', 'label', 'X-linked Recessive (HP:0001419)'),
                                jsonb_build_object('value', 'SD', 'label', 'Semidominant (HP:0032113)'),
                                jsonb_build_object('value', 'MT', 'label', 'Mitochondrial (HP:0001427)'),
                                jsonb_build_object('value', 'Other', 'label', 'Other (specify)')
                            )
                        ),
                        jsonb_build_object(
                            'id', 'moi_notes',
                            'label', 'MOI Notes',
                            'type', 'textarea',
                            'required', false,
                            'show_when', jsonb_build_object('mode_of_inheritance', 'Other'),
                            'help_text', 'Provide details for Other inheritance pattern'
                        )
                    )
                ),
                jsonb_build_object(
                    'id', 'lumping_splitting',
                    'label', 'Lumping & Splitting',
                    'description', 'Document any lumping or splitting decisions per ClinGen guidelines',
                    'fields', jsonb_build_array(
                        jsonb_build_object(
                            'id', 'lumping_splitting_applicable',
                            'label', 'Lumping/Splitting Applicable?',
                            'type', 'boolean',
                            'required', true,
                            'default', false,
                            'help_text', 'Does this curation involve combining or separating disease entities?'
                        ),
                        jsonb_build_object(
                            'id', 'lumping_splitting_decision',
                            'label', 'Decision',
                            'type', 'select',
                            'required', true,
                            'show_when', jsonb_build_object('lumping_splitting_applicable', true),
                            'options', jsonb_build_array(
                                jsonb_build_object('value', 'LUMP', 'label', 'Lump - Combine disease entities'),
                                jsonb_build_object('value', 'SPLIT', 'label', 'Split - Separate disease entities')
                            )
                        ),
                        jsonb_build_object(
                            'id', 'lumping_splitting_rationale',
                            'label', 'Rationale',
                            'type', 'textarea',
                            'required', true,
                            'show_when', jsonb_build_object('lumping_splitting_applicable', true),
                            'help_text', 'Explain the rationale for lumping or splitting per ClinGen guidelines'
                        )
                    )
                ),
                jsonb_build_object(
                    'id', 'metadata',
                    'label', 'Precuration Metadata',
                    'fields', jsonb_build_array(
                        jsonb_build_object(
                            'id', 'affiliation',
                            'label', 'Expert Panel / Affiliation',
                            'type', 'text',
                            'required', true,
                            'help_text', 'Your ClinGen Expert Panel or curation group'
                        ),
                        jsonb_build_object(
                            'id', 'curator_notes',
                            'label', 'Curator Notes',
                            'type', 'textarea',
                            'required', false,
                            'help_text', 'Any additional notes for the precuration record'
                        )
                    )
                )
            )
        ),
        -- Validation Rules
        jsonb_build_object(
            'required_fields', jsonb_build_array('mondo_id', 'disease_name', 'mode_of_inheritance', 'affiliation'),
            'conditional_required', jsonb_build_object(
                'lumping_splitting_decision', jsonb_build_object('when', jsonb_build_object('lumping_splitting_applicable', true)),
                'lumping_splitting_rationale', jsonb_build_object('when', jsonb_build_object('lumping_splitting_applicable', true))
            ),
            'custom_validators', jsonb_build_array(
                jsonb_build_object(
                    'type', 'mondo_id_format',
                    'field', 'mondo_id',
                    'pattern', '^MONDO:\d{6,9}$',
                    'comment', 'Mondo IDs have 6-9 digits (e.g., MONDO:0000001 to MONDO:012345678)'
                )
            )
        ),
        -- Workflow States
        jsonb_build_object(
            'entry', jsonb_build_object('allowed_transitions', jsonb_build_array('precuration')),
            'precuration', jsonb_build_object('allowed_transitions', jsonb_build_array('review')),
            'review', jsonb_build_object('allowed_transitions', jsonb_build_array('precuration', 'approved')),
            'approved', jsonb_build_object('allowed_transitions', jsonb_build_array('curation'))
        ),
        -- UI Configuration
        jsonb_build_object(
            'form_layout', 'wizard',
            'sections_collapsible', false,
            'show_progress_bar', true,
            'auto_save_interval_seconds', 30
        ),
        -- Scoring Configuration (NULL for precuration - no scoring at this stage)
        NULL,
        -- Schema hash
        md5('ClinGen Precuration' || 'SOP v11'),
        true,
        admin_id,
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        version = EXCLUDED.version,
        description = EXCLUDED.description,
        field_definitions = EXCLUDED.field_definitions,
        validation_rules = EXCLUDED.validation_rules,
        workflow_states = EXCLUDED.workflow_states,
        ui_configuration = EXCLUDED.ui_configuration,
        is_active = EXCLUDED.is_active,
        updated_at = NOW();

    RAISE NOTICE '✅ ClinGen Precuration schema (SOP v11) created/updated with ID: %', precuration_schema_id;
END $$;

-- Verify insertion
DO $$
DECLARE
    schema_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO schema_count
    FROM curation_schemas
    WHERE name = 'ClinGen Precuration' AND version = 'SOP v11';

    IF schema_count = 1 THEN
        RAISE NOTICE '✅ ClinGen Precuration schema verified successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to verify ClinGen Precuration schema';
    END IF;
END $$;

COMMIT;
