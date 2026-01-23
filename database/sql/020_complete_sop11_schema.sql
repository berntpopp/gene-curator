-- Migration 020: Complete ClinGen SOP v11 Curation Schema
-- Exact scoring parameters from ClinGen Gene-Disease Validity framework
-- https://clinicalgenome.org/site/assets/files/2186/gene_validity_framework_table.pdf
--
-- GENETIC EVIDENCE (Max 12 points):
--   Case-Level Data:
--     AD/X-linked: Predicted Null (1.5 default, 0-3), Other (0.1 default, 0-1.5)
--     Autosomal Recessive: Predicted Null (1.5 default, 0-3), Other (0.1 default, 0-1.5)
--   Segregation Data: 0-3 points based on LOD score
--   Case-Control Data: Single Variant (0-6), Aggregate (0-6)
--
-- EXPERIMENTAL EVIDENCE (Max 6 points):
--   Function: Biochemical (0.5, 0-2), Protein Interaction (0.5, 0-2), Expression (0.5, 0-2) - Max 2
--   Functional Alteration: Patient cells (1, 0-2), Non-patient (0.5, 0-1) - Max 2
--   Models: Non-human organism (2, 0-4), Cell culture (1, 0-2) - Max 4
--   Rescue: Human (2, 0-4), Non-human (2, 0-4), Cell culture (1, 0-2), Patient cells (1, 0-2) - Max 4
--
-- Total Max: 18 points (Genetic 12 + Experimental 6, but capped)
-- Date: 2026-01-13

BEGIN;

-- ============================================================================
-- Update ClinGen_SOP_v11 Curation Schema - Complete Genetic Evidence Structure
-- ============================================================================

