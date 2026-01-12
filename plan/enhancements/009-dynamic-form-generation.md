# Enhancement: Dynamic UI Form Generation from Schemas

**Priority**: High
**Complexity**: High
**Estimated Effort**: 8-10 hours
**Status**: Backend ready (schema validator), frontend pending

## Overview

Implement dynamic form generation from schema definitions to support Gene Curator's schema-agnostic design. This is the **core of Gene Curator's value proposition** - supporting any curation methodology through configurable schemas without code changes.

## Current State (from PLAN.md)

✅ **Backend Ready**:
- Schema repository with 12+ field types
- Dynamic validation engine (`schema_validator.py`)
- JSON Schema generation endpoint

❌ **Frontend Pending**:
- Forms are hardcoded or incomplete
- Cannot render arbitrary schemas dynamically
- Violates schema-agnostic design principle

## Business Value

**Core Product Differentiator**: Gene Curator's ability to support ClinGen, GenCC, or institutional methodologies through configuration (not code) depends entirely on dynamic form generation.

**Without This Feature**:
- Cannot support new methodologies without frontend code changes
- Schema repository is useless (backend validates, but frontend can't render)
- Violates the fundamental architecture principle of schema-agnosticism

## Proposed Implementation

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend (Vue 3 + Vuetify)                          │
│ ┌─────────────────────────────────────────────────┐ │
│ │ DynamicForm Component                           │ │
│ │ - Loads schema from backend                     │ │
│ │ - Renders fields based on type                  │ │
│ │ - Validates using schema rules                  │ │
│ │ - Returns evidence_data as JSONB               │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────┘
                  │ GET /api/v1/schemas/{id}
┌─────────────────▼───────────────────────────────────┐
│ Backend (FastAPI)                                   │
│ - Returns schema definition with field types       │
│ - Validates evidence_data against schema           │
│ - Computes scores using scoring engine             │
└─────────────────────────────────────────────────────┘
```

### Schema Structure (from PLAN.md)

**Example Schema Definition**:

```json
{
  "id": 1,
  "name": "ClinGen SOP v11",
  "version": "11.0",
  "fields": [
    {
      "id": "genetic_evidence",
      "type": "section",
      "label": "Genetic Evidence",
      "description": "Case-level, segregation, and case-control data"
    },
    {
      "id": "case_level",
      "type": "evidence_table",
      "label": "Case-Level Data",
      "columns": [
        { "id": "variant", "type": "text", "label": "Variant", "required": true },
        { "id": "zygosity", "type": "select", "label": "Zygosity", "options": ["Het", "Hom", "Hemizygous"] },
        { "id": "phenotype", "type": "text", "label": "Phenotype" },
        { "id": "score", "type": "number", "label": "Score", "min": 0, "max": 12 }
      ],
      "scoring_weight": 1.0
    },
    {
      "id": "segregation",
      "type": "evidence_table",
      "label": "Segregation Data",
      "columns": [
        { "id": "family_id", "type": "text", "label": "Family ID" },
        { "id": "lod_score", "type": "number", "label": "LOD Score", "step": 0.01 }
      ],
      "scoring_weight": 1.5
    },
    {
      "id": "summary",
      "type": "textarea",
      "label": "Evidence Summary",
      "rows": 5,
      "required": true
    },
    {
      "id": "verdict",
      "type": "select",
      "label": "Verdict",
      "options": ["Definitive", "Strong", "Moderate", "Limited", "No Known Disease Relationship"],
      "readonly": true,
      "computed": true
    }
  ]
}
```

### Field Type Components

**1. Field Type Registry** (`frontend/src/components/fields/index.js`)

```javascript
// Map field types to Vue components
export const FIELD_COMPONENTS = {
  text: () => import('./TextField.vue'),
  textarea: () => import('./TextAreaField.vue'),
  number: () => import('./NumberField.vue'),
  select: () => import('./SelectField.vue'),
  multiselect: () => import('./MultiSelectField.vue'),
  checkbox: () => import('./CheckboxField.vue'),
  date: () => import('./DateField.vue'),
  url: () => import('./URLField.vue'),
  email: () => import('./EmailField.vue'),
  evidence_table: () => import('./EvidenceTable.vue'),
  reference: () => import('./ReferenceField.vue'),
  section: () => import('./SectionField.vue'),
  computed: () => import('./ComputedField.vue')
}

export function getFieldComponent(fieldType) {
  return FIELD_COMPONENTS[fieldType] || FIELD_COMPONENTS.text
}
```

**2. Base Field Component** (`frontend/src/components/fields/BaseField.vue`)

```vue
<template>
  <v-sheet class="field-wrapper" :class="{ required: field.required }">
    <label v-if="field.label" class="field-label">
      {{ field.label }}
      <span v-if="field.required" class="text-error">*</span>
    </label>

    <p v-if="field.description" class="text-caption text-medium-emphasis mb-2">
      {{ field.description }}
    </p>

    <slot :field="field" :modelValue="modelValue" :updateValue="updateValue" />

    <v-messages
      v-if="errorMessages.length"
      :messages="errorMessages"
      color="error"
      class="mt-1"
    />
  </v-sheet>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  field: {
    type: Object,
    required: true
  },
  modelValue: {
    type: [String, Number, Boolean, Array, Object],
    default: null
  },
  errors: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const errorMessages = computed(() => props.errors)

function updateValue(value) {
  emit('update:modelValue', value)
}
</script>
```

**3. Evidence Table Component** (`frontend/src/components/fields/EvidenceTable.vue`)

```vue
<template>
  <base-field :field="field" :modelValue="modelValue" :errors="errors">
    <template #default="{ updateValue }">
      <v-data-table
        :headers="tableHeaders"
        :items="rows"
        class="elevation-1"
      >
        <!-- Editable cells -->
        <template v-for="col in field.columns" :key="col.id" v-slot:[`item.${col.id}`]="{ item }">
          <component
            :is="getFieldComponent(col.type)"
            v-model="item[col.id]"
            :field="col"
            density="compact"
            hide-details
            @update:modelValue="updateValue(rows)"
          />
        </template>

        <!-- Actions column -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            @click="removeRow(item, updateValue)"
          />
        </template>

        <!-- Footer: Add row button -->
        <template v-slot:bottom>
          <v-btn
            prepend-icon="mdi-plus"
            variant="tonal"
            class="ma-2"
            @click="addRow(updateValue)"
          >
            Add Row
          </v-btn>
        </template>
      </v-data-table>
    </template>
  </base-field>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getFieldComponent } from './index'
