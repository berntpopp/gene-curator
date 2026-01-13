-- Migration 019: Fix ClinGen Curation Schema - Complete Experimental Evidence
-- Per ClinGen SOP v11, Experimental Evidence has specific subcategories:
-- Function: Biochemical Function, Protein Interaction, Expression (each 0.5-2 pts, max 2 total)
-- Functional Alteration: Patient cells, Non-patient cells (max 2 pts total)
-- Models: Non-human model organism, Cell culture model (max 4 pts total)
-- Rescue: Human, Non-human organism, Cell culture, Patient cells (max 4 pts total)
-- Total experimental evidence max: 6 points
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- Update ClinGen_SOP_v11 Curation Schema - Experimental Evidence
-- Fix the experimental evidence structure per SOP v11 specifications
-- ============================================================================

UPDATE curation_schemas
SET
    field_definitions = jsonb_set(
        field_definitions,
        '{experimental_evidence}',
        '{
            "type": "object",
            "description": "Experimental evidence supporting gene-disease mechanism (max 6 points total)",
            "properties": {
                "function": {
                    "type": "object",
                    "description": "Function evidence category (max 2 points combined from all subcategories)",
                    "properties": {
                        "biochemical_function": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Gene product performs a biochemical function consistent with established knowledge of the disease mechanism",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "gene_function_description": {"type": "string", "required": true, "min_length": 20},
                                "disease_mechanism_relevance": {"type": "string", "required": true, "min_length": 20},
                                "points": {"type": "number", "required": true, "min": 0.5, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 2}
                        },
                        "protein_interaction": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Gene product interacts with proteins previously implicated in the disease mechanism",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "interacting_protein": {"type": "string", "required": true},
                                "interaction_method": {"type": "string", "required": true},
                                "disease_relevance": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 0.5, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 2}
                        },
                        "expression": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Gene is expressed in relevant tissues for the disease phenotype",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "tissue_organ": {"type": "string", "required": true},
                                "expression_method": {"type": "string", "required": true},
                                "disease_tissue_relevance": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 0.5, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 2}
                        }
                    },
                    "scoring": {"max_total_points": 2}
                },
                "functional_alteration": {
                    "type": "object",
                    "description": "Functional alteration evidence (max 2 points combined)",
                    "properties": {
                        "patient_cells": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Patient cells with variant show functional alteration consistent with disease mechanism",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "cell_type": {"type": "string", "required": true},
                                "variant_tested": {"type": "string", "required": true},
                                "functional_effect": {"type": "string", "required": true},
                                "assay_method": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 1, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2}
                        },
                        "non_patient_cells": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Non-patient cells with engineered variant show functional alteration",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "cell_line": {"type": "string", "required": true},
                                "variant_engineered": {"type": "string", "required": true},
                                "functional_effect": {"type": "string", "required": true},
                                "assay_method": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 0.5, "max": 1, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 1}
                        }
                    },
                    "scoring": {"max_total_points": 2}
                },
                "models": {
                    "type": "object",
                    "description": "Model systems evidence (max 4 points combined)",
                    "properties": {
                        "non_human_model_organism": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Non-human model organism (mouse, zebrafish, etc.) with gene knockout/knockin recapitulates disease phenotype",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "organism": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "mouse", "label": "Mouse"},
                                        {"value": "rat", "label": "Rat"},
                                        {"value": "zebrafish", "label": "Zebrafish"},
                                        {"value": "drosophila", "label": "Drosophila"},
                                        {"value": "c_elegans", "label": "C. elegans"},
                                        {"value": "xenopus", "label": "Xenopus"},
                                        {"value": "other", "label": "Other"}
                                    ]
                                },
                                "model_type": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "knockout", "label": "Knockout"},
                                        {"value": "knockin", "label": "Knockin"},
                                        {"value": "transgenic", "label": "Transgenic"},
                                        {"value": "morpholino", "label": "Morpholino"},
                                        {"value": "crispr", "label": "CRISPR-edited"},
                                        {"value": "other", "label": "Other"}
                                    ]
                                },
                                "phenotype_observed": {"type": "string", "required": true, "min_length": 20},
                                "human_phenotype_match": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 2, "max": 4, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 2, "max_per_item": 4}
                        },
                        "cell_culture_model": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Cell culture model (iPSC, organoid, etc.) demonstrates disease-relevant phenotype",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "cell_type": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "ipsc", "label": "iPSC-derived"},
                                        {"value": "organoid", "label": "Organoid"},
                                        {"value": "primary", "label": "Primary cells"},
                                        {"value": "cell_line", "label": "Cell line"},
                                        {"value": "other", "label": "Other"}
                                    ]
                                },
                                "modification": {"type": "string", "required": true},
                                "phenotype_observed": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 1, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2}
                        }
                    },
                    "scoring": {"max_total_points": 4}
                },
                "rescue": {
                    "type": "object",
                    "description": "Rescue evidence demonstrating causality (max 4 points combined)",
                    "properties": {
                        "human": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues disease phenotype in human context",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "rescue_extent": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 2, "max": 4, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 2, "max_per_item": 4}
                        },
                        "non_human_model_organism": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues phenotype in animal model",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "organism": {"type": "string", "required": true},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 2, "max": 4, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 2, "max_per_item": 4}
                        },
                        "cell_culture": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues phenotype in cell culture",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "cell_type": {"type": "string", "required": true},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 1, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2}
                        },
                        "patient_cells": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues phenotype in patient-derived cells",
                            "item_schema": {
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "cell_type": {"type": "string", "required": true},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "points": {"type": "number", "required": true, "min": 1, "max": 2, "step": 0.5},
                                "rationale": {"type": "string", "required": true}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2}
                        }
                    },
                    "scoring": {"max_total_points": 4}
                }
            },
            "scoring": {"max_total_points": 6}
        }'::jsonb
    ),
    -- Also update scoring_configuration to reflect the correct subcategories
    scoring_configuration = jsonb_set(
        scoring_configuration,
        '{evidence_categories,1}',
        '{
            "name": "experimental_evidence",
            "max_score": 6,
            "subcategories": [
                {
                    "name": "function",
                    "max_score": 2,
                    "subcategories": [
                        {"name": "biochemical_function", "max_score": 2},
                        {"name": "protein_interaction", "max_score": 2},
                        {"name": "expression", "max_score": 2}
                    ]
                },
                {
                    "name": "functional_alteration",
                    "max_score": 2,
                    "subcategories": [
                        {"name": "patient_cells", "max_score": 2},
                        {"name": "non_patient_cells", "max_score": 1}
                    ]
                },
                {
                    "name": "models",
                    "max_score": 4,
                    "subcategories": [
                        {"name": "non_human_model_organism", "max_score": 4},
                        {"name": "cell_culture_model", "max_score": 2}
                    ]
                },
                {
                    "name": "rescue",
                    "max_score": 4,
                    "subcategories": [
                        {"name": "human", "max_score": 4},
                        {"name": "non_human_model_organism", "max_score": 4},
                        {"name": "cell_culture", "max_score": 2},
                        {"name": "patient_cells", "max_score": 2}
                    ]
                }
            ]
        }'::jsonb
    ),
    description = 'ClinGen Standard Operating Procedure v11 for Gene-Disease Validity Curation. Complete experimental evidence structure with Function (biochemical, protein interaction, expression), Functional Alteration (patient/non-patient cells), Models (organism/cell culture), and Rescue categories.',
    updated_at = NOW()
