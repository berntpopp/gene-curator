-- Schema-Agnostic Seed Data
-- Initial Scopes, Schemas, and Workflow Pairs

-- ========================================
-- INITIAL SCOPES (CLINICAL SPECIALTIES)
-- ========================================

-- Insert core clinical specialty scopes
INSERT INTO scopes (id, name, display_name, description, institution, scope_config) VALUES
-- Nephrology/Kidney Genetics
(uuid_generate_v4(), 'kidney-genetics', 'Kidney Genetics', 'Gene-disease associations related to kidney and urological disorders', 'Halbritter Lab', 
 '{"primary_inheritance_modes": ["Autosomal Recessive", "Autosomal Dominant", "X-linked"], "focus_areas": ["CAKUT", "Ciliopathies", "Tubulopathies", "FSGS"]}'),

-- Cardiology Genetics  
(uuid_generate_v4(), 'cardio-genetics', 'Cardiovascular Genetics', 'Gene-disease associations for cardiovascular disorders', 'General', 
 '{"primary_inheritance_modes": ["Autosomal Dominant", "Autosomal Recessive"], "focus_areas": ["Cardiomyopathy", "Arrhythmia", "Congenital Heart Disease"]}'),

-- Neurology Genetics
(uuid_generate_v4(), 'neuro-genetics', 'Neurological Genetics', 'Gene-disease associations for neurological and neurodevelopmental disorders', 'General', 
 '{"primary_inheritance_modes": ["Autosomal Dominant", "Autosomal Recessive", "X-linked", "Mitochondrial"], "focus_areas": ["Epilepsy", "Intellectual Disability", "Movement Disorders"]}'),

-- Oncogenetics
(uuid_generate_v4(), 'oncogenetics', 'Oncogenetics', 'Gene-disease associations for hereditary cancer syndromes and tumor predisposition', 'General',
 '{"primary_inheritance_modes": ["Autosomal Dominant", "Autosomal Recessive"], "focus_areas": ["Hereditary Cancer", "Tumor Suppressor Genes", "DNA Repair", "Tumor Predisposition"]}'),

-- Rare Disease Genetics
(uuid_generate_v4(), 'rare-disease', 'Rare Disease Genetics', 'Gene-disease associations for rare and ultra-rare genetic disorders', 'General',
 '{"primary_inheritance_modes": ["Autosomal Dominant", "Autosomal Recessive", "X-linked", "Mitochondrial"], "focus_areas": ["Metabolic Disorders", "Syndromic Conditions", "Ultra-Rare Diseases"]}');

-- ========================================
-- CLINGEN SOP V11 SCHEMA DEFINITION
-- ========================================