import BaseField from './BaseField.vue'

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { type: Array, default: () => [] },
  errors: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

// Initialize rows from modelValue
const rows = ref(props.modelValue || [])

// Table headers from column definitions
const tableHeaders = computed(() => [
  ...props.field.columns.map(col => ({
    title: col.label,
    key: col.id,
    sortable: false
  })),
  { title: 'Actions', key: 'actions', sortable: false, width: 80 }
])

function addRow(updateValue) {
  const newRow = {}
  // Initialize with default values
  props.field.columns.forEach(col => {
    newRow[col.id] = col.default || null
  })
  rows.value.push(newRow)
  updateValue(rows.value)
}

function removeRow(item, updateValue) {
  const index = rows.value.indexOf(item)
  if (index > -1) {
    rows.value.splice(index, 1)
    updateValue(rows.value)
  }
}
</script>
```

**4. Dynamic Form Component** (`frontend/src/components/DynamicForm.vue`)

```vue
<template>
  <v-form ref="formRef">
    <v-row>
      <v-col
        v-for="field in schema.fields"
        :key="field.id"
        :cols="field.cols || 12"
      >
        <component
          :is="getFieldComponent(field.type)"
          v-model="formData[field.id]"
          :field="field"
          :errors="fieldErrors[field.id]"
          @update:modelValue="handleFieldUpdate(field.id, $event)"
        />
      </v-col>
    </v-row>
  </v-form>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { getFieldComponent } from './fields'

const props = defineProps({
  schema: {
    type: Object,
    required: true
  },
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'validate'])

// Form data (evidence_data)
const formData = reactive({ ...props.modelValue })

// Validation errors per field
const fieldErrors = ref({})

// Form ref for validation
const formRef = ref(null)