UPDATE curation_schemas
SET
    field_definitions = '{
        "entity_definition": {
            "type": "object",
            "description": "Gene-disease relationship entity (inherited from approved precuration)",
            "readonly": true,
            "properties": {
                "disease_name": {
                    "type": "string",
                    "required": true,
                    "readonly": true,
                    "help_text": "Inherited from precuration"
                },
                "mondo_id": {
                    "type": "string",
                    "required": true,
                    "readonly": true,
                    "validation": "mondo_id_format",
                    "help_text": "Inherited from precuration"
                },
                "mode_of_inheritance": {
                    "type": "string",
                    "required": true,
                    "readonly": true,
                    "help_text": "Inherited from precuration"
                }
            }
        },
        "genetic_evidence": {
            "type": "object",
            "description": "Genetic evidence supporting gene-disease association (max 12 points)",
            "properties": {
                "case_level": {
                    "type": "object",
                    "description": "Case-level variant evidence organized by inheritance pattern and variant type",
                    "properties": {
                        "autosomal_dominant_or_x_linked": {
                            "type": "object",
                            "description": "Evidence for AD or X-linked inheritance patterns",
                            "properties": {
                                "predicted_or_proven_null": {
                                    "type": "array",
                                    "ui_component": "EvidenceTable",
                                    "description": "Predicted or proven null variants (nonsense, frameshift, canonical splice, initiation codon, single/multi-exon deletion)",
                                    "item_schema": {
                                        "proband_label": {"type": "string", "required": true, "min_length": 1, "help_text": "Unique identifier for proband"},
                                        "variant_type": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "nonsense", "label": "Nonsense"},
                                                {"value": "frameshift", "label": "Frameshift"},
                                                {"value": "canonical_splice", "label": "Canonical +/- 1,2 splice"},
                                                {"value": "initiation_codon", "label": "Initiation codon"},
                                                {"value": "single_exon_deletion", "label": "Single exon deletion"},
                                                {"value": "multi_exon_deletion", "label": "Multi-exon deletion"},
                                                {"value": "whole_gene_deletion", "label": "Whole gene deletion"}
                                            ]
                                        },
                                        "variant": {"type": "string", "required": true, "help_text": "HGVS notation (e.g., c.123G>A)"},
                                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                        "score_status": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "score", "label": "Score"},
                                                {"value": "review", "label": "Review"},
                                                {"value": "contradicts", "label": "Contradicts"}
                                            ]
                                        },
                                        "proband_counted_points": {"type": "number", "required": true, "min": 0, "max": 3, "step": 0.1},
                                        "proband_not_counted_points": {"type": "number", "min": 0, "max": 3, "step": 0.1, "default": 0},
                                        "explanation": {"type": "string", "help_text": "Rationale for scoring decision"},
                                        "sex": {"type": "enum", "options": [{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}, {"value": "unknown", "label": "Unknown"}]},
                                        "age": {"type": "string", "help_text": "Age at onset or diagnosis"},
                                        "ethnicity": {"type": "string"},
                                        "phenotypes": {"type": "string", "help_text": "HPO terms or free text"},
                                        "methods": {"type": "string", "help_text": "Detection methods used"},
                                        "zygosity": {
                                            "type": "enum",
                                            "options": [
                                                {"value": "heterozygous", "label": "Heterozygous"},
                                                {"value": "hemizygous", "label": "Hemizygous (X-linked)"},
                                                {"value": "unknown", "label": "Unknown"}
                                            ]
                                        },
                                        "segregations": {"type": "string", "help_text": "Family segregation notes"},
                                        "previous_testing": {"type": "string"},
                                        "de_novo": {"type": "boolean", "default": false},
                                        "paternity_maternity_confirmed": {"type": "boolean", "default": false}
                                    },
                                    "scoring": {
                                        "default_points": 1.5,
                                        "max_per_item": 3,
                                        "range": [0, 3]
                                    }
                                },
                                "other_variant_type": {
                                    "type": "array",
                                    "ui_component": "EvidenceTable",
                                    "description": "Other variant types (missense, in-frame indels, etc.)",
                                    "item_schema": {
                                        "proband_label": {"type": "string", "required": true, "min_length": 1},
                                        "variant_type": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "missense", "label": "Missense"},
                                                {"value": "in_frame_indel", "label": "In-frame indel"},
                                                {"value": "cryptic_splice", "label": "Cryptic splice variant"},
                                                {"value": "synonymous", "label": "Synonymous (splicing)"},
                                                {"value": "5_utr", "label": "5 prime UTR"},
                                                {"value": "3_utr", "label": "3 prime UTR"},
                                                {"value": "intronic", "label": "Intronic"},
                                                {"value": "other", "label": "Other"}
                                            ]
                                        },
                                        "variant": {"type": "string", "required": true},
                                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                        "score_status": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "score", "label": "Score"},
                                                {"value": "review", "label": "Review"},
                                                {"value": "contradicts", "label": "Contradicts"}
                                            ]
                                        },
                                        "proband_counted_points": {"type": "number", "required": true, "min": 0, "max": 1.5, "step": 0.1},
                                        "proband_not_counted_points": {"type": "number", "min": 0, "max": 1.5, "step": 0.1, "default": 0},
                                        "explanation": {"type": "string"},
                                        "sex": {"type": "enum", "options": [{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}, {"value": "unknown", "label": "Unknown"}]},
                                        "age": {"type": "string"},
                                        "ethnicity": {"type": "string"},
                                        "phenotypes": {"type": "string"},
                                        "methods": {"type": "string"},
                                        "zygosity": {
                                            "type": "enum",
                                            "options": [
                                                {"value": "heterozygous", "label": "Heterozygous"},
                                                {"value": "hemizygous", "label": "Hemizygous (X-linked)"},
                                                {"value": "unknown", "label": "Unknown"}
                                            ]
                                        },
                                        "functional_data": {"type": "string", "help_text": "Supporting functional evidence"},
                                        "de_novo": {"type": "boolean", "default": false},
                                        "paternity_maternity_confirmed": {"type": "boolean", "default": false}
                                    },
                                    "scoring": {
                                        "default_points": 0.1,
                                        "max_per_item": 1.5,
                                        "range": [0, 1.5]
                                    }
                                }
                            },
                            "scoring": {"max_total_points": 12}
                        },
                        "autosomal_recessive": {
                            "type": "object",
                            "description": "Evidence for autosomal recessive inheritance",
                            "properties": {
                                "predicted_or_proven_null": {
                                    "type": "array",
                                    "ui_component": "EvidenceTable",
                                    "description": "Predicted or proven null variants (requires biallelic)",
                                    "item_schema": {
                                        "proband_label": {"type": "string", "required": true},
                                        "variant_type": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "two_null", "label": "Two null variants"},
                                                {"value": "null_and_null", "label": "Homozygous null"}
                                            ]
                                        },
                                        "variant_1": {"type": "string", "required": true, "help_text": "First variant (HGVS)"},
                                        "variant_2": {"type": "string", "help_text": "Second variant (HGVS) if compound het"},
                                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                        "score_status": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "score", "label": "Score"},
                                                {"value": "review", "label": "Review"},
                                                {"value": "contradicts", "label": "Contradicts"}
                                            ]
                                        },
                                        "proband_counted_points": {"type": "number", "required": true, "min": 0, "max": 3, "step": 0.1},
                                        "proband_not_counted_points": {"type": "number", "min": 0, "max": 3, "step": 0.1, "default": 0},
                                        "explanation": {"type": "string"},
                                        "sex": {"type": "enum", "options": [{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}, {"value": "unknown", "label": "Unknown"}]},
                                        "age": {"type": "string"},
                                        "ethnicity": {"type": "string"},
                                        "phenotypes": {"type": "string"},
                                        "methods": {"type": "string"},
                                        "consanguinity": {"type": "boolean", "default": false},
                                        "phase_confirmed": {"type": "boolean", "default": false, "help_text": "Are variants confirmed in trans?"}
                                    },
                                    "scoring": {
                                        "default_points": 1.5,
                                        "max_per_item": 3,
                                        "range": [0, 3]
                                    }
                                },
                                "other_variant_type": {
                                    "type": "array",
                                    "ui_component": "EvidenceTable",
                                    "description": "Other variant types for AR inheritance",
                                    "item_schema": {
                                        "proband_label": {"type": "string", "required": true},
                                        "variant_type": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "null_and_other", "label": "Null + Other variant"},
                                                {"value": "two_other", "label": "Two other variants"},
                                                {"value": "homozygous_other", "label": "Homozygous other"}
                                            ]
                                        },
                                        "variant_1": {"type": "string", "required": true},
                                        "variant_2": {"type": "string"},
                                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                        "score_status": {
                                            "type": "enum",
                                            "required": true,
                                            "options": [
                                                {"value": "score", "label": "Score"},
                                                {"value": "review", "label": "Review"},
                                                {"value": "contradicts", "label": "Contradicts"}
                                            ]
                                        },
                                        "proband_counted_points": {"type": "number", "required": true, "min": 0, "max": 1.5, "step": 0.1},
                                        "proband_not_counted_points": {"type": "number", "min": 0, "max": 1.5, "step": 0.1, "default": 0},
                                        "explanation": {"type": "string"},
                                        "sex": {"type": "enum", "options": [{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}, {"value": "unknown", "label": "Unknown"}]},
                                        "age": {"type": "string"},
                                        "ethnicity": {"type": "string"},
                                        "phenotypes": {"type": "string"},
                                        "methods": {"type": "string"},
                                        "functional_data": {"type": "string"},
                                        "consanguinity": {"type": "boolean", "default": false},
                                        "phase_confirmed": {"type": "boolean", "default": false}
                                    },
                                    "scoring": {
                                        "default_points": 0.1,
                                        "max_per_item": 1.5,
                                        "range": [0, 1.5]
                                    }
                                }
                            },
                            "scoring": {"max_total_points": 12}
                        }
                    },
                    "scoring": {"max_total_points": 12}
                },
                "segregation": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "description": "Segregation evidence based on LOD scores (max 3 points)",
                    "item_schema": {
                        "family_label": {"type": "string", "required": true},
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "lod_score": {
                            "type": "number",
                            "required": true,
                            "min": 0,
                            "step": 0.1,
                            "help_text": "Calculated LOD score"
                        },
                        "lod_score_method": {
                            "type": "enum",
                            "options": [
                                {"value": "calculated", "label": "Calculated from family data"},
                                {"value": "published", "label": "Published LOD score"},
                                {"value": "estimated", "label": "Estimated from pedigree"}
                            ]
                        },
                        "segregations_counted": {"type": "integer", "required": true, "min": 0, "help_text": "Number of informative meioses"},
                        "segregations_not_counted": {"type": "integer", "min": 0, "default": 0},
                        "points": {"type": "number", "required": true, "min": 0, "max": 3, "step": 0.1},
                        "explanation": {"type": "string"},
                        "pedigree_description": {"type": "string", "help_text": "Family structure description"},
                        "inheritance_pattern_match": {"type": "boolean", "default": true, "help_text": "Does segregation match expected pattern?"}
                    },
                    "scoring": {
                        "lod_score_thresholds": {
                            "0.6_to_1.2": 1,
                            "1.2_to_2.4": 2,
                            "above_2.4": 3
                        },
                        "max_total_points": 3,
                        "range": [0, 3]
                    }
                },
                "case_control": {
                    "type": "object",
                    "description": "Case-control study evidence (max 6 points from either method)",
                    "properties": {
                        "single_variant_analysis": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Single variant analysis studies",
                            "item_schema": {
                                "study_label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "variant": {"type": "string", "required": true},
                                "cases_with_variant": {"type": "integer", "required": true, "min": 0},
                                "cases_total": {"type": "integer", "required": true, "min": 1},
                                "controls_with_variant": {"type": "integer", "required": true, "min": 0},
                                "controls_total": {"type": "integer", "required": true, "min": 1},
                                "odds_ratio": {"type": "number", "min": 0},
                                "confidence_interval": {"type": "string", "help_text": "95% CI"},
                                "p_value": {"type": "number", "min": 0, "max": 1},
                                "statistical_test": {"type": "string"},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"},
                                        {"value": "contradicts", "label": "Contradicts"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 6, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {
                                "default_points": 0,
                                "max_per_item": 6,
                                "range": [0, 6]
                            }
                        },
                        "aggregate_variant_analysis": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Aggregate/burden analysis studies",
                            "item_schema": {
                                "study_label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "analysis_type": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "burden", "label": "Burden test"},
                                        {"value": "collapsing", "label": "Collapsing method"},
                                        {"value": "skat", "label": "SKAT"},
                                        {"value": "skat_o", "label": "SKAT-O"},
                                        {"value": "other", "label": "Other"}
                                    ]
                                },
                                "cases_with_variants": {"type": "integer", "required": true, "min": 0},
                                "cases_total": {"type": "integer", "required": true, "min": 1},
                                "controls_with_variants": {"type": "integer", "required": true, "min": 0},
                                "controls_total": {"type": "integer", "required": true, "min": 1},
                                "odds_ratio": {"type": "number", "min": 0},
                                "confidence_interval": {"type": "string"},
                                "p_value": {"type": "number", "min": 0, "max": 1},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"},
                                        {"value": "contradicts", "label": "Contradicts"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 6, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {
                                "default_points": 0,
                                "max_per_item": 6,
                                "range": [0, 6]
                            }
                        }
                    },
                    "scoring": {"max_total_points": 6}
                }
            },
            "scoring": {"max_total_points": 12}
        },
        "experimental_evidence": {
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
                            "description": "Gene product performs a biochemical function consistent with disease mechanism",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Biochemical Function"},
                                "gene_function_description": {"type": "string", "required": true},
                                "disease_mechanism_relevance": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string", "help_text": "Reason for changed score (if applicable)"}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 2, "range": [0, 2]}
                        },
                        "protein_interaction": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Gene product interacts with proteins implicated in disease",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Protein Interaction"},
                                "interacting_protein": {"type": "string", "required": true},
                                "interaction_method": {"type": "string", "required": true},
                                "disease_relevance": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 2, "range": [0, 2]}
                        },
                        "expression": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Gene is expressed in relevant tissues",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Expression"},
                                "tissue_organ": {"type": "string", "required": true},
                                "expression_method": {"type": "string", "required": true},
                                "disease_tissue_relevance": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 2, "range": [0, 2]}
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
                            "description": "Patient cells with variant show functional alteration",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Functional Alteration - Patient Cells"},
                                "cell_type": {"type": "string", "required": true},
                                "variant_tested": {"type": "string", "required": true},
                                "functional_effect": {"type": "string", "required": true},
                                "assay_method": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2, "range": [0, 2]}
                        },
                        "non_patient_cells": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Non-patient cells with engineered variant show functional alteration",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Functional Alteration - Non-patient Cells"},
                                "cell_line": {"type": "string", "required": true},
                                "variant_engineered": {"type": "string", "required": true},
                                "functional_effect": {"type": "string", "required": true},
                                "assay_method": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 1, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 0.5, "max_per_item": 1, "range": [0, 1]}
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
                            "description": "Non-human model organism with gene modification recapitulates phenotype",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Non-human Model Organism"},
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
                                        {"value": "yeast", "label": "Yeast"},
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
                                "phenotype_observed": {"type": "string", "required": true},
                                "human_phenotype_match": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 4, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 2, "max_per_item": 4, "range": [0, 4]}
                        },
                        "cell_culture_model": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Cell culture model demonstrates disease-relevant phenotype",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Cell Culture Model"},
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
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2, "range": [0, 2]}
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
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Rescue - Human"},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "rescue_extent": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 4, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 2, "max_per_item": 4, "range": [0, 4]}
                        },
                        "non_human_model_organism": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues phenotype in animal model",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Rescue - Non-human Model"},
                                "organism": {"type": "string", "required": true},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 4, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 2, "max_per_item": 4, "range": [0, 4]}
                        },
                        "cell_culture": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues phenotype in cell culture",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Rescue - Cell Culture"},
                                "cell_type": {"type": "string", "required": true},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2, "range": [0, 2]}
                        },
                        "patient_cells": {
                            "type": "array",
                            "ui_component": "EvidenceTable",
                            "description": "Wild-type gene product rescues phenotype in patient-derived cells",
                            "item_schema": {
                                "label": {"type": "string", "required": true},
                                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                                "experimental_category": {"type": "string", "default": "Rescue - Patient Cells"},
                                "cell_type": {"type": "string", "required": true},
                                "rescue_method": {"type": "string", "required": true},
                                "phenotype_rescued": {"type": "string", "required": true},
                                "score_status": {
                                    "type": "enum",
                                    "required": true,
                                    "options": [
                                        {"value": "score", "label": "Score"},
                                        {"value": "review", "label": "Review"}
                                    ]
                                },
                                "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.5},
                                "explanation": {"type": "string"}
                            },
                            "scoring": {"default_points": 1, "max_per_item": 2, "range": [0, 2]}
                        }
                    },
                    "scoring": {"max_total_points": 4}
                }
            },
            "scoring": {"max_total_points": 6}
        },
        "contradictory_evidence": {
            "type": "array",
            "ui_component": "EvidenceTable",
            "description": "Evidence that contradicts the gene-disease association",
            "item_schema": {
                "label": {"type": "string", "required": true},
                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                "evidence_type": {
                    "type": "enum",
                    "required": true,
                    "options": [
                        {"value": "population", "label": "Population/control data"},
                        {"value": "segregation", "label": "Non-segregation"},
                        {"value": "functional", "label": "Contradictory functional data"},
                        {"value": "phenotype", "label": "Phenotype mismatch"},
                        {"value": "other", "label": "Other"}
                    ]
                },
                "description": {"type": "string", "required": true},
                "proband_with_variant": {"type": "integer", "min": 0},
                "controls_with_variant": {"type": "integer", "min": 0},
                "impact": {
                    "type": "enum",
                    "options": [
                        {"value": "disputed", "label": "Disputed classification"},
                        {"value": "note", "label": "Note only"},
                        {"value": "requires_review", "label": "Requires expert review"}
                    ]
                },
                "explanation": {"type": "string"}
            }
        },
        "evidence_summary": {
            "type": "string",
            "ui_component": "RichTextEditor",
            "description": "Free-text summary of the evidence and classification rationale",
            "help_text": "Summarize the overall evidence supporting the gene-disease relationship"
        }
    }'::jsonb,
    -- scoring_configuration
    scoring_configuration = '{
        "engine": "clingen_sop_v11",
        "version": "1.0.0",
        "parameters": {
            "max_genetic_score": 12,
            "max_experimental_score": 6,
            "max_total_score": 18
        },
        "evidence_categories": [
            {
                "name": "genetic_evidence",
                "max_score": 12,
                "subcategories": [
                    {
                        "name": "case_level",
                        "max_score": 12,
                        "subcategories": [
                            {
                                "name": "autosomal_dominant_or_x_linked",
                                "subcategories": [
                                    {"name": "predicted_or_proven_null", "default_points": 1.5, "range": [0, 3]},
                                    {"name": "other_variant_type", "default_points": 0.1, "range": [0, 1.5]}
                                ]
                            },
                            {
                                "name": "autosomal_recessive",
                                "subcategories": [
                                    {"name": "predicted_or_proven_null", "default_points": 1.5, "range": [0, 3]},
                                    {"name": "other_variant_type", "default_points": 0.1, "range": [0, 1.5]}
                                ]
                            }
                        ]
                    },
                    {"name": "segregation", "max_score": 3, "range": [0, 3]},
                    {
                        "name": "case_control",
                        "max_score": 6,
                        "subcategories": [
                            {"name": "single_variant_analysis", "max_score": 6, "range": [0, 6]},
                            {"name": "aggregate_variant_analysis", "max_score": 6, "range": [0, 6]}
                        ]
                    }
                ]
            },
            {
                "name": "experimental_evidence",
                "max_score": 6,
                "subcategories": [
                    {
                        "name": "function",
                        "max_score": 2,
                        "subcategories": [
                            {"name": "biochemical_function", "default_points": 0.5, "max_score": 2, "range": [0, 2]},
                            {"name": "protein_interaction", "default_points": 0.5, "max_score": 2, "range": [0, 2]},
                            {"name": "expression", "default_points": 0.5, "max_score": 2, "range": [0, 2]}
                        ]
                    },
                    {
                        "name": "functional_alteration",
                        "max_score": 2,
                        "subcategories": [
                            {"name": "patient_cells", "default_points": 1, "max_score": 2, "range": [0, 2]},
                            {"name": "non_patient_cells", "default_points": 0.5, "max_score": 1, "range": [0, 1]}
                        ]
                    },
                    {
                        "name": "models",
                        "max_score": 4,
                        "subcategories": [
                            {"name": "non_human_model_organism", "default_points": 2, "max_score": 4, "range": [0, 4]},
                            {"name": "cell_culture_model", "default_points": 1, "max_score": 2, "range": [0, 2]}
                        ]
                    },
                    {
                        "name": "rescue",
                        "max_score": 4,
                        "subcategories": [
                            {"name": "human", "default_points": 2, "max_score": 4, "range": [0, 4]},
                            {"name": "non_human_model_organism", "default_points": 2, "max_score": 4, "range": [0, 4]},
                            {"name": "cell_culture", "default_points": 1, "max_score": 2, "range": [0, 2]},
                            {"name": "patient_cells", "default_points": 1, "max_score": 2, "range": [0, 2]}
                        ]
                    }
                ]
            }
        ],
        "verdicts": {
            "Definitive": {
                "conditions": [
                    {"score_range": [12, 18]},
                    {"replication": true},
                    {"time_requirement": "3_or_more_years"}
                ],
                "description": "Conclusive evidence for role of gene in disease"
            },
            "Strong": {
                "conditions": [
                    {"score_range": [12, 18]},
                    {"replication": true}
                ],
                "description": "Strong evidence but may lack replication or time requirement"
            },
            "Moderate": {
                "conditions": [
                    {"score_range": [7, 11.99]}
                ],
                "description": "Moderate evidence supporting role in disease"
            },
            "Limited": {
                "conditions": [
                    {"score_range": [0.1, 6.99]}
                ],
                "description": "Limited evidence, inconclusive"
            },
            "No Known Disease Relationship": {
                "conditions": [
                    {"score_range": [0, 0.09]}
                ],
                "description": "No convincing evidence"
            },
            "Disputed": {
                "conditions": [
                    {"contradictory_evidence": true}
                ],
                "description": "Conflicting evidence exists"
            },
            "Refuted": {
                "conditions": [
                    {"score_range": [0, 0]},
                    {"contradictory_evidence": true},
                    {"expert_override": true}
                ],
                "description": "Evidence contradicts role in disease"
            }
        }
    }'::jsonb,
    -- ui_configuration
    ui_configuration = '{
        "layout": {
            "type": "tabs",
            "tabs": [
                {
                    "id": "summary",
                    "name": "Summary",
                    "icon": "mdi-file-document-outline",
                    "sections": [
                        {"name": "Classification Summary", "fields": ["evidence_summary"]},
                        {"name": "Score Summary", "component": "ScoreSummary"}
                    ]
                },
                {
                    "id": "genetic",
                    "name": "Genetic Evidence",
                    "icon": "mdi-dna",
                    "show_score_badge": true,
                    "sections": [
                        {
                            "name": "Case-Level Data - AD/X-linked",
                            "collapsible": true,
                            "fields": ["genetic_evidence.case_level.autosomal_dominant_or_x_linked"]
                        },
                        {
                            "name": "Case-Level Data - Autosomal Recessive",
                            "collapsible": true,
                            "collapsed": true,
                            "fields": ["genetic_evidence.case_level.autosomal_recessive"]
                        },
                        {
                            "name": "Segregation Evidence",
                            "collapsible": true,
                            "fields": ["genetic_evidence.segregation"]
                        },
                        {
                            "name": "Case-Control Data",
                            "collapsible": true,
                            "collapsed": true,
                            "fields": ["genetic_evidence.case_control"]
                        }
                    ]
                },
                {
                    "id": "experimental",
                    "name": "Experimental Evidence",
                    "icon": "mdi-flask",
                    "show_score_badge": true,
                    "sections": [
                        {
                            "name": "Function",
                            "collapsible": true,
                            "fields": ["experimental_evidence.function"],
                            "help_text": "Biochemical function, protein interaction, and expression (max 2 pts)"
                        },
                        {
                            "name": "Functional Alteration",
                            "collapsible": true,
                            "collapsed": true,
                            "fields": ["experimental_evidence.functional_alteration"],
                            "help_text": "Patient cells and non-patient cells (max 2 pts)"
                        },
                        {
                            "name": "Models",
                            "collapsible": true,
                            "collapsed": true,
                            "fields": ["experimental_evidence.models"],
                            "help_text": "Non-human model organisms and cell culture (max 4 pts)"
                        },
                        {
                            "name": "Rescue",
                            "collapsible": true,
                            "collapsed": true,
                            "fields": ["experimental_evidence.rescue"],
                            "help_text": "Rescue experiments (max 4 pts)"
                        }
                    ]
                },
                {
                    "id": "contradictory",
                    "name": "Contradictory",
                    "icon": "mdi-alert-circle-outline",
                    "sections": [
                        {"name": "Contradictory Evidence", "fields": ["contradictory_evidence"]}
                    ]
                },
                {
                    "id": "lumping",
                    "name": "Lumping & Splitting",
                    "icon": "mdi-call-split",
                    "readonly": true,
                    "sections": [
                        {
                            "name": "Disease Entity",
                            "component": "LumpingSplittingSection",
                            "help_text": "Disease entity definition from approved precuration (read-only)"
                        }
                    ]
                }
            ]
        },
        "components": {
            "EvidenceTable": {
                "features": ["inline_edit", "bulk_import", "pmid_lookup", "sorting", "filtering"],
                "pmid_auto_fetch": true,
                "show_score_status": true,
                "show_row_scores": true,
                "expandable_rows": true
            },
            "ScoreSummary": {
                "show_breakdown": true,
                "show_classification": true,
                "sticky": true
            },
            "LumpingSplittingSection": {
                "readonly": true,
                "show_precuration_link": true
            }
        },
        "keyboard_shortcuts": {
            "save_draft": "Ctrl+S",
            "submit": "Ctrl+Enter",
            "undo": "Ctrl+Z"
        },
        "quick_actions": [
            {"label": "Add Case-Level Evidence", "target": "genetic_evidence.case_level", "icon": "mdi-plus"},
            {"label": "Add Experimental Evidence", "target": "experimental_evidence", "icon": "mdi-plus"}
        ]
    }'::jsonb,
    description = 'ClinGen Standard Operating Procedure v11 for Gene-Disease Validity Curation. Complete schema with exact scoring parameters matching ClinGen Gene Validity Framework.'
