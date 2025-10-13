# Schema Specifications: Technical Format Guide

This document defines the technical format and structure for curation methodology schemas in Gene Curator. Schemas are JSON documents that completely define how a curation methodology works, from data collection to scoring to UI generation.

## Schema Structure Overview

```json
{
  "metadata": {
    "name": "string",
    "version": "string", 
    "type": "precuration|curation|combined",
    "description": "string",
    "created_by": "string",
    "institution": "string",
    "based_on_schema": "schema_id"
  },
  "field_definitions": {},
  "validation_rules": {},
  "scoring_configuration": {},
  "workflow_states": {},
  "ui_configuration": {}
}
```

## Metadata Section

### Required Fields
- **name**: Unique identifier for the schema (e.g., "ClinGen_SOP_v11")
- **version**: Semantic version (e.g., "1.0.0", "2.1.3")
- **type**: Schema type - "precuration", "curation", or "combined"
- **description**: Human-readable description of the methodology

### Optional Fields
- **created_by**: Creator identifier
- **institution**: Institutional affiliation
- **based_on_schema**: Parent schema ID for inheritance

## Field Definitions

Defines what data to collect and how to structure it.

### Basic Field Types

```json
{
  "field_definitions": {
    "field_name": {
      "type": "string|number|boolean|date|array|object|enum",
      "required": true|false,
      "description": "Field description",
      "validation": "validation_rule_name",
      "ui_component": "component_name",
      "ui_props": {}
    }
  }
}
```

### Field Type Specifications

#### String Fields
```json
{
  "pmid": {
    "type": "string",
    "required": true,
    "min_length": 7,
    "max_length": 8,
    "validation": "pmid_format",
    "ui_component": "PMIDInput",
    "description": "PubMed identifier"
  }
}
```

#### Number Fields
```json
{
  "points": {
    "type": "number",
    "required": true,
    "min": 0,
    "max": 12,
    "step": 0.1,
    "ui_component": "NumberInput",
    "description": "Evidence points assigned"
  }
}
```

#### Enum Fields
```json
{
  "variant_type": {
    "type": "enum",
    "required": true,
    "options": [
      {"value": "null", "label": "Predicted or Proven Null"},
      {"value": "missense", "label": "Missense Variant"},
      {"value": "other", "label": "Other Variant Type"}
    ],
    "ui_component": "Select",
    "description": "Type of genetic variant"
  }
}
```

#### Array Fields
```json
{
  "case_level_data": {
    "type": "array",
    "item_schema": {
      "pmid": {"type": "string", "required": true},
      "points": {"type": "number", "min": 0, "max": 2}
    },
    "min_items": 0,
    "max_items": 100,
    "ui_component": "EvidenceTable",
    "description": "Case-level evidence entries"
  }
}
```

#### Object Fields
```json
{
  "genetic_evidence": {
    "type": "object",
    "properties": {
      "case_level_data": {"$ref": "#/field_definitions/case_level_data"},
      "segregation_data": {"$ref": "#/field_definitions/segregation_data"}
    },
    "ui_component": "EvidenceSection",
    "ui_props": {"collapsible": true, "title": "Genetic Evidence"}
  }
}
```

### Complex Evidence Structures

#### Evidence Tables
```json
{
  "case_level_data": {
    "type": "array",
    "ui_component": "EvidenceTable",
    "item_schema": {
      "pmid": {
        "type": "string",
        "required": true,
        "validation": "pmid_format",
        "ui_component": "PMIDInput"
      },
      "proband_label": {
        "type": "string", 
        "required": true,
        "min_length": 5,
        "ui_component": "TextInput",
        "placeholder": "Study identifier, e.g., 'Smith et al, Proband 1'"
      },
      "variant_type": {
        "type": "enum",
        "required": true,
        "options": [
          {"value": "null", "label": "Predicted or Proven Null"},
          {"value": "missense", "label": "Missense"}
        ],
        "ui_component": "Select"
      },
      "points": {
        "type": "number",
        "required": true,
        "min": 0,
        "max": 2,
        "step": 0.1,
        "ui_component": "NumberInput"
      },
      "rationale": {
        "type": "string",
        "required": true,
        "min_length": 20,
        "ui_component": "TextArea",
        "placeholder": "Explanation for point assignment"
      }
    },
    "scoring": {
      "max_total_points": 12,
      "point_field": "points",
      "algorithm": "sum_with_max"
    }
  }
}
```

## Validation Rules

Define how to validate field data.

### Built-in Validators