WHERE name = 'ClinGen_SOP_v11'
  AND version = '1.0.0'
  AND schema_type = 'curation';

-- ============================================================================
-- Update UI Configuration to reflect new experimental evidence structure
-- ============================================================================

UPDATE curation_schemas
SET
    ui_configuration = jsonb_set(
        ui_configuration,
        '{layout,sections}',
        '[
            {
                "name": "Entity Definition",
                "collapsible": false,
                "fields": ["entity_definition"],
                "help_text": "Define the gene-disease relationship being curated (inherited from approved precuration)"
            },
            {
                "name": "Genetic Evidence",
                "collapsible": true,
                "collapsed": false,
                "fields": ["genetic_evidence"],
                "help_text": "Evidence supporting genetic association per ClinGen SOP v11 (max 12 points)"
            },
            {
                "name": "Experimental Evidence - Function",
                "collapsible": true,
                "collapsed": false,
                "fields": ["experimental_evidence.function"],
                "help_text": "Biochemical function, protein interaction, and expression evidence (max 2 points combined)"
            },
            {
                "name": "Experimental Evidence - Functional Alteration",
                "collapsible": true,
                "collapsed": true,
                "fields": ["experimental_evidence.functional_alteration"],
                "help_text": "Functional alteration in patient cells and non-patient cells (max 2 points combined)"
            },
            {
                "name": "Experimental Evidence - Models",
                "collapsible": true,
                "collapsed": true,
                "fields": ["experimental_evidence.models"],
                "help_text": "Non-human model organisms and cell culture models (max 4 points combined)"
            },
            {
                "name": "Experimental Evidence - Rescue",
                "collapsible": true,
                "collapsed": true,
                "fields": ["experimental_evidence.rescue"],
                "help_text": "Rescue experiments demonstrating causality (max 4 points combined)"
            },
            {
                "name": "Contradictory Evidence",
                "collapsible": true,
                "collapsed": true,
                "fields": ["contradictory_evidence"],
                "help_text": "Evidence that contradicts the gene-disease association"
            }
        ]'::jsonb
    ),
    updated_at = NOW()
WHERE name = 'ClinGen_SOP_v11'
  AND version = '1.0.0'
  AND schema_type = 'curation';

RAISE NOTICE '✅ Updated ClinGen_SOP_v11 curation schema with complete experimental evidence structure';

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    schema_check RECORD;
    has_function_alteration BOOLEAN;
    has_expression BOOLEAN;
BEGIN
    SELECT
        field_definitions->'experimental_evidence'->'properties' as exp_props,
        field_definitions->'experimental_evidence'->'properties'->'function'->'properties' as func_props
    INTO schema_check
    FROM curation_schemas
    WHERE name = 'ClinGen_SOP_v11' AND version = '1.0.0' AND schema_type = 'curation';

    -- Check functional_alteration exists
    has_function_alteration := schema_check.exp_props ? 'functional_alteration';

    -- Check expression exists within function
    has_expression := schema_check.func_props ? 'expression';

    IF NOT has_function_alteration THEN
        RAISE EXCEPTION '❌ functional_alteration category missing from experimental evidence';
    END IF;

    IF NOT has_expression THEN
        RAISE EXCEPTION '❌ expression subcategory missing from function evidence';
    END IF;

    RAISE NOTICE '✅ Verified: functional_alteration category present';
    RAISE NOTICE '✅ Verified: expression subcategory present in function';
    RAISE NOTICE '✅ Experimental evidence structure now matches ClinGen SOP v11';
END $$;

COMMIT;