-- Insert ClinGen SOP v11 curation schema
INSERT INTO curation_schemas (
    id, name, version, schema_type, description, institution,
    field_definitions, validation_rules, scoring_configuration, 
    workflow_states, ui_configuration, is_active, schema_hash
) VALUES (
    uuid_generate_v4(),
    'ClinGen_SOP_v11',
    '1.0.0',
    'curation',
    'ClinGen Standard Operating Procedure v11 for Gene-Disease Validity Curation',
    'ClinGen',
    -- field_definitions
    '{
        "genetic_evidence": {
            "type": "object",
            "properties": {
                "case_level_data": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "proband_label": {"type": "string", "required": true, "min_length": 5},
                        "variant_type": {
                            "type": "enum", 
                            "required": true,
                            "options": [
                                {"value": "null", "label": "Predicted or Proven Null"},
                                {"value": "missense", "label": "Missense"},
                                {"value": "other", "label": "Other Variant Type"}
                            ]
                        },
                        "points": {"type": "number", "required": true, "min": 0, "max": 2, "step": 0.1},
                        "rationale": {"type": "string", "required": true, "min_length": 20}
                    },
                    "scoring": {"max_total_points": 12, "point_field": "points"}
                },
                "segregation_data": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "family_label": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 3}
                    },
                    "scoring": {"max_total_points": 3}
                },
                "case_control_data": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "study_type": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 6}
                    },
                    "scoring": {"max_total_points": 6}
                }
            }
        },
        "experimental_evidence": {
            "type": "object",
            "properties": {
                "function": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "evidence_type": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 2}
                    },
                    "scoring": {"max_total_points": 2}
                },
                "models": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "model_type": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 4}
                    },
                    "scoring": {"max_total_points": 4}
                },
                "rescue": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "rescue_type": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 2}
                    },
                    "scoring": {"max_total_points": 2}
                }
            }
        },
        "contradictory_evidence": {
            "type": "array",
            "ui_component": "EvidenceTable",
            "item_schema": {
                "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                "description": {"type": "string", "required": true},
                "rationale": {"type": "string", "required": true}
            }
        },
        "entity_definition": {
            "type": "object",
            "properties": {
                "disease_name": {"type": "string", "required": true},
                "mondo_id": {"type": "string", "required": true, "validation": "mondo_id_format"},
                "mode_of_inheritance": {"type": "string", "required": true},
                "lumping_splitting_rationale": {"type": "string", "required": true}
            }
        }
    }',
    -- validation_rules
    '{
        "pmid_format": {
            "type": "regex",
            "pattern": "^[0-9]{7,8}$",
            "message": "PMID must be 7-8 digits"
        },
        "mondo_id_format": {
            "type": "regex",
            "pattern": "^MONDO:[0-9]{7}$",
            "message": "MONDO ID must be format MONDO:0000000"
        },
        "required_evidence": {
            "type": "custom",
            "function": "validateRequiredEvidence",
            "params": {"min_categories": 1},
            "message": "At least one evidence category required"
        }
    }',
    -- scoring_configuration
    '{
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
                    {"name": "case_level_data", "max_score": 12},
                    {"name": "segregation_data", "max_score": 3},
                    {"name": "case_control_data", "max_score": 6}
                ]
            },
            {
                "name": "experimental_evidence",
                "max_score": 6,
                "subcategories": [
                    {"name": "function", "max_score": 2},
                    {"name": "models", "max_score": 4},
                    {"name": "rescue", "max_score": 2}
                ]
            }
        ],
        "verdicts": {
            "Definitive": {
                "conditions": [
                    {"field": "total_score", "operator": ">=", "value": 12},
                    {"field": "contradictory_evidence", "operator": "==", "value": false}
                ],
                "priority": 1
            },
            "Strong": {
                "conditions": [
                    {"field": "total_score", "operator": ">=", "value": 7},
                    {"field": "total_score", "operator": "<", "value": 12},
                    {"field": "contradictory_evidence", "operator": "==", "value": false}
                ],
                "priority": 2
            },
            "Moderate": {
                "conditions": [
                    {"field": "total_score", "operator": ">=", "value": 4},
                    {"field": "total_score", "operator": "<", "value": 7}
                ],
                "priority": 3
            },
            "Limited": {
                "conditions": [
                    {"field": "total_score", "operator": ">=", "value": 1},
                    {"field": "total_score", "operator": "<", "value": 4}
                ],
                "priority": 4
            },
            "Disputed": {
                "conditions": [
                    {"field": "contradictory_evidence", "operator": "==", "value": true}
                ],
                "priority": 10
            },
            "No Known Disease Relationship": {
                "conditions": [
                    {"field": "total_score", "operator": "<", "value": 1}
                ],
                "priority": 11
            }
        }
    }',
    -- workflow_states
    '{
        "states": [
            {"name": "draft", "description": "Initial curation state", "permissions": ["curator", "admin"]},
            {"name": "submitted", "description": "Submitted for review", "permissions": ["admin"]},
            {"name": "in_review", "description": "Under reviewer assessment", "permissions": ["reviewer", "admin"]},
            {"name": "approved", "description": "Approved by reviewer", "permissions": ["admin"]},
            {"name": "rejected", "description": "Rejected by reviewer", "permissions": ["curator", "admin"]},
            {"name": "active", "description": "Active and published", "permissions": ["admin"]},
            {"name": "archived", "description": "Archived version", "permissions": ["admin"]}
        ],
        "transitions": {
            "draft": ["submitted"],
            "submitted": ["in_review"],
            "in_review": ["approved", "rejected"],
            "approved": ["active"],
            "rejected": ["draft"],
            "active": ["archived"],
            "archived": []
        },
        "initial_state": "draft"
    }',
    -- ui_configuration
    '{
        "layout": {
            "type": "sections",
            "sections": [
                {
                    "name": "Entity Definition",
                    "collapsible": false,
                    "fields": ["entity_definition"],
                    "help_text": "Define the gene-disease relationship being curated"
                },
                {
                    "name": "Genetic Evidence",
                    "collapsible": true,
                    "collapsed": false,
                    "fields": ["genetic_evidence"],
                    "help_text": "Evidence supporting genetic association per ClinGen SOP v11"
                },
                {
                    "name": "Experimental Evidence",
                    "collapsible": true,
                    "collapsed": true,
                    "fields": ["experimental_evidence"],
                    "help_text": "Functional evidence supporting gene-disease mechanism"
                },
                {
                    "name": "Contradictory Evidence",
                    "collapsible": true,
                    "collapsed": true,
                    "fields": ["contradictory_evidence"],
                    "help_text": "Evidence that contradicts the gene-disease association"
                }
            ]
        },
        "components": {
            "EvidenceTable": {
                "props": {
                    "sortable": true,
                    "filterable": true,
                    "exportable": true,
                    "add_button_text": "Add Evidence Item"
                }
            }
        },
        "real_time": {
            "scoring": {"enabled": true, "update_delay": 500},
            "validation": {"enabled": true, "show_inline_errors": true},
            "save": {"auto_save": true, "save_interval": 10000}
        }
    }',
    true,
    encode(digest('ClinGen_SOP_v11_1.0.0', 'sha256'), 'hex')
);

