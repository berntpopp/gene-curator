# Gene Curator: Schema-Agnostic Architecture

## Overview

Gene Curator is a **methodology-agnostic** curation platform that supports any scientific approach to gene-disease association through configurable schemas. The platform adapts to different curation methodologies through dynamic configuration rather than hard-coded implementations.

## Architectural Principles

### 1. Schema-Driven Design
**Everything is configurable through schemas**: field definitions, validation rules, scoring algorithms, workflow states, and UI components. No curation methodology is hard-coded into the system.

### 2. Universal Platform
The same codebase supports:
- **ClinGen SOP v11** gene-disease validity curation
- **GenCC-based** classification approaches  
- **Custom institutional** methodologies
- **Future methodologies** not yet developed

### 3. Clean Separation of Concerns
```
Schema Definitions → Define what/how to curate
Scoring Engines   → Calculate verdicts/classifications  
Dynamic UI        → Render forms and interfaces
Flexible Storage  → Store evidence in any structure
```

## System Architecture

### High-Level Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Schema Repository │    │  Scoring Engine     │    │   Dynamic Frontend  │
│                     │    │     Registry        │    │                     │
│ • Methodology Defs  │◄──►│                     │◄──►│                     │
│ • Version Control   │    │ • ClinGen Engine    │    │ • Form Generation   │
│ • Validation Rules  │    │ • GenCC Engine      │    │ • Real-time Scoring │
│ • UI Configuration  │    │ • Custom Engines    │    │ • Schema Selection  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
         ┌─────────────────────────────────────────────────────────┐
         │              Flexible Data Storage Layer                │
         │                                                         │
         │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
         │  │ Evidence    │  │ Computed    │  │ Workflow    │    │
         │  │ Data        │  │ Scores      │  │ States      │    │
         │  │ (JSONB)     │  │ (JSONB)     │  │ (Dynamic)   │    │
         │  └─────────────┘  └─────────────┘  └─────────────┘    │
         └─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Schema Repository
**Purpose**: Store and manage curation methodology definitions

**Key Features**:
- Version control for methodology evolution
- Schema inheritance and customization
- Validation of schema definitions
- User/institution preferences

**Database Tables**:
```sql
curation_schemas  → Store methodology definitions
workflow_pairs    → Combine precuration + curation schemas
schema_selections → User/institution preferences
```

### 2. Scoring Engine Registry
**Purpose**: Pluggable calculation engines for different methodologies

**Key Features**:
- Runtime engine selection based on schema
- Consistent interface for all methodologies
- Custom engine registration
- Validation and error handling

**Supported Engines**:
- `clingen_sop_v11` → ClinGen Standard Operating Procedure v11
- `gencc_based` → GenCC classification approaches
- `qualitative_assessment` → Institution-specific qualitative methods
- `custom_*` → User-defined scoring algorithms

### 3. Dynamic User Interface
**Purpose**: Generate forms and interfaces from schema definitions

**Key Features**:
- Real-time form generation from schemas
- Live validation and scoring updates
- Methodology switching interface
- Responsive, accessible design

**Component Types**:
- `DynamicForm` → Renders complete curation forms
- `EvidenceTable` → Dynamic evidence entry tables
- `PMIDInput` → Literature reference validation
- `ScoreDisplay` → Real-time scoring visualization

### 4. Flexible Data Storage
**Purpose**: Store evidence data in any structure required by schemas

**Key Features**:
- JSONB-based evidence storage
- Schema-aware validation triggers
- Performance-optimized indexing
- Complete audit trails

## Database Architecture

### Schema-Agnostic Design

```sql
-- Core flexible storage
CREATE TABLE curations (
    id UUID PRIMARY KEY,
    gene_id UUID REFERENCES genes(id),
    workflow_pair_id UUID REFERENCES workflow_pairs(id),
    
    -- Current workflow state (defined by schema)
    current_stage ENUM('precuration', 'curation'),
    current_status VARCHAR(50) NOT NULL,
    
    -- Flexible evidence storage
    precuration_data JSONB DEFAULT '{}',
    curation_data JSONB DEFAULT '{}',
    
    -- Schema-computed results
    computed_scores JSONB DEFAULT '{}',
    computed_verdict VARCHAR(100),
    computed_summary TEXT,
    
    -- Audit and integrity
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    record_hash VARCHAR(64) UNIQUE,
    previous_hash VARCHAR(64)
);

-- Schema definitions
CREATE TABLE curation_schemas (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    schema_type ENUM('precuration', 'curation', 'combined'),
    
    -- Complete schema definition
    field_definitions JSONB NOT NULL,
    validation_rules JSONB NOT NULL,
    scoring_configuration JSONB,
    workflow_states JSONB NOT NULL,
    ui_configuration JSONB NOT NULL,
    
    -- Metadata
    description TEXT,
    institution VARCHAR(255),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(name, version)
);

-- Schema pairing system
CREATE TABLE workflow_pairs (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    
    precuration_schema_id UUID REFERENCES curation_schemas(id),
    curation_schema_id UUID REFERENCES curation_schemas(id),
    
    -- How data flows between stages
    data_mapping JSONB NOT NULL,
    
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);
```