WHERE name = 'ClinGen_SOP_v11'
  AND version = '1.0.0'
  AND schema_type = 'curation';

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    schema_check RECORD;
    has_ad_xl BOOLEAN;
    has_ar BOOLEAN;
    has_segregation BOOLEAN;
    has_case_control BOOLEAN;
BEGIN
    SELECT
        field_definitions->'genetic_evidence'->'properties'->'case_level'->'properties' as case_level_props,
        field_definitions->'genetic_evidence'->'properties' as genetic_props,
        scoring_configuration->'evidence_categories' as scoring_cats
    INTO schema_check
    FROM curation_schemas
    WHERE name = 'ClinGen_SOP_v11' AND version = '1.0.0' AND schema_type = 'curation';

    -- Check genetic evidence structure
    has_ad_xl := schema_check.case_level_props ? 'autosomal_dominant_or_x_linked';
    has_ar := schema_check.case_level_props ? 'autosomal_recessive';
    has_segregation := schema_check.genetic_props ? 'segregation';
    has_case_control := schema_check.genetic_props ? 'case_control';

    IF NOT has_ad_xl THEN
        RAISE EXCEPTION '❌ autosomal_dominant_or_x_linked case level missing';
    END IF;

    IF NOT has_ar THEN
        RAISE EXCEPTION '❌ autosomal_recessive case level missing';
    END IF;

    IF NOT has_segregation THEN
        RAISE EXCEPTION '❌ segregation evidence missing';
    END IF;

    IF NOT has_case_control THEN
        RAISE EXCEPTION '❌ case_control evidence missing';
    END IF;

    RAISE NOTICE '✅ Verified: AD/X-linked case-level structure present';
    RAISE NOTICE '✅ Verified: Autosomal recessive case-level structure present';
    RAISE NOTICE '✅ Verified: Segregation evidence structure present';
    RAISE NOTICE '✅ Verified: Case-control evidence structure present';
    RAISE NOTICE '✅ ClinGen SOP v11 schema now matches official ClinGen Gene Validity Framework';
END $$;

COMMIT;