-- ========================================
-- GENCC-BASED SCHEMA DEFINITION
-- ========================================

-- Insert GenCC-based classification schema
INSERT INTO curation_schemas (
    id, name, version, schema_type, description, institution,
    field_definitions, validation_rules, scoring_configuration,
    workflow_states, ui_configuration, is_active, schema_hash
) VALUES (
    uuid_generate_v4(),
    'GenCC_Classification',
    '1.0.0',
    'curation',
    'GenCC-based gene-disease validity classification methodology',
    'GenCC',
    -- field_definitions (similar to ClinGen but adapted for GenCC)
    '{
        "genetic_evidence": {
            "type": "object",
            "properties": {
                "case_level_data": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "proband_label": {"type": "string", "required": true},
                        "variant_type": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 2}
                    },
                    "scoring": {"max_total_points": 12}
                },
                "segregation_data": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "family_label": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 3}
                    },
                    "scoring": {"max_total_points": 3}
                }
            }
        },
        "experimental_evidence": {
            "type": "object",
            "properties": {
                "function": {
                    "type": "array",
                    "ui_component": "EvidenceTable",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "evidence_type": {"type": "string", "required": true},
                        "points": {"type": "number", "required": true, "min": 0, "max": 2}
                    },
                    "scoring": {"max_total_points": 2}
                }
            }
        }
    }',
    -- validation_rules
    '{
        "pmid_format": {
            "type": "regex",
            "pattern": "^[0-9]{7,8}$",
            "message": "PMID must be 7-8 digits"
        }
    }',
    -- scoring_configuration
    '{
        "engine": "gencc_based",
        "version": "1.0.0",
        "verdicts": {
            "Definitive": {"conditions": [{"field": "total_score", "operator": ">=", "value": 12}]},
            "Strong": {"conditions": [{"field": "total_score", "operator": ">=", "value": 7}]},
            "Moderate": {"conditions": [{"field": "total_score", "operator": ">=", "value": 4}]},
            "Limited": {"conditions": [{"field": "total_score", "operator": ">=", "value": 1}]}
        }
    }',
    -- workflow_states (same as ClinGen)
    '{
        "states": [
            {"name": "draft", "description": "Initial curation state"},
            {"name": "submitted", "description": "Submitted for review"},
            {"name": "in_review", "description": "Under reviewer assessment"},
            {"name": "approved", "description": "Approved by reviewer"},
            {"name": "active", "description": "Active and published"}
        ],
        "transitions": {
            "draft": ["submitted"],
            "submitted": ["in_review"],
            "in_review": ["approved"],
            "approved": ["active"]
        }
    }',
    -- ui_configuration (simplified)
    '{
        "layout": {
            "sections": [
                {"name": "Genetic Evidence", "fields": ["genetic_evidence"]},
                {"name": "Experimental Evidence", "fields": ["experimental_evidence"]}
            ]
        }
    }',
    true,
    encode(digest('GenCC_Classification_1.0.0', 'sha256'), 'hex')
);