### Dynamic Triggers

```sql
-- Schema-aware scoring trigger
CREATE OR REPLACE FUNCTION calculate_dynamic_scores()
RETURNS TRIGGER AS $$
DECLARE
    schema_config JSONB;
    scoring_engine VARCHAR(100);
    scoring_result JSONB;
BEGIN
    -- Get schema configuration
    SELECT cs.scoring_configuration INTO schema_config
    FROM curation_schemas cs
    JOIN workflow_pairs wp ON wp.curation_schema_id = cs.id
    WHERE wp.id = NEW.workflow_pair_id;
    
    -- Extract scoring engine
    scoring_engine := schema_config->>'engine';
    
    -- Call appropriate scoring function
    CASE scoring_engine
        WHEN 'clingen_sop_v11' THEN
            scoring_result := calculate_clingen_scores(NEW.curation_data, schema_config);
        WHEN 'gencc_based' THEN
            scoring_result := calculate_gencc_scores(NEW.curation_data, schema_config);
        WHEN 'qualitative_assessment' THEN
            scoring_result := calculate_qualitative_scores(NEW.curation_data, schema_config);
        ELSE
            RAISE EXCEPTION 'Unknown scoring engine: %', scoring_engine;
    END CASE;
    
    -- Update computed fields
    NEW.computed_scores := scoring_result->'scores';
    NEW.computed_verdict := scoring_result->>'verdict';
    NEW.computed_summary := scoring_result->>'summary';
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_scores
    BEFORE INSERT OR UPDATE ON curations
    FOR EACH ROW
    EXECUTE FUNCTION calculate_dynamic_scores();
```

## API Architecture

### Schema Management Endpoints

```python
# Schema CRUD operations
POST   /api/v1/schemas                    # Create new schema
GET    /api/v1/schemas                    # List schemas (with filtering)
GET    /api/v1/schemas/{id}               # Get specific schema
PUT    /api/v1/schemas/{id}               # Update schema
DELETE /api/v1/schemas/{id}               # Delete schema

# Schema pairing
POST   /api/v1/workflow-pairs             # Create schema pair
GET    /api/v1/workflow-pairs             # List workflow pairs
GET    /api/v1/workflow-pairs/{id}        # Get specific pair

# User preferences
GET    /api/v1/users/me/default-schemas   # Get user's default schemas
POST   /api/v1/users/me/default-schemas   # Set default schemas

# Scoring engines
GET    /api/v1/scoring/engines            # List available engines
POST   /api/v1/scoring/calculate          # Calculate scores
POST   /api/v1/scoring/validate           # Validate evidence
```

### Dynamic Curation Endpoints

```python
# Flexible curation operations
POST   /api/v1/curations                  # Create curation (any schema)
GET    /api/v1/curations                  # List curations (multi-schema)
GET    /api/v1/curations/{id}             # Get curation with computed scores
PUT    /api/v1/curations/{id}/evidence    # Update evidence data
POST   /api/v1/curations/{id}/workflow    # Advance workflow state

# Schema-aware validation
POST   /api/v1/curations/validate-evidence  # Validate against schema
POST   /api/v1/curations/preview-scores     # Preview scoring results
```

## Frontend Architecture

### Schema-Driven Components