```json
{
  "validation_rules": {
    "pmid_format": {
      "type": "regex",
      "pattern": "^[0-9]{7,8}$",
      "message": "PMID must be 7-8 digits"
    },
    "email_format": {
      "type": "regex", 
      "pattern": "^[^@]+@[^@]+\\.[^@]+$",
      "message": "Invalid email format"
    },
    "mondo_id_format": {
      "type": "regex",
      "pattern": "^MONDO:[0-9]{7}$",
      "message": "MONDO ID must be format MONDO:0000000"
    },
    "hgnc_id_format": {
      "type": "regex",
      "pattern": "^HGNC:[0-9]+$", 
      "message": "HGNC ID must be format HGNC:####"
    }
  }
}
```

### Custom Validators

```json
{
  "validation_rules": {
    "points_consistency": {
      "type": "custom",
      "function": "validatePointsConsistency",
      "params": {
        "max_total": 12,
        "evidence_categories": ["case_level_data", "segregation_data"]
      },
      "message": "Total points across categories cannot exceed {max_total}"
    },
    "required_evidence": {
      "type": "custom",
      "function": "validateRequiredEvidence",
      "params": {
        "min_categories": 2,
        "categories": ["genetic_evidence", "experimental_evidence"]
      },
      "message": "At least {min_categories} evidence categories required"
    }
  }
}
```

## Scoring Configuration

Defines how to calculate scores and determine verdicts.

### Scoring Engine Selection

```json
{
  "scoring_configuration": {
    "engine": "clingen_sop_v11",
    "version": "1.0.0",
    "parameters": {
      "max_genetic_score": 12,
      "max_experimental_score": 6,
      "max_total_score": 18
    }
  }
}
```

### Verdict Thresholds

```json
{
  "scoring_configuration": {
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
      "Disputed": {
        "conditions": [
          {"field": "contradictory_evidence", "operator": "==", "value": true}
        ],
        "priority": 10
      }
    }
  }
}
```

### Scoring Algorithms

#### ClinGen SOP v11
```json
{
  "scoring_configuration": {
    "engine": "clingen_sop_v11",
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
    ]
  }
}
```

#### GenCC-Based Classification
```json
{
  "scoring_configuration": {
    "engine": "gencc_based",
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
    ]
  }
}
```

## Workflow States

Define the states and transitions for curation workflow.

### State Machine Definition

```json
{
  "workflow_states": {
    "states": [
      {
        "name": "Draft",
        "description": "Initial curation state",
        "permissions": ["curator", "admin"],
        "actions": ["edit", "submit_for_review"]
      },
      {
        "name": "In_Primary_Review",
        "description": "Under primary reviewer assessment", 
        "permissions": ["primary_reviewer", "admin"],
        "actions": ["approve", "request_changes", "reject"]
      },
      {
        "name": "In_Secondary_Review",
        "description": "Under secondary reviewer assessment",
        "permissions": ["secondary_reviewer", "admin"], 
        "actions": ["approve", "request_changes", "reject"]
      },
      {
        "name": "Approved",
        "description": "Approved and ready for publication",
        "permissions": ["admin"],
        "actions": ["publish", "return_to_review"]
      },
      {
        "name": "Published",
        "description": "Published and public",
        "permissions": ["admin"], 
        "actions": ["archive", "create_revision"]
      }
    ],
    "transitions": {
      "Draft": ["In_Primary_Review"],
      "In_Primary_Review": ["Draft", "In_Secondary_Review", "Approved"],
      "In_Secondary_Review": ["In_Primary_Review", "Approved"],
      "Approved": ["Published", "In_Secondary_Review"],
      "Published": ["Approved"]
    },
    "initial_state": "Draft"
  }
}
```

### Role-Based Permissions

```json
{
  "workflow_states": {
    "roles": {
      "curator": {
        "permissions": ["read", "create", "edit_own"],
        "allowed_states": ["Draft"]
      },
      "primary_reviewer": {
        "permissions": ["read", "review", "comment"],
        "allowed_states": ["In_Primary_Review"]
      },
      "secondary_reviewer": {
        "permissions": ["read", "review", "comment", "approve"],
        "allowed_states": ["In_Secondary_Review"]
      },
      "admin": {
        "permissions": ["read", "create", "edit", "delete", "publish"],
        "allowed_states": ["*"]
      }
    }
  }
}
```

## UI Configuration

Define how to render the schema as user interface components.

### Form Layout