-- ========================================
-- QUALITATIVE ASSESSMENT SCHEMA
-- ========================================

-- Insert qualitative assessment schema for institutions
INSERT INTO curation_schemas (
    id, name, version, schema_type, description, institution,
    field_definitions, validation_rules, scoring_configuration,
    workflow_states, ui_configuration, is_active, schema_hash
) VALUES (
    uuid_generate_v4(),
    'Qualitative_Assessment',
    '1.0.0',
    'curation',
    'Institutional qualitative assessment methodology',
    'General',
    -- field_definitions
    '{
        "clinical_assessment": {
            "type": "object",
            "properties": {
                "phenotype_match": {
                    "type": "enum",
                    "options": [
                        {"value": "excellent", "label": "Excellent"},
                        {"value": "good", "label": "Good"},
                        {"value": "fair", "label": "Fair"},
                        {"value": "poor", "label": "Poor"}
                    ],
                    "required": true
                },
                "inheritance_consistency": {
                    "type": "enum",
                    "options": [
                        {"value": "consistent", "label": "Consistent"},
                        {"value": "partially_consistent", "label": "Partially Consistent"},
                        {"value": "inconsistent", "label": "Inconsistent"}
                    ],
                    "required": true
                }
            }
        },
        "literature_review": {
            "type": "object",
            "properties": {
                "evidence_quality": {
                    "type": "enum",
                    "options": [
                        {"value": "high", "label": "High"},
                        {"value": "moderate", "label": "Moderate"},
                        {"value": "low", "label": "Low"}
                    ],
                    "required": true
                },
                "study_design_strength": {
                    "type": "enum",
                    "options": [
                        {"value": "strong", "label": "Strong"},
                        {"value": "adequate", "label": "Adequate"},
                        {"value": "weak", "label": "Weak"}
                    ],
                    "required": true
                }
            }
        }
    }',
    -- validation_rules
    '{}',
    -- scoring_configuration
    '{
        "engine": "qualitative_assessment",
        "version": "1.0.0",
        "verdicts": {
            "Strong Association": {"conditions": [{"field": "total_score", "operator": ">=", "value": 8}]},
            "Moderate Association": {"conditions": [{"field": "total_score", "operator": ">=", "value": 5}]},
            "Weak Association": {"conditions": [{"field": "total_score", "operator": ">=", "value": 2}]},
            "Insufficient Evidence": {"conditions": [{"field": "total_score", "operator": "<", "value": 2}]}
        }
    }',
    -- workflow_states
    '{
        "states": [
            {"name": "draft", "description": "Initial assessment"},
            {"name": "submitted", "description": "Submitted for review"},
            {"name": "approved", "description": "Approved assessment"},
            {"name": "active", "description": "Active assessment"}
        ],
        "transitions": {
            "draft": ["submitted"],
            "submitted": ["approved"],
            "approved": ["active"]
        }
    }',
    -- ui_configuration
    '{
        "layout": {
            "sections": [
                {"name": "Clinical Assessment", "fields": ["clinical_assessment"]},
                {"name": "Literature Review", "fields": ["literature_review"]}
            ]
        }
    }',
    true,
    encode(digest('Qualitative_Assessment_1.0.0', 'sha256'), 'hex')
);