// Handle field updates
function handleFieldUpdate(fieldId, value) {
  formData[fieldId] = value
  emit('update:modelValue', formData)

  // Clear error for this field
  if (fieldErrors.value[fieldId]) {
    delete fieldErrors.value[fieldId]
  }
}

// Validate form against schema
async function validate() {
  const errors = {}

  // Validate each field
  for (const field of props.schema.fields) {
    const value = formData[field.id]

    // Required validation
    if (field.required && (value === null || value === undefined || value === '')) {
      errors[field.id] = [`${field.label} is required`]
    }

    // Type-specific validation
    if (field.type === 'number') {
      if (field.min !== undefined && value < field.min) {
        errors[field.id] = errors[field.id] || []
        errors[field.id].push(`Must be at least ${field.min}`)
      }
      if (field.max !== undefined && value > field.max) {
        errors[field.id] = errors[field.id] || []
        errors[field.id].push(`Must be at most ${field.max}`)
      }
    }

    // Pattern validation
    if (field.pattern && value) {
      const regex = new RegExp(field.pattern)
      if (!regex.test(value)) {
        errors[field.id] = errors[field.id] || []
        errors[field.id].push(field.pattern_error || 'Invalid format')
      }
    }
  }

  fieldErrors.value = errors
  const isValid = Object.keys(errors).length === 0

  emit('validate', { valid: isValid, errors })
  return isValid
}

// Watch for external modelValue changes
watch(() => props.modelValue, (newValue) => {
  Object.assign(formData, newValue)
}, { deep: true })

// Expose validate method
defineExpose({ validate })
</script>
```

**5. Curation Form Using Dynamic Form** (`frontend/src/views/CurationForm.vue`)

```vue
<template>
  <v-container>
    <v-card>
      <v-card-title>
        Curate Gene: {{ gene?.symbol }}
        <v-chip class="ml-2" size="small">{{ schema?.name }}</v-chip>
      </v-card-title>

      <v-card-text>
        <!-- Loading state -->
        <v-progress-circular v-if="loading" indeterminate />

        <!-- Dynamic form -->
        <dynamic-form
          v-else
          ref="dynamicFormRef"
          v-model="curation.evidence_data"
          :schema="schema"
          @validate="handleValidation"
        />
      </v-card-text>

      <v-card-actions>
        <v-btn
          color="primary"
          :loading="saving"
          @click="saveDraft"
        >
          Save Draft
        </v-btn>

        <v-btn
          color="success"
          :disabled="!canSubmit"
          :loading="submitting"
          @click="submitCuration"
        >
          Submit for Review
        </v-btn>

        <v-spacer />

        <v-btn @click="cancel">Cancel</v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DynamicForm from '@/components/DynamicForm.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useCurationsStore } from '@/stores/curations'
import { useGenesStore } from '@/stores/genes'

const route = useRoute()
const router = useRouter()

const schemasStore = useSchemasStore()
const curationsStore = useCurationsStore()
const genesStore = useGenesStore()

const loading = ref(true)
const saving = ref(false)
const submitting = ref(false)

const gene = ref(null)
const schema = ref(null)
const curation = ref({
  gene_id: null,
  scope_id: null,
  schema_id: null,
  status: 'draft',
  evidence_data: {}
})

const dynamicFormRef = ref(null)
const validationErrors = ref({})

const canSubmit = computed(() => {
  return Object.keys(validationErrors.value).length === 0
})

async function saveDraft() {
  saving.value = true
  try {
    if (curation.value.id) {
      await curationsStore.updateCuration(curation.value.id, curation.value)
    } else {
      const created = await curationsStore.createCuration(curation.value)
      curation.value.id = created.id
    }
  } finally {
    saving.value = false
  }
}

async function submitCuration() {
  // Validate form
  const isValid = await dynamicFormRef.value.validate()
  if (!isValid) return

  submitting.value = true
  try {
    curation.value.status = 'submitted'
    await curationsStore.updateCuration(curation.value.id, curation.value)
    router.push('/curations')
  } finally {
    submitting.value = false
  }
}

function handleValidation({ valid, errors }) {
  validationErrors.value = errors
}