```json
{
  "ui_configuration": {
    "layout": {
      "type": "sections",
      "sections": [
        {
          "name": "Basic Information",
          "collapsible": false,
          "fields": ["disease_name", "mode_of_inheritance"],
          "columns": 2
        },
        {
          "name": "Genetic Evidence",
          "collapsible": true,
          "collapsed": false,
          "fields": ["genetic_evidence"],
          "help_text": "Evidence supporting genetic association"
        },
        {
          "name": "Experimental Evidence", 
          "collapsible": true,
          "collapsed": true,
          "fields": ["experimental_evidence"]
        }
      ]
    }
  }
}
```

### Component Mapping

```json
{
  "ui_configuration": {
    "components": {
      "PMIDInput": {
        "props": {
          "validate_pubmed": true,
          "show_abstract": true,
          "placeholder": "e.g., 12345678"
        }
      },
      "EvidenceTable": {
        "props": {
          "sortable": true,
          "filterable": true,
          "exportable": true,
          "add_button_text": "Add Evidence Item"
        }
      },
      "Select": {
        "props": {
          "searchable": true,
          "clearable": false
        }
      },
      "NumberInput": {
        "props": {
          "show_slider": false,
          "decimal_places": 1
        }
      }
    }
  }
}
```

### Real-Time Features

```json
{
  "ui_configuration": {
    "real_time": {
      "scoring": {
        "enabled": true,
        "update_delay": 500,
        "show_breakdown": true
      },
      "validation": {
        "enabled": true,
        "show_inline_errors": true,
        "validate_on_blur": true
      },
      "save": {
        "auto_save": true,
        "save_interval": 10000,
        "show_save_status": true
      }
    }
  }
}
```

## Complete Schema Examples

### ClinGen SOP v11 Schema (Condensed)

```json
{
  "metadata": {
    "name": "ClinGen_SOP_v11",
    "version": "1.0.0",
    "type": "curation",
    "description": "ClinGen Standard Operating Procedure v11 for Gene-Disease Validity"
  },
  "field_definitions": {
    "genetic_evidence": {
      "type": "object",
      "properties": {
        "case_level_data": {
          "type": "array",
          "ui_component": "EvidenceTable",
          "item_schema": {
            "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
            "proband_label": {"type": "string", "required": true},
            "variant_type": {"type": "enum", "options": ["null", "missense"]},
            "points": {"type": "number", "min": 0, "max": 2}
          },
          "scoring": {"max_total_points": 12}
        }
      }
    }
  },
  "scoring_configuration": {
    "engine": "clingen_sop_v11",
    "verdicts": {
      "Definitive": {"conditions": [{"field": "total_score", "operator": ">=", "value": 12}]},
      "Strong": {"conditions": [{"field": "total_score", "operator": ">=", "value": 7}]}
    }
  },
  "workflow_states": {
    "states": ["Draft", "Review", "Approved", "Published"],
    "transitions": {"Draft": ["Review"], "Review": ["Approved"]}
  },
  "ui_configuration": {
    "layout": {
      "sections": [
        {"name": "Genetic Evidence", "fields": ["genetic_evidence"], "collapsible": true}
      ]
    }
  }
}
```

## Schema Validation

Every schema must pass validation before it can be used:

### Required Sections
- ✅ metadata (with name, version, type)
- ✅ field_definitions (non-empty)
- ✅ workflow_states (with valid state machine)
- ✅ ui_configuration (with layout)

### Optional Sections
- scoring_configuration (if scoring is needed)
- validation_rules (if custom validation is needed)

### Validation Rules
1. **Name Uniqueness**: Schema name+version must be unique
2. **State Machine Validity**: All transitions must be valid
3. **Field References**: All field references in UI must exist
4. **Scoring Consistency**: Scoring config must match field definitions
5. **Component Availability**: All UI components must be registered

## Schema Evolution

### Versioning Strategy
- **Major Version** (1.0.0 → 2.0.0): Breaking changes to field structure
- **Minor Version** (1.0.0 → 1.1.0): New fields or non-breaking changes  
- **Patch Version** (1.0.0 → 1.0.1): Bug fixes or clarifications

### Schema Inheritance

```json
{
  "metadata": {
    "name": "ClinGen_SOP_v11_Extended",
    "version": "1.0.0",
    "based_on_schema": "clingen_sop_v11_1.0.0",
    "description": "ClinGen SOP v11 with institutional extensions"
  },
  "field_definitions": {
    "extends": "parent",
    "additional_fields": {
      "institutional_notes": {
        "type": "string",
        "ui_component": "TextArea"
      }
    }
  }
}
```

This specification provides the complete technical foundation for creating methodology schemas that work with Gene Curator's flexible architecture.