-- ========================================
-- PRECURATION SCHEMA
-- ========================================

-- Insert precuration schema
INSERT INTO curation_schemas (
    id, name, version, schema_type, description, 
    field_definitions, validation_rules, scoring_configuration,
    workflow_states, ui_configuration, is_active, schema_hash
) VALUES (
    uuid_generate_v4(),
    'Standard_Precuration',
    '1.0.0',
    'precuration',
    'Standard precuration schema for initial gene-disease evaluation',
    -- field_definitions
    '{
        "entity_definition": {
            "type": "object",
            "properties": {
                "disease_name": {"type": "string", "required": true},
                "mondo_id": {"type": "string", "required": true, "validation": "mondo_id_format"},
                "mode_of_inheritance": {
                    "type": "enum",
                    "options": [
                        {"value": "autosomal_dominant", "label": "Autosomal Dominant"},
                        {"value": "autosomal_recessive", "label": "Autosomal Recessive"},
                        {"value": "x_linked", "label": "X-linked"},
                        {"value": "mitochondrial", "label": "Mitochondrial"},
                        {"value": "unknown", "label": "Unknown"}
                    ],
                    "required": true
                }
            }
        },
        "lumping_splitting": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "enum",
                    "options": [
                        {"value": "lump", "label": "Lump"},
                        {"value": "split", "label": "Split"},
                        {"value": "undecided", "label": "Undecided"}
                    ],
                    "required": true
                },
                "rationale": {"type": "string", "required": true, "min_length": 50}
            }
        },
        "initial_assessment": {
            "type": "object",
            "properties": {
                "literature_search_strategy": {"type": "string", "required": true},
                "key_references": {
                    "type": "array",
                    "item_schema": {
                        "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
                        "relevance": {"type": "string", "required": true}
                    }
                },
                "preliminary_verdict": {"type": "string"}
            }
        }
    }',
    -- validation_rules
    '{
        "mondo_id_format": {
            "type": "regex",
            "pattern": "^MONDO:[0-9]{7}$",
            "message": "MONDO ID must be format MONDO:0000000"
        },
        "pmid_format": {
            "type": "regex",
            "pattern": "^[0-9]{7,8}$",
            "message": "PMID must be 7-8 digits"
        }
    }',
    -- No scoring for precuration
    null,
    -- workflow_states
    '{
        "states": [
            {"name": "draft", "description": "Initial precuration"},
            {"name": "submitted", "description": "Completed precuration"},
            {"name": "approved", "description": "Approved for curation"}
        ],
        "transitions": {
            "draft": ["submitted"],
            "submitted": ["approved"]
        }
    }',
    -- ui_configuration
    '{
        "layout": {
            "sections": [
                {"name": "Entity Definition", "fields": ["entity_definition"]},
                {"name": "Lumping/Splitting Decision", "fields": ["lumping_splitting"]},
                {"name": "Initial Assessment", "fields": ["initial_assessment"]}
            ]
        }
    }',
    true,
    encode(digest('Standard_Precuration_1.0.0', 'sha256'), 'hex')
);

-- ========================================
-- WORKFLOW PAIRS
-- ========================================

