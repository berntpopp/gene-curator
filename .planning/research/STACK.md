# STACK.md - Dynamic Forms Integration

**Project:** Gene Curator - Dynamic Form Integration
**Researched:** 2026-01-22
**Confidence:** HIGH (verified against existing codebase)

## Executive Summary

The existing stack (Vue 3.4 + Vuetify 3.9 + Pinia 2.1 + VueUse 14.1) provides everything needed for dynamic schema-driven forms. No new dependencies required. The `DynamicForm` and `DynamicField` components are 70-80% complete and already integrate with the backend JSON Schema generation API.

**Key finding:** The infrastructure is in place. The work is wiring, not building.

---

## Existing Stack (Keep As-Is)

| Technology | Version | Status | Purpose |
|------------|---------|--------|---------|
| Vue 3 | ^3.4.21 | Current | Core framework |
| Vuetify 3 | ^3.9.3 | Current | UI component library |
| Pinia | ^2.1.7 | Current | State management |
| VueUse | ^14.1.0 | Current | Composition utilities (debounce, etc.) |
| Axios | ^1.13.2 | Current | HTTP client |
| Vue Router | ^4.3.0 | Current | Routing |

**Rationale:** All dependencies are recent (2024-2025 releases). No upgrades needed.

---

## Vuetify 3 Components for Dynamic Forms

### Core Form Components (Already Used)

| Component | Purpose | Current Usage |
|-----------|---------|---------------|
| `v-form` | Form wrapper with validation | DynamicForm.vue, all form views |
| `v-text-field` | Text/number/date input | DynamicField.vue |
| `v-textarea` | Multiline text | DynamicField.vue |
| `v-select` | Single select dropdown | DynamicField.vue |
| `v-checkbox` | Boolean toggle | DynamicField.vue |
| `v-card` | Section containers | All form layouts |
| `v-row` / `v-col` | Grid layout | Form field positioning |

### Tab Components (For Dynamic Sections)

| Component | Purpose | Recommendation |
|-----------|---------|----------------|
| `v-tabs` | Tab navigation | Use for schema-defined sections |
| `v-tab` | Individual tab | Render from `ui_configuration.sections` |
| `v-window` | Tab content container | Wrap section content |
| `v-window-item` | Individual tab panel | One per schema section |

**Pattern for Dynamic Tabs:**

```vue
<v-tabs v-model="activeTab">
  <v-tab
    v-for="section in schema.ui_configuration.sections"
    :key="section.id"
    :value="section.id"
  >
    <v-icon start>{{ section.icon }}</v-icon>
    {{ section.label }}
  </v-tab>
</v-tabs>

<v-window v-model="activeTab">
  <v-window-item
    v-for="section in schema.ui_configuration.sections"
    :key="section.id"
    :value="section.id"
  >
    <DynamicForm
      :schema-id="schemaId"
      :fields="section.fields"
      :form-data="formData"
      @update="handleFieldUpdate"
    />
  </v-window-item>
</v-window>
```

**Source:** ClinGenCurationForm.vue already implements this pattern with hardcoded tabs.

### Additional Input Components (As Needed)

| Component | Use Case | Notes |
|-----------|----------|-------|
| `v-autocomplete` | External lookups (HGNC, MONDO) | Already used in evidence components |
| `v-combobox` | Free-form with suggestions | For PMIDs, gene symbols |
| `v-radio-group` | Exclusive options | For curation type selection |
| `v-chip-group` | Multi-select tags | For rationale criteria |
| `v-expansion-panels` | Collapsible sections | Alternative to tabs for long forms |
| `v-slider` | Numeric ranges | Score adjustments |

---

## Vue 3 Composition API Patterns

### Dynamic Component Rendering

**Pattern 1: Conditional Field Types**

```javascript
// DynamicField.vue - Already implemented
const fieldComponent = computed(() => {
  const typeMap = {
    'string': 'v-text-field',
    'number': 'v-text-field',
    'boolean': 'v-checkbox',
    'select': 'v-select',
    'multiselect': 'v-select',
    'array': 'ArrayField',
    'object': 'ObjectField'
  }
  return typeMap[props.fieldSchema.type] || 'v-text-field'
})
```

**Pattern 2: Dynamic Validation Rules**

```javascript
// Already in DynamicField.vue
const getValidationRules = () => {
  const rules = []

  if (props.fieldSchema.required) {
    rules.push(v => !!v || `${label.value} is required`)
  }

  if (props.fieldSchema.minLength) {
    rules.push(v => (v?.length >= props.fieldSchema.minLength) ||
      `Minimum ${props.fieldSchema.minLength} characters`)
  }

  if (props.fieldSchema.maximum !== undefined) {
    rules.push(v => (v <= props.fieldSchema.maximum) ||
      `Maximum value is ${props.fieldSchema.maximum}`)
  }

  return rules
}
```

### Debounced Validation with VueUse

**Pattern: watchDebounced for Live Scoring**

```javascript
import { watchDebounced } from '@vueuse/core'

// Debounce validation to avoid excessive API calls
watchDebounced(
  formData,
  async (newData) => {
    await validationStore.validateEvidence(newData, props.schemaId, 'form')
  },
  { debounce: 500, maxWait: 2000, deep: true }
)
```

**Source:** Already using `useDebounceFn` in MONDOAutocomplete.vue and OMIMAutocomplete.vue.

### Computed Properties for Dynamic Field Layout

```javascript
// Determine column width based on field configuration
const getFieldCols = computed(() => (field) => {
  // From ui_configuration or sensible defaults
  if (field.ui?.cols) return field.ui.cols

  switch (field.type) {
    case 'boolean': return 12
    case 'array':
    case 'object': return 12
    case 'text':
      return field.multiline ? 12 : 6
    default: return 6
  }
})
```

