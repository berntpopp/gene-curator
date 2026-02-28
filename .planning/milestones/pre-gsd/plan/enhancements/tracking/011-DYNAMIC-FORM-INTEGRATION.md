# Enhancement #011: Wire DynamicForm to CurationFormView

**Status**: Ready for Implementation
**Priority**: CRITICAL - Unblocks schema-agnostic architecture
**Estimated Effort**: 4-6 hours
**Created**: 2026-01-12
**Last Reviewed**: 2026-01-12 (Code Review Applied)
**Closes Issues**: #62, #61, #77

---

## Executive Summary

The DynamicForm component already exists and works (`frontend/src/components/dynamic/DynamicForm.vue`), but it's **NOT wired** to the curation workflow. The current `CurationForm.vue` is hardcoded for ClinGen SOP v11 with manual tabs for Genetic/Experimental/Contradictory evidence.

This enhancement replaces the hardcoded form with the schema-driven DynamicForm, enabling Gene Curator's core value proposition: **any curation methodology through configuration, not code**.

---

## Current State Analysis

### What Exists (Ready to Use)

| Component | Location | Status |
|-----------|----------|--------|
| DynamicForm | `frontend/src/components/dynamic/DynamicForm.vue` | Complete |
| DynamicField | `frontend/src/components/dynamic/DynamicField.vue` | Complete (8+ field types) |
| SchemaSelector | `frontend/src/components/dynamic/SchemaSelector.vue` | Complete (workflow pairs) |
| Schemas Store | `frontend/src/stores/schemas.js` | Complete |
| Validation Store | `frontend/src/stores/validation.js` | Complete |
| JSON Schema Generator | `GET /validation/generate-json-schema/{id}` | Backend ready |

### What's Broken

| Component | Issue |
|-----------|-------|
| `CurationForm.vue` | Hardcoded ClinGen SOP v11 tabs (lines 62-204) |
| `CurationFormView.vue` | Doesn't pass schemaId to CurationForm |
| Schema Selection | No single-schema selector for curation flow |
| Workflow Integration | workflow_pair_id not used to determine schema |

---

## Architecture Design

### Principle: Single Source of Truth

```
Workflow Pair (DB)
    ├── precuration_schema_id
    └── curation_schema_id
           ↓
    Schema Definition (DB)
           ↓
    JSON Schema (generated)
           ↓
    DynamicForm (renders)
           ↓
    evidence_data (JSONB)
```

### Component Hierarchy (Refactored)

```
CurationFormView.vue (router view)
    │
    ├── CurationSchemaSelect.vue (new - single schema selector)
    │
    └── SchemaDrivenCurationForm.vue (new wrapper)
            │
            ├── [inline header] (gene info, status - kept inline per KISS)
            │
            ├── DynamicForm.vue (existing - schema-driven fields)
            │
            ├── ScorePreview.vue (existing - live scoring)
            │
            └── FormActions.vue (extracted - reusable for Precuration)
```

---

## Implementation Plan

### Phase 1: Create Schema-Driven Form Wrapper (2h)

**File**: `frontend/src/components/forms/SchemaDrivenCurationForm.vue`

**Responsibilities** (Single Responsibility Principle):
1. Load curation schema from workflow pair or direct schemaId
2. Pass schemaId to DynamicForm
3. Handle form state (loading, saving, error)
4. Manage evidence_data binding via v-model events
5. Integrate existing composables (formRecovery, history, timeout)
6. Handle keyboard shortcuts (migrated from CurationForm)

**Implementation**:

```vue
<template>
  <ErrorBoundary @error="handleFormError">
    <v-form ref="formRef" @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card>
        <!-- Header: Kept inline per KISS principle (too small to extract) -->
        <v-card-title class="d-flex align-center">
          <span>{{ gene?.symbol }} - {{ schema?.name || 'Curation' }}</span>
          <v-chip v-if="isDraft" color="warning" size="small" class="ml-2">
            Draft
          </v-chip>
          <v-spacer />
          <v-chip v-if="lastSaved" color="success" size="small" variant="outlined">
            <v-icon start size="small">mdi-content-save</v-icon>
            Saved {{ formatRelativeTime(lastSaved) }}
          </v-chip>
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-row>
            <!-- Main: Dynamic Form -->
            <v-col cols="12" lg="8">
              <v-skeleton-loader v-if="loadingSchema" type="article" />

              <DynamicForm
                v-else-if="schemaId"
                :schema-id="schemaId"
                :initial-data="evidenceData"
                :title="schema?.name || 'Curation Form'"
                :readonly="readonly"
                @update:model-value="handleEvidenceChange"
                @validation-change="handleValidationChange"
                @submit="handleSubmit"
                @save-draft="handleSaveDraft"
              />

              <v-alert v-else type="warning" variant="tonal">
                <template #prepend>
                  <v-icon>mdi-alert</v-icon>
                </template>
                No schema assigned to this curation. Please contact an administrator.
              </v-alert>
            </v-col>

            <!-- Sidebar: Live Scoring -->
            <v-col cols="12" lg="4">
              <div class="sticky-sidebar">
                <ScorePreview
                  :evidence-data="evidenceData"
                  :schema-id="schemaId"
                />
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider />

        <!-- Actions: Extracted for reuse with PrecurationForm -->
        <FormActions
          :can-undo="canUndo"
          :can-redo="canRedo"
          :can-submit="canSubmit"
          :saving="savingDraft"
          :submitting="submitting"
          @undo="undo"
          @redo="redo"
          @save-draft="handleSaveDraft"
          @submit="handleSubmit"
          @cancel="handleCancel"
        />
      </v-card>
    </v-form>

    <!-- Form Recovery Dialog -->
    <FormRecoveryDialog
      v-model="showRecoveryDialog"
      :recovery-data="recoveryData"
      @restore="restoreRecovery"
      @discard="discardRecovery"
    />
  </ErrorBoundary>
</template>

<script setup>
/**
 * SchemaDrivenCurationForm
 *
 * Schema-agnostic curation form that renders fields dynamically based on
 * the assigned curation schema. Replaces the hardcoded CurationForm.
 *
 * Key Features:
 * - Renders any schema (ClinGen, GenCC, custom)
 * - Integrates form recovery, undo/redo, session timeout
 * - Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Enter, Esc)
 * - Event-driven validation (no defineExpose)
 */

import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useSchemasStore } from '@/stores/schemas'
import { useCurationsStore } from '@/stores/curations'
import { useValidationStore } from '@/stores/validation'
import { useNotificationsStore } from '@/stores/notifications'
import { useFormRecovery } from '@/composables/useFormRecovery'
import { useHistory } from '@/composables/useHistory'
import { useLogger } from '@/composables/useLogger'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import FormRecoveryDialog from '@/components/FormRecoveryDialog.vue'
import DynamicForm from '@/components/dynamic/DynamicForm.vue'
import ScorePreview from '@/components/evidence/ScorePreview.vue'
import FormActions from '@/components/forms/FormActions.vue'

const props = defineProps({
  schemaId: {
    type: String,
    required: true
  },
  curationId: {
    type: String,
    default: null
  },
  scopeId: {
    type: String,
    required: true
  },
  geneId: {
    type: String,
    default: null
  },
  gene: {
    type: Object,
    default: null
  },
  readonly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['submit', 'cancel', 'saved'])

const logger = useLogger()
const router = useRouter()
const schemasStore = useSchemasStore()
const curationsStore = useCurationsStore()
const validationStore = useValidationStore()
const notificationsStore = useNotificationsStore()

// Form state
const formRef = ref(null)
const evidenceData = ref({})
const isDraft = ref(true)
const loadingSchema = ref(false)
const savingDraft = ref(false)
const submitting = ref(false)
const isValid = ref(true) // Updated via validation-change event
const lockVersion = ref(0)

// Schema data
const schema = computed(() => schemasStore.getSchemaById(props.schemaId))

// Form Recovery - schema-aware key to prevent cross-schema data restore
const recoveryKey = computed(() =>
  `curation-${props.curationId || 'new'}-schema-${props.schemaId}`
)

const {
  showRecoveryDialog,
  recoveryData,
  lastSaved,
  restoreRecovery,
  discardRecovery,
  clearRecovery
} = useFormRecovery(recoveryKey.value, evidenceData, {
  saveInterval: 5000,
  maxAge: 24 * 60 * 60 * 1000
})

// Clear recovery when schema changes (prevents invalid data restore)
watch(() => props.schemaId, (newId, oldId) => {
  if (oldId && newId !== oldId) {
    clearRecovery()
    evidenceData.value = {}
    logger.info('Schema changed, cleared form recovery', { oldId, newId })
  }
})

// Undo/Redo
const {
  canUndo,
  canRedo,
  recordAction,
  undo: undoAction,
  redo: redoAction,
  clearHistory
} = useHistory(recoveryKey.value, state => {
  evidenceData.value = { ...state }
})

// Track changes for undo/redo
watch(evidenceData, (newVal, oldVal) => {
  if (oldVal && Object.keys(oldVal).length > 0) {
    recordAction('edit', oldVal, { ...newVal })
  }
}, { deep: true })

// Submit eligibility
const canSubmit = computed(() => isValid.value && !props.readonly)

/**
 * Handle evidence data changes from DynamicForm
 */
function handleEvidenceChange(newData) {
  evidenceData.value = newData
}

/**
 * Handle validation state changes from DynamicForm
 * Event-driven pattern instead of defineExpose
 */
function handleValidationChange(validationResult) {
  isValid.value = validationResult?.is_valid !== false
}

/**
 * Handle form-level errors from ErrorBoundary
 */
function handleFormError(error) {
  logger.error('Form rendering failed', {
    error: error.message,
    schemaId: props.schemaId,
    curationId: props.curationId
  })
  notificationsStore.addToast('Form failed to render. Please try refreshing.', 'error')
}

/**
 * Keyboard shortcuts - migrated from CurationForm
 */
function handleKeydown(event) {
  const ctrl = event.ctrlKey || event.metaKey

  if (ctrl && event.key === 's') {
    event.preventDefault()
    handleSaveDraft()
  } else if (ctrl && event.key === 'Enter') {
    event.preventDefault()
    if (canSubmit.value) handleSubmit()
  } else if (ctrl && event.key === 'z' && !event.shiftKey) {
    event.preventDefault()
    if (canUndo.value) undo()
  } else if (ctrl && event.key === 'z' && event.shiftKey) {
    event.preventDefault()
    if (canRedo.value) redo()
  } else if (event.key === 'Escape') {
    handleCancel()
  }
}

/**
 * Undo/Redo actions
 */
function undo() {
  undoAction()
  logger.debug('Undo performed')
}

function redo() {
  redoAction()
  logger.debug('Redo performed')
}

/**
 * Save draft
 */
async function handleSaveDraft() {
  savingDraft.value = true
  try {
    const payload = {
      evidence_data: evidenceData.value,
      lock_version: lockVersion.value
    }

    if (props.curationId) {
      const updated = await curationsStore.saveDraft(props.curationId, payload)
      if (updated) {
        lockVersion.value = updated.lock_version
        emit('saved')
      }
    } else {
      // Create new curation as draft
      const created = await curationsStore.createCuration({
        gene_id: props.geneId,
        scope_id: props.scopeId,
        curation_schema_id: props.schemaId,
        evidence_data: evidenceData.value
      })
      // Navigate to edit the created curation
      router.replace({
        name: 'curation-edit',
        params: { scopeId: props.scopeId, curationId: created.id }
      })
    }

    notificationsStore.addToast('Draft saved', 'success')
    clearRecovery()
  } catch (error) {
    logger.error('Failed to save draft', { error: error.message })
    notificationsStore.addToast('Failed to save draft', 'error')
  } finally {
    savingDraft.value = false
  }
}

/**
 * Submit curation
 */
async function handleSubmit() {
  if (!canSubmit.value) return

  submitting.value = true
  try {
    if (props.curationId) {
      await curationsStore.submitCuration(props.curationId, {
        lock_version: lockVersion.value
      })
    } else {
      // Create and submit
      const created = await curationsStore.createCuration({
        gene_id: props.geneId,
        scope_id: props.scopeId,
        curation_schema_id: props.schemaId,
        evidence_data: evidenceData.value
      })
      await curationsStore.submitCuration(created.id, { lock_version: 0 })
    }

    notificationsStore.addToast('Curation submitted for review', 'success')
    clearRecovery()
    clearHistory()
    emit('submit')
  } catch (error) {
    logger.error('Failed to submit curation', { error: error.message })
    notificationsStore.addToast('Failed to submit curation', 'error')
  } finally {
    submitting.value = false
  }
}

/**
 * Cancel editing
 */
function handleCancel() {
  if (Object.keys(evidenceData.value).length > 0) {
    if (!confirm('Discard unsaved changes?')) return
  }
  clearRecovery()
  clearHistory()
  emit('cancel')
}

/**
 * Format relative time
 */
function formatRelativeTime(timestamp) {
  if (!timestamp) return ''
  const now = new Date()
  const then = new Date(timestamp)
  const diffSec = Math.floor((now - then) / 1000)

  if (diffSec < 60) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

/**
 * Load existing curation data
 */
async function loadCuration() {
  if (!props.curationId) return

  try {
    const curation = await curationsStore.fetchCurationById(props.curationId)
    if (curation) {
      evidenceData.value = curation.evidence_data || {}
      lockVersion.value = curation.lock_version || 0
      isDraft.value = curation.status === 'draft'
    }
  } catch (error) {
    logger.error('Failed to load curation', { error: error.message })
    notificationsStore.addToast('Failed to load curation', 'error')
  }
}

/**
 * Load schema
 */
async function loadSchema() {
  if (!props.schemaId) return

  loadingSchema.value = true
  try {
    await schemasStore.fetchSchemaById(props.schemaId)
    await validationStore.generateJsonSchema(props.schemaId)
  } catch (error) {
    logger.error('Failed to load schema', { error: error.message })
    notificationsStore.addToast('Failed to load curation schema', 'error')
  } finally {
    loadingSchema.value = false
  }
}

onMounted(async () => {
  await loadSchema()
  await loadCuration()
  logger.debug('SchemaDrivenCurationForm mounted', {
    schemaId: props.schemaId,
    curationId: props.curationId
  })
})

onBeforeUnmount(() => {
  logger.debug('SchemaDrivenCurationForm unmounted')
})
</script>

<style scoped>
.sticky-sidebar {
  position: sticky;
  top: 80px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}
</style>
```