onMounted(async () => {
  loading.value = true
  try {
    // Load gene
    const geneId = route.params.geneId
    gene.value = await genesStore.fetchGeneById(geneId)

    // Load schema (from scope or query param)
    const schemaId = route.query.schemaId
    schema.value = await schemasStore.fetchSchemaById(schemaId)

    // Initialize curation
    curation.value.gene_id = geneId
    curation.value.scope_id = route.query.scopeId
    curation.value.schema_id = schemaId
  } finally {
    loading.value = false
  }
})
</script>
```

## Implementation Steps

1. **Create field type components** (12+ components, ~100 lines each)
   - TextField, TextAreaField, NumberField
   - SelectField, MultiSelectField
   - DateField, CheckboxField
   - URLField, EmailField
   - **EvidenceTable** (complex, ~200 lines)
   - ReferenceField (PMID lookup)
   - SectionField (grouping)
   - ComputedField (read-only, calculated)

2. **Create BaseField wrapper** (~80 lines)
   - Consistent label/description rendering
   - Error message display
   - Required field indicator

3. **Create DynamicForm component** (~150 lines)
   - Load schema from backend
   - Render fields dynamically
   - Validate against schema rules
   - Emit evidence_data as JSONB

4. **Update CurationForm view** (~50 lines changed)
   - Replace hardcoded fields with DynamicForm
   - Handle validation from DynamicForm

5. **Add schema preview** (optional, ~100 lines)
   - Admin view to preview schema rendering
   - Test fields without creating curations

6. **Update CLAUDE.md**
   ```markdown
   ## Dynamic Forms

   All curation forms use DynamicForm component.
   Field types registered in `frontend/src/components/fields/index.js`.
   Schema defines what fields render, no code changes needed for new methodologies.
   ```

## Benefits

- **Schema-Agnostic Design**: Core value proposition realized
- **Zero Code for New Methodologies**: Add ClinGen, GenCC, or custom schemas without frontend changes
- **Consistent UX**: All forms follow same patterns
- **Validation**: Rules defined in schema, enforced client-side and server-side
- **Maintainability**: One set of field components, reused everywhere

## Testing

```javascript
// tests/unit/DynamicForm.test.js
describe('DynamicForm', () => {
  it('should render fields from schema', () => {
    const schema = {
      fields: [
        { id: 'title', type: 'text', label: 'Title', required: true },
        { id: 'score', type: 'number', label: 'Score', min: 0, max: 10 }
      ]
    }

    const wrapper = mount(DynamicForm, { props: { schema } })
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="number"]').exists()).toBe(true)
  })

  it('should validate required fields', async () => {
    const schema = {
      fields: [
        { id: 'title', type: 'text', label: 'Title', required: true }
      ]
    }

    const wrapper = mount(DynamicForm, { props: { schema } })
    const isValid = await wrapper.vm.validate()

    expect(isValid).toBe(false)
    expect(wrapper.vm.fieldErrors.title).toContain('Title is required')
  })

  it('should emit evidence_data on field changes', async () => {
    const schema = {
      fields: [
        { id: 'title', type: 'text', label: 'Title' }
      ]
    }

    const wrapper = mount(DynamicForm, { props: { schema } })
    await wrapper.find('input').setValue('Test Title')

    expect(wrapper.emitted('update:modelValue')[0][0]).toEqual({
      title: 'Test Title'
    })
  })
})
```

## Dependencies

- Vuetify 3 components (already in project)
- No new dependencies required

## Acceptance Criteria

- [ ] 12+ field type components implemented
- [ ] BaseField wrapper for consistent rendering
- [ ] DynamicForm component renders any schema
- [ ] CurationForm uses DynamicForm (no hardcoded fields)
- [ ] EvidenceTable component supports nested data entry
- [ ] Client-side validation from schema rules
- [ ] Error messages displayed per field
- [ ] Schema preview page for admins (optional)
- [ ] Unit tests for DynamicForm validation
- [ ] Integration test: Create curation with ClinGen schema
- [ ] Integration test: Create curation with GenCC schema

---

**Impact**: This is the **core feature** that makes Gene Curator schema-agnostic. Without this, the entire architecture principle collapses. High complexity but **essential** for product differentiation.