-- Create workflow pairs combining precuration and curation schemas
INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, curation_schema_id, data_mapping, workflow_config, description) 
SELECT 
    uuid_generate_v4(),
    'ClinGen_Complete_Workflow',
    '1.0.0',
    (SELECT id FROM curation_schemas WHERE name = 'Standard_Precuration' AND version = '1.0.0'),
    (SELECT id FROM curation_schemas WHERE name = 'ClinGen_SOP_v11' AND version = '1.0.0'),
    '{
        "precuration_to_curation": {
            "entity_definition.disease_name": "entity_definition.disease_name",
            "entity_definition.mondo_id": "entity_definition.mondo_id",
            "entity_definition.mode_of_inheritance": "entity_definition.mode_of_inheritance",
            "lumping_splitting.rationale": "entity_definition.lumping_splitting_rationale"
        }
    }'::jsonb,
    '{
        "require_precuration": true,
        "auto_populate_fields": true,
        "review_required": true
    }'::jsonb,
    'Complete ClinGen workflow from precuration to curation with SOP v11 compliance'

UNION ALL

SELECT 
    uuid_generate_v4(),
    'GenCC_Complete_Workflow',
    '1.0.0',
    (SELECT id FROM curation_schemas WHERE name = 'Standard_Precuration' AND version = '1.0.0'),
    (SELECT id FROM curation_schemas WHERE name = 'GenCC_Classification' AND version = '1.0.0'),
    '{
        "precuration_to_curation": {
            "entity_definition.disease_name": "entity_definition.disease_name",
            "entity_definition.mondo_id": "entity_definition.mondo_id",
            "entity_definition.mode_of_inheritance": "entity_definition.mode_of_inheritance"
        }
    }'::jsonb,
    '{
        "require_precuration": true,
        "auto_populate_fields": true,
        "review_required": true
    }'::jsonb,
    'GenCC-based workflow from precuration to classification'

UNION ALL

SELECT 
    uuid_generate_v4(),
    'Qualitative_Complete_Workflow',
    '1.0.0',
    (SELECT id FROM curation_schemas WHERE name = 'Standard_Precuration' AND version = '1.0.0'),
    (SELECT id FROM curation_schemas WHERE name = 'Qualitative_Assessment' AND version = '1.0.0'),
    '{
        "precuration_to_curation": {
            "entity_definition.disease_name": "entity_definition.disease_name",
            "entity_definition.mode_of_inheritance": "entity_definition.mode_of_inheritance"
        }
    }'::jsonb,
    '{
        "require_precuration": true,
        "review_required": false
    }'::jsonb,
    'Qualitative assessment workflow for institutional use';

-- ========================================
-- UPDATE SCOPES WITH DEFAULT WORKFLOW PAIRS
-- ========================================

-- Set default workflow pairs for scopes
UPDATE scopes SET default_workflow_pair_id = (
    SELECT id FROM workflow_pairs WHERE name = 'ClinGen_Complete_Workflow' AND version = '1.0.0'
) WHERE name IN ('kidney-genetics', 'cardio-genetics', 'neuro-genetics');

UPDATE scopes SET default_workflow_pair_id = (
    SELECT id FROM workflow_pairs WHERE name = 'Qualitative_Complete_Workflow' AND version = '1.0.0'
) WHERE name IN ('oncogenetics', 'rare-disease');

-- ========================================
-- DEVELOPMENT USERS (1 Admin + 3 Test Users)
-- ========================================

-- **CRITICAL ARCHITECTURE NOTE**:
-- Application roles: 'admin' (platform-level) and 'user' (standard user)
-- Scope roles: 'admin', 'curator', 'reviewer', 'viewer' (defined in scope_memberships)
--
-- This seed data creates:
-- - 1 application admin (full platform access)
-- - 3 test users with scope-level roles (no global curator/reviewer/viewer roles)

-- Insert application admin user
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'admin@genecurator.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Admin User',
    'admin',  -- Application-level admin role
    'Gene Curator Platform',
    (SELECT array_agg(id) FROM scopes WHERE is_active = true),
    '0000-0000-0000-0001',
    ARRAY['Platform Administration', 'System Management'],
    true
);

-- ========================================
-- TEST USERS (Standard Users with Scope Roles)
-- ========================================