**Key Design Decisions**:
- **DRY**: Reuses existing DynamicForm, composables, dialogs
- **KISS**: Header kept inline (too small to extract per review)
- **SOLID (Open/Closed)**: New schemas work without code changes
- **No defineExpose**: Uses `@validation-change` event pattern instead

---

### Phase 2: Update CurationFormView to Resolve Schema (1h)

**File**: `frontend/src/views/curation/CurationFormView.vue`

**Changes**:
1. Determine schemaId from multiple sources with clear priority
2. Load required data (gene, workflow pair)
3. Pass resolved schemaId to form component

**Implementation**:

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex align-center mb-6">
          <v-btn
            icon="mdi-arrow-left"
            variant="text"
            class="mr-3"
            aria-label="Go back"
            @click="handleCancel"
          />
          <h1 class="text-h4">
            {{ isEdit ? 'Edit Curation' : 'New Curation' }}
          </h1>
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <!-- Loading State -->
        <v-skeleton-loader v-if="loading" type="card" />

        <!-- Schema Selection (if not determined) -->
        <CurationSchemaSelect
          v-else-if="!resolvedSchemaId && availableSchemas.length > 1"
          v-model="selectedSchemaId"
          :scope-id="scopeId"
          @update:model-value="handleSchemaSelected"
        />

        <!-- Main Form -->
        <SchemaDrivenCurationForm
          v-else-if="resolvedSchemaId"
          :schema-id="resolvedSchemaId"
          :curation-id="curationId"
          :scope-id="scopeId"
          :gene-id="geneId"
          :gene="gene"
          @submit="handleSubmit"
          @cancel="handleCancel"
          @saved="handleSaved"
        />

        <!-- No Schema Available -->
        <v-alert v-else type="error" variant="tonal">
          <template #prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          <div class="font-weight-medium">No Curation Schema Available</div>
          <div class="text-body-2 mt-1">
            This scope does not have a curation schema configured.
            Please contact an administrator.
          </div>
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSchemasStore } from '@/stores/schemas'
import { useCurationsStore } from '@/stores/curations'
import { useGenesStore } from '@/stores/genes'
import { useNotificationsStore } from '@/stores/notifications'
import { useLogger } from '@/composables/useLogger'
import SchemaDrivenCurationForm from '@/components/forms/SchemaDrivenCurationForm.vue'
import CurationSchemaSelect from '@/components/forms/CurationSchemaSelect.vue'