```vue
<!-- Dynamic form generation -->
<template>
  <div class="curation-form">
    <!-- Schema selection -->
    <SchemaSelector 
      v-model="selectedWorkflowPair"
      :available-pairs="availableWorkflowPairs"
    />
    
    <!-- Dynamic form based on selected schema -->
    <DynamicForm
      v-if="selectedWorkflowPair"
      :schema="currentSchema"
      v-model="evidenceData"
      @validate="validateEvidence"
      @score="calculateScores"
    />
    
    <!-- Real-time scoring display -->
    <ScoreCard
      v-if="currentScores"
      :scores="currentScores"
      :verdict="currentVerdict"
      :schema="currentSchema"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useSchemaStore } from '@/stores/schema'
import { useScoringService } from '@/services/scoring'

const schemaStore = useSchemaStore()
const scoringService = useScoringService()

const selectedWorkflowPair = ref(null)
const evidenceData = ref({})
const currentScores = ref(null)
const currentVerdict = ref('')

// Get schema definition
const currentSchema = computed(() => {
  return selectedWorkflowPair.value?.curation_schema
})

// Real-time scoring
watch(evidenceData, async (newData) => {
  if (currentSchema.value && Object.keys(newData).length > 0) {
    const result = await scoringService.calculateScores({
      evidence_data: newData,
      schema_config: currentSchema.value.scoring_configuration,
      engine_name: currentSchema.value.scoring_configuration.engine
    })
    
    currentScores.value = result.scores
    currentVerdict.value = result.verdict
  }
}, { deep: true })
</script>
```

## Example Schema Definitions

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
  }
}
```

### GenCC-Based Schema

```json
{
  "metadata": {
    "name": "GenCC_Classification",
    "version": "1.0.0",
    "type": "curation",
    "description": "GenCC-based gene-disease classification"
  },
  "field_definitions": {
    "clinical_evidence": {
      "type": "object",
      "properties": {
        "phenotype_overlap": {"type": "enum", "options": ["complete", "partial", "minimal"]},
        "inheritance_pattern": {"type": "enum", "options": ["consistent", "inconsistent"]},
        "population_data": {"type": "number", "min": 0, "max": 10}
      }
    }
  },
  "scoring_configuration": {
    "engine": "gencc_based",
    "verdicts": {
      "Definitive": {"conditions": [{"field": "confidence_score", "operator": ">=", "value": 8}]},
      "Strong": {"conditions": [{"field": "confidence_score", "operator": ">=", "value": 6}]},
      "Moderate": {"conditions": [{"field": "confidence_score", "operator": ">=", "value": 4}]}
    }
  }
}
```

### Custom Institutional Schema

```json
{
  "metadata": {
    "name": "Institution_Custom",
    "version": "1.0.0",
    "type": "curation",
    "description": "Custom institutional methodology"
  },
  "field_definitions": {
    "literature_review": {
      "type": "object",
      "properties": {
        "study_quality": {"type": "enum", "options": ["high", "medium", "low"]},
        "evidence_strength": {"type": "enum", "options": ["strong", "moderate", "weak"]},
        "consistency": {"type": "boolean"}
      }
    }
  },
  "scoring_configuration": {
    "engine": "qualitative_assessment",
    "verdicts": {
      "Strong Association": {"conditions": [{"field": "overall_assessment", "operator": "==", "value": "strong"}]},
      "Moderate Association": {"conditions": [{"field": "overall_assessment", "operator": "==", "value": "moderate"}]},
      "Weak Association": {"conditions": [{"field": "overall_assessment", "operator": "==", "value": "weak"}]}
    }
  }
}
```

## Migration from ClinGen-Centric Architecture

### Key Changes

1. **Database**: Replace fixed columns with flexible JSONB storage
2. **API**: Add schema management endpoints and dynamic validation
3. **Frontend**: Replace static forms with dynamic generation
4. **Scoring**: Convert ClinGen logic to pluggable engine

### ClinGen Compatibility

The existing ClinGen functionality is preserved as the default schema, ensuring no disruption to current users while enabling future flexibility.

## Performance Considerations

### Database Optimization

```sql
-- JSONB indexing for common queries
CREATE INDEX idx_curations_evidence_gin 
ON curations USING GIN (curation_data);

CREATE INDEX idx_curations_scores_gin 
ON curations USING GIN (computed_scores);

-- Schema-specific indexes
CREATE INDEX idx_curations_by_workflow_pair 
ON curations (workflow_pair_id);
```

### Caching Strategy

- Schema definitions cached at application level
- Scoring results cached for identical evidence sets
- UI components lazy-loaded based on schema requirements

## Security Considerations

### Schema Validation
- Comprehensive validation of schema definitions
- Prevention of malicious schema configurations
- Role-based access to schema creation/modification

### Data Integrity
- Content addressing with SHA-256 hashes
- Complete audit trail with user attribution
- Schema-aware data validation

This architecture transforms Gene Curator from a ClinGen-specific tool into a universal platform for gene-disease curation that can adapt to any scientific methodology through configuration rather than code changes.