---

## Form Validation Approach

### Use Vuetify Native Validation (No VeeValidate Needed)

**Rationale:**
1. DynamicField.vue already uses `:rules` prop pattern
2. Backend validation via `/validation/validate-evidence` provides comprehensive checks
3. VeeValidate adds complexity without benefit for this use case

**Pattern: Two-Layer Validation**

```javascript
// Layer 1: Vuetify instant feedback (client-side)
const clientRules = getValidationRules()

// Layer 2: Backend comprehensive validation (debounced)
watchDebounced(formData, async () => {
  const result = await validationStore.validateEvidence(
    formData.value,
    schemaId,
    'form'
  )
  // Merge backend errors into field states
  applyBackendValidation(result)
}, { debounce: 500 })
```

**Backend validation provides:**
- Cross-field validation rules
- Business rule enforcement (ClinGen score limits, etc.)
- Live score calculations
- Completeness scoring
- Improvement suggestions

**Already Implemented:**
- `validationStore.validateEvidence()` - calls `/validation/validate-evidence`
- `validationStore.generateJsonSchema()` - calls `/validation/schema/{id}/json-schema`
- `SchemaValidationResult` includes `score_calculations` for live scoring

---

## Live Score Calculation

### Backend-Driven (Recommended)

```javascript
// Already in DynamicForm.vue - line 68-92
<div v-if="validationResult && validationResult.score_calculations">
  <v-row>
    <v-col
      v-for="(score, category) in validationResult.score_calculations"
      :key="category"
    >
      <v-card variant="outlined">
        <v-card-text class="text-center">
          <div class="text-h4 text-primary">{{ score }}</div>
          <div class="text-caption">{{ formatScoreCategory(category) }}</div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</div>
```

**Flow:**
1. User edits field
2. Debounced watch triggers validation
3. Backend calculates scores based on scoring_configuration
4. `score_calculations` returned in validation response
5. UI displays scores

**ClinGen-specific scoring** is already implemented in:
- `backend/app/core/schema_validator.py` - `_calculate_clingen_scores()`
- `frontend/src/components/clingen/ClinGenCurationForm.vue` - `calculateGeneticScore()`

---

## NOT Recommended

### Libraries to Avoid

| Library | Reason |
|---------|--------|
| VeeValidate | Overkill - Vuetify native validation + backend validation sufficient |
| vue3-schema-forms | External dependency with own opinions; existing DynamicForm already does this |
| @koumoul/vjsf | Same - adds dependency when existing code covers 80% |
| FormKit | Heavy; not needed for this use case |
| JSON Schema form libraries | The backend already generates compatible JSON Schema |

### Patterns to Avoid

| Anti-Pattern | Why | Do Instead |
|--------------|-----|------------|
| Client-only validation | Backend has business rules, scores | Use backend as source of truth |
| defineExpose for validation | Couples parent/child tightly | Event-driven pattern (already used) |
| Hardcoded field types | Prevents schema flexibility | Map field types dynamically |
| Synchronous validation | Blocks UI on complex rules | Debounced async validation |

---

## Integration Notes

### Connecting DynamicForm to Views

**Current State:**
- `DynamicForm.vue` exists and works
- `DynamicField.vue` handles 6+ field types
- `SchemaDrivenCurationForm.vue` integrates DynamicForm for non-ClinGen schemas
- `CurationFormView.vue` resolves schema and renders SchemaDrivenCurationForm

**Gap to Close:**
- PrecurationFormView.vue is hardcoded (doesn't use DynamicForm)
- ClinGenCurationForm.vue is hardcoded (acceptable for specialized UI)
- Tab rendering is not driven by `ui_configuration.sections`

### Schema UI Configuration Structure

Backend schemas should include:

```json
{
  "ui_configuration": {
    "sections": [
      {
        "id": "disease",
        "label": "Disease Entity",
        "icon": "mdi-medical-bag",
        "fields": ["disease_name", "mondo_id", "mode_of_inheritance"]
      },
      {
        "id": "evidence",
        "label": "Evidence",
        "icon": "mdi-chart-line",
        "fields": ["evidence_strength", "recommendation"]
      }
    ],
    "layout": "tabs"  // or "panels", "wizard"
  }
}
```

### Validation Store Integration

Already connected:

```javascript
// stores/validation.js
async generateJsonSchema(schemaId) {
  const jsonSchema = await validationAPI.generateJsonSchema(schemaId)
  this.jsonSchemas[schemaId] = jsonSchema
  return jsonSchema
}

async validateEvidence(evidenceData, schemaId, key) {
  const result = await validationAPI.validateEvidence({
    evidence_data: evidenceData,
    schema_id: schemaId
  })
  this.validationResults[key] = result
  return result
}
```

### Component Wiring Summary

```
CurationFormView.vue
    |
    v
SchemaDrivenCurationForm.vue
    |
    +-- ClinGenCurationForm.vue (if ClinGen schema)
    |       |
    |       +-- [Hardcoded specialized tabs]
    |
    +-- DynamicForm.vue (for other schemas)
            |
            +-- DynamicField.vue (per field)
```

**Target State:**

```
CurationFormView.vue
    |
    v
SchemaDrivenCurationForm.vue
    |
    +-- DynamicTabs.vue (render from ui_configuration)
            |
            +-- DynamicForm.vue (per section)
                    |
                    +-- DynamicField.vue (per field)
```

---

## Sources

- Existing codebase analysis (HIGH confidence)
- [Vuetify 3 Form Documentation](https://vuetifyjs.com/en/components/forms/)
- [VueUse watchDebounced](https://vueuse.org/shared/watchdebounced/)
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