const router = useRouter()
const route = useRoute()
const logger = useLogger()
const schemasStore = useSchemasStore()
const curationsStore = useCurationsStore()
const genesStore = useGenesStore()
const notificationsStore = useNotificationsStore()

// Route params
const scopeId = computed(() => route.params.scopeId)
const curationId = computed(() => route.params.curationId || null)
const geneId = computed(() => route.params.geneId || route.query.gene_id || null)

// State
const loading = ref(true)
const selectedSchemaId = ref(null)
const curation = ref(null)
const gene = ref(null)

// Determine if edit mode
const isEdit = computed(() => !!curationId.value)

// Available curation schemas for this scope
const availableSchemas = computed(() => schemasStore.getCurationSchemas)

// Schema resolution with clear priority chain
const resolvedSchemaId = computed(() => {
  // Priority 1: Existing curation has schema
  if (curation.value?.curation_schema_id) {
    return curation.value.curation_schema_id
  }

  // Priority 2: User selected schema
  if (selectedSchemaId.value) {
    return selectedSchemaId.value
  }

  // Priority 3: Route query param (admin override)
  if (route.query.schema_id) {
    return route.query.schema_id
  }

  // Priority 4: Workflow pair default for scope
  const workflowPair = schemasStore.workflowPairs.find(
    wp => wp.scope_id === scopeId.value
  )
  if (workflowPair?.curation_schema_id) {
    return workflowPair.curation_schema_id
  }

  // Priority 5: Only one schema available - use it
  if (availableSchemas.value.length === 1) {
    return availableSchemas.value[0].id
  }

  return null
})