-- Test User 1: Alice Smith (curator in kidney-genetics scope)
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'alice.smith@genecurator.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Alice Smith',
    'user',  -- Standard user (scope roles assigned via scope_memberships)
    'Nephrology Research Institute',
    (SELECT array_agg(id) FROM scopes WHERE name = 'kidney-genetics'),
    '0000-0001-5000-0001',
    ARRAY['Nephrology', 'CAKUT', 'Ciliopathies'],
    true
);

-- Test User 2: Bob Jones (reviewer in cardio-genetics scope)
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'bob.jones@genecurator.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Bob Jones',
    'user',  -- Standard user (scope roles assigned via scope_memberships)
    'Cardiovascular Genomics Center',
    (SELECT array_agg(id) FROM scopes WHERE name = 'cardio-genetics'),
    '0000-0001-5000-0002',
    ARRAY['Cardiology', 'Arrhythmia', 'Congenital Heart Disease'],
    true
);

-- Test User 3: Carol Williams (viewer in neuro-genetics scope)
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'carol.williams@genecurator.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Carol Williams',
    'user',  -- Standard user (scope roles assigned via scope_memberships)
    'Neurology and Epilepsy Lab',
    (SELECT array_agg(id) FROM scopes WHERE name = 'neuro-genetics'),
    '0000-0001-5000-0003',
    ARRAY['Neurology', 'Epilepsy', 'Intellectual Disability'],
    true
);

-- ========================================
-- SCOPE MEMBERSHIPS (Scope-Level Roles)
-- ========================================

-- **CRITICAL**: These entries define SCOPE-LEVEL roles, not application roles
-- Scope roles: 'admin', 'curator', 'reviewer', 'viewer'

-- Admin user as scope admin in all scopes
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status)
SELECT
    s.id as scope_id,
    (SELECT id FROM users_new WHERE email = 'admin@genecurator.org') as user_id,
    'admin' as role,
    true as is_active,
    'accepted' as invitation_status
FROM scopes s
WHERE s.is_active = true;

-- Alice Smith as curator in kidney-genetics scope
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(
    (SELECT id FROM scopes WHERE name = 'kidney-genetics'),
    (SELECT id FROM users_new WHERE email = 'alice.smith@genecurator.org'),
    'curator',  -- Scope-level curator role
    true,
    'accepted'
);

-- Bob Jones as reviewer in cardio-genetics scope
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(
    (SELECT id FROM scopes WHERE name = 'cardio-genetics'),
    (SELECT id FROM users_new WHERE email = 'bob.jones@genecurator.org'),
    'reviewer',  -- Scope-level reviewer role
    true,
    'accepted'
);

-- Carol Williams as viewer in neuro-genetics scope
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(
    (SELECT id FROM scopes WHERE name = 'neuro-genetics'),
    (SELECT id FROM users_new WHERE email = 'carol.williams@genecurator.org'),
    'viewer',  -- Scope-level viewer role
    true,
    'accepted'
);

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE scopes IS 'Clinical specialty scopes with ClinGen, GenCC, and custom methodology support';
COMMENT ON TABLE curation_schemas IS 'Contains ClinGen SOP v11, GenCC, qualitative assessment, and precuration schemas';
COMMENT ON TABLE workflow_pairs IS 'Complete workflows combining precuration and curation methodologies';

-- Display summary of seed data
SELECT 'Seed Data Summary' as component, 
       COUNT(*) as count,
       string_agg(name, ', ') as items
FROM (
    SELECT 'Scopes' as component, COUNT(*) as count, string_agg(display_name, ', ') as name FROM scopes
    UNION ALL
    SELECT 'Schemas' as component, COUNT(*) as count, string_agg(name || ' v' || version, ', ') as name FROM curation_schemas
    UNION ALL 
    SELECT 'Workflow Pairs' as component, COUNT(*) as count, string_agg(name || ' v' || version, ', ') as name FROM workflow_pairs
    UNION ALL
    SELECT 'Users' as component, COUNT(*) as count, string_agg(name, ', ') as name FROM users_new
) summary
GROUP BY component
ORDER BY component;