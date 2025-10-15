-- Migration 014: Seed ClinGen SOP v11 curation schema
-- ClinGen Gene-Disease Validity Standard Operating Procedures (September 2024)
-- Date: 2025-10-14

BEGIN;

-- Insert ClinGen SOP v11 schema
-- Schema ID will be generated, admin user ID will be looked up
INSERT INTO curation_schemas (
    id,
    name,
    version,
    description,
    schema_type,
    institution,
    is_active,
    created_by,
    field_definitions,
    validation_rules,
    scoring_configuration,
    workflow_states,
    ui_configuration,
    schema_hash,
    created_at
)
SELECT
    gen_random_uuid() as id,
    'ClinGen Gene-Disease Validity SOP' as name,
    '11.0' as version,
    'ClinGen Standard Operating Procedures for Gene-Disease Clinical Validity Curation (September 2024)' as description,
    'curation'::schema_type as schema_type,
    'ClinGen' as institution,
    true as is_active,
    u.id as created_by,
    -- Field Definitions
    jsonb_build_object(
        'genetic_evidence', jsonb_build_object(
            'label', 'Genetic Evidence',
            'type', 'array',
            'required', true,
            'items', jsonb_build_object(
                'type', 'object',
                'properties', jsonb_build_object(
                    'evidence_category', jsonb_build_object(
                        'type', 'select',
                        'options', jsonb_build_array('case_level', 'segregation', 'case_control'),
                        'required', true
                    ),
                    'variant_type', jsonb_build_object(
                        'type', 'select',
                        'options', jsonb_build_array('predicted_null', 'missense', 'other_variant_type'),
                        'required', true,
                        'condition', 'evidence_category == ''case_level'''
                    ),
                    'proband_count', jsonb_build_object(
                        'type', 'integer',
                        'min', 0,
                        'required', true,
                        'condition', 'evidence_category == ''case_level'''
                    ),
                    'de_novo', jsonb_build_object(
                        'type', 'boolean',
                        'default', false
                    ),
                    'functional_alteration', jsonb_build_object(
                        'type', 'boolean',
                        'default', false
                    ),
                    'family_count', jsonb_build_object(
                        'type', 'integer',
                        'min', 0,
                        'condition', 'evidence_category == ''segregation'''
                    ),
                    'lod_score', jsonb_build_object(
                        'type', 'number',
                        'min', 0,
                        'condition', 'evidence_category == ''segregation'''
                    ),
                    'inheritance_pattern', jsonb_build_object(
                        'type', 'select',
                        'options', jsonb_build_array('autosomal_dominant', 'autosomal_recessive', 'x_linked'),
                        'required', true
                    ),
                    'pmids', jsonb_build_object(
                        'type', 'array',
                        'items', jsonb_build_object('type', 'string', 'pattern', '^[0-9]+$'),
                        'required', true
                    ),
                    'notes', jsonb_build_object(
                        'type', 'textarea'
                    )
                )
            )
        ),
        'experimental_evidence', jsonb_build_object(
            'label', 'Experimental Evidence',
            'type', 'array',
            'required', false,
            'items', jsonb_build_object(
                'type', 'object',
                'properties', jsonb_build_object(
                    'evidence_category', jsonb_build_object(
                        'type', 'select',
                        'options', jsonb_build_array('expression', 'protein_function', 'models', 'rescue'),
                        'required', true
                    ),
                    'model_system', jsonb_build_object(
                        'type', 'select',
                        'options', jsonb_build_array('patient_cells', 'non_patient_cells', 'animal_model', 'non_human_model'),
                        'required', true
                    ),
                    'functional_effect', jsonb_build_object(
                        'type', 'select',
                        'options', jsonb_build_array('loss_of_function', 'gain_of_function', 'altered_function'),
                        'required', true
                    ),
                    'rescue_observed', jsonb_build_object(
                        'type', 'boolean',
                        'default', false
                    ),
                    'pmids', jsonb_build_object(
                        'type', 'array',
                        'items', jsonb_build_object('type', 'string', 'pattern', '^[0-9]+$'),
                        'required', true
                    ),
                    'notes', jsonb_build_object(
                        'type', 'textarea'
                    )
                )
            )
        )
    ) as field_definitions,
    -- Validation Rules
    jsonb_build_object(
        'genetic_evidence_required', jsonb_build_object(
            'rule', 'len(genetic_evidence) > 0',
            'message', 'At least one genetic evidence item is required'
        ),
        'lod_score_consistency', jsonb_build_object(
            'rule', 'if segregation: lod_score >= 0',
            'message', 'LOD score must be non-negative for segregation evidence'
        ),
        'pmid_format', jsonb_build_object(
            'rule', 'all PMIDs must be numeric strings',
            'validator', 'pubmed'
        )
    ) as validation_rules,
    -- Scoring Configuration
    jsonb_build_object(
        'engine', 'clingen',
        'genetic_evidence_rules', jsonb_build_object(
            'case_level_predicted_null', jsonb_build_object(
                'base_score', 1.5,
                'de_novo_bonus', 0.5,
                'functional_alteration_bonus', 0.4,
                'max_score', 12
            ),
            'case_level_missense', jsonb_build_object(
                'base_score', 0.1,
                'de_novo_bonus', 0.4,
                'functional_alteration_bonus', 0.4,
                'max_score', 2
            ),
            'segregation', jsonb_build_object(
                'lod_scoring', true,
                'max_score', 7,
                'family_limit', 7
            ),
            'case_control', jsonb_build_object(
                'max_score', 6
            )
        ),
        'experimental_evidence_rules', jsonb_build_object(
            'max_total_score', 6,
            'expression', jsonb_build_object('max_score', 2),
            'protein_function', jsonb_build_object('max_score', 2),
            'models', jsonb_build_object('max_score', 4),
            'rescue', jsonb_build_object('max_score', 2)
        ),
        'classification_thresholds', jsonb_build_object(
            'definitive', 12,
            'strong', 7,
            'moderate', 2,
            'limited', 0.1,
            'no_known', 0,
            'disputed', -1,
            'refuted', -2
        )
    ) as scoring_configuration,
    -- Workflow States
    jsonb_build_object(
        'entry', jsonb_build_object('label', 'Entry', 'color', 'grey'),
        'precuration', jsonb_build_object('label', 'Precuration', 'color', 'blue'),
        'curation', jsonb_build_object('label', 'Curation', 'color', 'orange'),
        'review', jsonb_build_object('label', 'Review', 'color', 'purple'),
        'active', jsonb_build_object('label', 'Active', 'color', 'green')
    ) as workflow_states,
    -- UI Configuration
    jsonb_build_object(
        'form_layout', 'tabbed',
        'tabs', jsonb_build_array('Genetic Evidence', 'Experimental Evidence', 'Scoring Summary'),
        'show_score_preview', true,
        'enable_auto_save', true,
        'validation_on_blur', true
    ) as ui_configuration,
    -- Schema hash (simple hash of name + version for now)
    md5('ClinGen Gene-Disease Validity SOP' || '11.0') as schema_hash,
    NOW() as created_at
FROM users u
WHERE u.role = 'admin'
LIMIT 1;

-- Verify insertion
DO $$
DECLARE
    schema_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO schema_count
    FROM curation_schemas
    WHERE name = 'ClinGen Gene-Disease Validity SOP' AND version = '11.0';

    IF schema_count = 1 THEN
        RAISE NOTICE '✅ ClinGen SOP v11 schema created successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to create ClinGen SOP v11 schema';
    END IF;
END $$;

COMMIT;
