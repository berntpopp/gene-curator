<template>
  <ErrorBoundary @error="handleFormError">
    <v-form ref="formRef" @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card>
        <!-- Header: Kept inline per KISS principle -->
        <v-card-title class="d-flex align-center">
          <span>{{ gene?.symbol }} - {{ schema?.name || 'Curation' }}</span>
          <v-chip v-if="isDraft" color="warning" size="small" class="ml-2"> Draft </v-chip>
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
                <ScorePreview :evidence-items="scoreEvidenceItems" />
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
   * - Integrates form recovery, undo/redo
   * - Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Enter, Esc)
   * - Event-driven validation (no defineExpose)
   *
   * @example
   * <SchemaDrivenCurationForm
   *   :schema-id="resolvedSchemaId"
   *   :curation-id="curationId"
   *   :scope-id="scopeId"
   *   :gene-id="geneId"
   *   :gene="gene"
   *   @submit="handleSubmit"
   *   @cancel="handleCancel"
   *   @saved="handleSaved"
   * />
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

  // Evidence items for score preview (transform to expected format)
  const scoreEvidenceItems = computed(() => {
    // ScorePreview expects an array of evidence items
    // Transform evidence_data to that format if needed
    if (Array.isArray(evidenceData.value.evidence_items)) {
      return evidenceData.value.evidence_items
    }
    return []
  })

  // Form Recovery - schema-aware key to prevent cross-schema data restore
  const recoveryKey = computed(
    () => `curation-${props.curationId || 'new'}-schema-${props.schemaId}`
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
  watch(
    () => props.schemaId,
    (newId, oldId) => {
      if (oldId && newId !== oldId) {
        clearRecovery()
        evidenceData.value = {}
        logger.info('Schema changed, cleared form recovery', { oldId, newId })
      }
    }
  )

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
  watch(
    evidenceData,
    (newVal, oldVal) => {
      if (oldVal && Object.keys(oldVal).length > 0) {
        recordAction('edit', oldVal, { ...newVal })
      }
    },
    { deep: true }
  )

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