function handleSchemaSelected(schemaId) {
  selectedSchemaId.value = schemaId
}

function handleSubmit(curationData) {
  notificationsStore.addToast('Curation submitted successfully', 'success')
  router.push({
    name: 'curation-detail',
    params: { scopeId: scopeId.value, curationId: curationData.id }
  })
}

function handleCancel() {
  router.back()
}

function handleSaved() {
  notificationsStore.addToast('Draft saved', 'info')
}

async function loadData() {
  loading.value = true
  try {
    // Load schemas and workflow pairs
    await Promise.all([
      schemasStore.fetchSchemas(),
      schemasStore.fetchWorkflowPairs()
    ])

    // Load existing curation if editing
    if (curationId.value) {
      curation.value = await curationsStore.fetchCurationById(curationId.value)
    }

    // Load gene info if available
    if (geneId.value) {
      gene.value = await genesStore.fetchGeneById(geneId.value)
    }
  } catch (error) {
    logger.error('Failed to load curation data', { error: error.message })
    notificationsStore.addToast('Failed to load data', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
```

---

### Phase 3: Create Single-Schema Selector Component (1h)

**File**: `frontend/src/components/forms/CurationSchemaSelect.vue`

> **Note**: Named `CurationSchemaSelect` to avoid conflict with existing `components/dynamic/SchemaSelector.vue` which handles workflow pairs (both schemas together).

**Purpose**: Allow selection of a single curation schema when multiple are available.

```vue
<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-file-document-outline</v-icon>
      Select Curation Methodology
    </v-card-title>

    <v-card-text>
      <v-select
        v-model="selectedSchemaId"
        :items="availableSchemas"
        :loading="loading"
        item-title="name"
        item-value="id"
        label="Curation Schema"
        placeholder="Choose curation methodology..."
        variant="outlined"
        :hint="selectedSchema?.description"
        persistent-hint
        @update:model-value="handleSelection"
      >
        <template #item="{ props: itemProps, item }">
          <v-list-item v-bind="itemProps">
            <template #subtitle>
              {{ item.raw.schema_type }} | v{{ item.raw.version }}
            </template>
            <template #append>
              <v-chip size="x-small" color="info" variant="flat">
                {{ getFieldCount(item.raw) }} fields
              </v-chip>
            </template>
          </v-list-item>
        </template>
      </v-select>

      <v-alert v-if="selectedSchema" type="info" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>mdi-information</v-icon>
        </template>
        <div class="font-weight-medium">{{ selectedSchema.name }}</div>
        <div class="text-body-2">{{ selectedSchema.description }}</div>
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!selectedSchemaId"
        @click="confirmSelection"
      >
        <v-icon start>mdi-arrow-right</v-icon>
        Continue
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSchemasStore } from '@/stores/schemas'

const props = defineProps({
  modelValue: {
    type: String,
    default: null
  },
  scopeId: {
    type: String,
    required: true
  },
  schemaType: {
    type: String,
    default: 'curation',
    validator: (v) => ['curation', 'precuration', 'combined'].includes(v)
  }
})

const emit = defineEmits(['update:modelValue'])

const schemasStore = useSchemasStore()
const selectedSchemaId = ref(props.modelValue)

const loading = computed(() => schemasStore.loading)

// Filter schemas by type
const availableSchemas = computed(() => {
  return schemasStore.schemas.filter(s =>
    s.schema_type === props.schemaType ||
    s.schema_type === 'combined'
  )
})

const selectedSchema = computed(() => {
  if (!selectedSchemaId.value) return null
  return availableSchemas.value.find(s => s.id === selectedSchemaId.value)
})

function getFieldCount(schema) {
  return schema.field_definitions?.length || 0
}

function handleSelection(schemaId) {
  selectedSchemaId.value = schemaId
}

function confirmSelection() {
  if (selectedSchemaId.value) {
    emit('update:modelValue', selectedSchemaId.value)
  }
}

onMounted(async () => {
  if (schemasStore.schemas.length === 0) {
    await schemasStore.fetchSchemas()
  }
})
</script>
```

---

### Phase 4: Create FormActions Component (30min)

**File**: `frontend/src/components/forms/FormActions.vue`

**Purpose**: Reusable action bar for both CurationForm and PrecurationForm.

```vue
<template>
  <v-card-actions class="px-4 py-3">
    <v-btn variant="outlined" @click="$emit('cancel')">
      <v-icon start>mdi-close</v-icon>
      Cancel
    </v-btn>

    <v-spacer />

    <!-- Undo/Redo -->
    <v-btn-group variant="outlined" density="compact" class="mr-2">
      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            :disabled="!canUndo"
            aria-label="Undo (Ctrl+Z)"
            @click="$emit('undo')"
          >
            <v-icon>mdi-undo</v-icon>
          </v-btn>
        </template>
        <span>Undo (Ctrl+Z)</span>
      </v-tooltip>

      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            :disabled="!canRedo"
            aria-label="Redo (Ctrl+Shift+Z)"
            @click="$emit('redo')"
          >
            <v-icon>mdi-redo</v-icon>
          </v-btn>
        </template>
        <span>Redo (Ctrl+Shift+Z)</span>
      </v-tooltip>
    </v-btn-group>

    <v-tooltip location="top">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          variant="outlined"
          :loading="saving"
          aria-label="Save Draft (Ctrl+S)"
          @click="$emit('save-draft')"
        >
          <v-icon start>mdi-content-save</v-icon>
          Save Draft
        </v-btn>
      </template>
      <span>Save Draft (Ctrl+S)</span>
    </v-tooltip>

    <v-tooltip location="top">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          color="primary"
          variant="flat"
          :loading="submitting"
          :disabled="!canSubmit"
          aria-label="Submit for Review (Ctrl+Enter)"
          @click="$emit('submit')"
        >
          <v-icon start>mdi-check-circle</v-icon>
          Submit for Review
        </v-btn>
      </template>
      <span>Submit for Review (Ctrl+Enter)</span>
    </v-tooltip>
  </v-card-actions>
</template>

<script setup>
defineProps({
  canUndo: {
    type: Boolean,
    default: false
  },
  canRedo: {
    type: Boolean,
    default: false
  },
  canSubmit: {
    type: Boolean,
    default: true
  },
  saving: {
    type: Boolean,
    default: false
  },
  submitting: {
    type: Boolean,
    default: false
  }
})

defineEmits(['undo', 'redo', 'save-draft', 'submit', 'cancel'])
</script>
```

---

### Phase 5: Update Existing DynamicForm (30min)

**File**: `frontend/src/components/dynamic/DynamicForm.vue`

**Changes** (minimal, non-breaking):

1. **Add `v-model` support** via `update:modelValue` event
2. **Add `validation-change` event** for parent to track validity
3. **Add `readonly` prop** for review mode

```javascript
// Add to existing defineProps
const props = defineProps({
  // ... existing props
  readonly: {
    type: Boolean,
    default: false
  }
})

// Add to existing defineEmits
const emit = defineEmits(['submit', 'save-draft', 'update:modelValue', 'validation-change'])

// Add watch to emit modelValue changes
watch(formData, (newVal) => {
  emit('update:modelValue', { ...newVal })
}, { deep: true })

// Add watch to emit validation changes
watch(validationResult, (result) => {
  emit('validation-change', result)
}, { immediate: true })
```

> **Note**: No `defineExpose` used. Parent components receive data via events, following Vue 3 best practices.

---

### Phase 6: Update Routes (15min)

**File**: `frontend/src/router/index.js`

Ensure routes pass schema_id query param:

```javascript
{
  path: '/scopes/:scopeId/genes/:geneId/curation/new',
  name: 'curation-new',
  component: CurationFormView,
  meta: { requiresAuth: true, roles: ['curator', 'admin'] }
},
{
  path: '/scopes/:scopeId/curations/:curationId/edit',
  name: 'curation-edit',
  component: CurationFormView,
  meta: { requiresAuth: true, roles: ['curator', 'admin'] }
}
```

---

## Migration Strategy

### Recommended: Parallel Components (Option A)

1. **Keep** `CurationForm.vue` as `LegacyCurationForm.vue`
2. **Create** `SchemaDrivenCurationForm.vue` as new implementation
3. **Feature flag** in `CurationFormView.vue`:
   ```javascript
   const useDynamicForm = import.meta.env.VITE_USE_DYNAMIC_FORM === 'true'
   ```
4. **Test** both paths in parallel
5. **Remove** legacy after 1 sprint validation

---

## File Changes Summary

| Action | File | Description |
|--------|------|-------------|
| CREATE | `components/forms/SchemaDrivenCurationForm.vue` | New schema-driven wrapper |
| CREATE | `components/forms/CurationSchemaSelect.vue` | Single-schema selector (avoids naming conflict) |
| CREATE | `components/forms/FormActions.vue` | Reusable action bar |
| MODIFY | `components/dynamic/DynamicForm.vue` | Add v-model, validation-change, readonly |
| MODIFY | `views/curation/CurationFormView.vue` | Add schema resolution logic |
| RENAME | `components/forms/CurationForm.vue` → `LegacyCurationForm.vue` | Preserve for rollback |

---

## Testing Checklist

### Unit Tests

- [ ] SchemaDrivenCurationForm renders DynamicForm with schemaId
- [ ] CurationSchemaSelect filters schemas by type
- [ ] Schema resolution priority chain works correctly
- [ ] evidenceData changes emit `update:modelValue`
- [ ] validation state emits `validation-change`
- [ ] Keyboard shortcuts work (Ctrl+S, Ctrl+Z, Ctrl+Enter, Esc)

### Integration Tests

- [ ] Create curation with ClinGen schema → fields render correctly
- [ ] Create curation with GenCC schema → different fields render
- [ ] Edit existing curation → loads saved evidence_data
- [ ] Save draft → evidence_data persists with correct lock_version
- [ ] Submit → validation runs against schema
- [ ] Form recovery works when browser crashes mid-edit
- [ ] Schema change clears form recovery (prevents data mismatch)

### E2E Tests

- [ ] Full workflow: Gene → Precuration → Curation → Review
- [ ] Schema switching for new curation (admin)
- [ ] Undo/redo across multiple edits

---

## Acceptance Criteria

- [ ] DynamicForm renders fields from any schema (not hardcoded)
- [ ] Schema determined by workflow_pair or explicit selection
- [ ] Evidence data saved as JSONB (schema-agnostic)
- [ ] Validation uses schema rules (not hardcoded)
- [ ] Live scoring still works with dynamic fields
- [ ] Auto-save (formRecovery) works with schema-aware keys
- [ ] Undo/redo works with dynamic form changes
- [ ] Keyboard shortcuts migrated and functional
- [ ] No regression in existing ClinGen workflow
- [ ] LegacyCurationForm available for rollback

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| JSON schema mismatch | Test with multiple schemas before deploy |
| Breaking existing curations | Keep LegacyCurationForm, feature flag |
| Form recovery cross-schema | Schema-aware recovery keys |
| Performance (large schemas) | Lazy load field components |
| Validation gaps | Backend validates regardless of frontend |

---

## Dependencies

- Schema definitions exist in database (seed data)
- Backend `/validation/generate-json-schema/{id}` working
- Workflow pairs configured for scopes
- Feature flag env var: `VITE_USE_DYNAMIC_FORM`

---

## Related Issues

| Issue | Relationship |
|-------|--------------|
| #62 Enhance Curation Card | **CLOSES** - DynamicForm replaces hardcoded |
| #61 Enhance Pre-Curation Card | **CLOSES** - Same pattern applies |
| #77 Prefill Logic | **CLOSES** - Schema drives prefill |
| #116 Multi-user approval | Enables (needs #010 for UI) |

---

## Post-Implementation

1. Update CLAUDE.md with DynamicForm patterns
2. Add documentation for schema authors
3. Create 2-3 example schemas (ClinGen, GenCC, Qualitative)
4. Remove LegacyCurationForm after 1 sprint validation
5. Apply same pattern to PrecurationForm

---

## Code Review Changes Applied

| Issue | Resolution |
|-------|------------|
| SchemaSelector naming conflict | Renamed to `CurationSchemaSelect.vue` |
| defineExpose anti-pattern | Replaced with `validation-change` event |
| Form recovery schema-awareness | Added schema-aware recovery keys |
| Keyboard shortcut migration | Added `handleKeydown` with all shortcuts |
| KISS violation (CurationHeader) | Kept inline in template |
| Error boundary handling | Added `handleFormError` with logging |
| EvidenceItemDialog integration | Handled by DynamicField array type |

---

**Last Updated**: 2026-01-12
**Author**: Claude Code
**Review Status**: Code review fixes applied - Ready for implementation
