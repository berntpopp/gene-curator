<template>
  <ErrorBoundary @error="handleFormError">
    <v-form ref="formRef" @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card>
        <!-- Header with precuration context -->
        <v-card-title class="d-flex align-center">
          <span>{{ gene?.symbol || 'Gene' }} - Precuration</span>
          <v-chip v-if="isDraft" color="warning" size="small" class="ml-2">Draft</v-chip>
          <v-spacer />
          <v-chip v-if="lastSaved" color="success" size="small" variant="outlined">
            <v-icon start size="small">mdi-content-save</v-icon>
            Saved {{ formatRelativeTime(lastSaved) }}
          </v-chip>
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-skeleton-loader v-if="loadingSchema" type="article" />

          <DynamicForm
            v-else-if="schemaId"
            :schema-id="schemaId"
            :initial-data="evidenceData"
            :title="schema?.name || 'Precuration Form'"
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
            No schema assigned. Please contact an administrator.
          </v-alert>
        </v-card-text>

        <v-divider />

        <!-- Actions -->
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
   * SchemaDrivenPrecurationForm
   *
   * Schema-agnostic precuration form that renders fields dynamically based on
   * the assigned precuration schema. Delegates rendering to DynamicForm.
   *
   * Key Features:
   * - Renders any precuration schema dynamically
   * - Integrates form recovery, undo/redo
   * - Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Enter, Esc)
   * - Event-driven validation (no defineExpose)
   * - No scoring sidebar (precurations typically don't have scoring)
   *
   * @example
   * <SchemaDrivenPrecurationForm
   *   :schema-id="precurationSchemaId"
   *   :precuration-id="precurationId"
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
  import { usePrecurationsStore } from '@/stores/precurations'
  import { useValidationStore } from '@/stores/validation'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useFormRecovery } from '@/composables/useFormRecovery'
  import { useHistory } from '@/composables/useHistory'
  import { useLogger } from '@/composables/useLogger'
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import FormRecoveryDialog from '@/components/FormRecoveryDialog.vue'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import FormActions from '@/components/forms/FormActions.vue'

  const props = defineProps({
    schemaId: {
      type: String,
      required: true
    },
    precurationId: {
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
  const precurationsStore = usePrecurationsStore()
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
  const recoveryKey = computed(
    () => `precuration-${props.precurationId || 'new'}-schema-${props.schemaId}`
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
      precurationId: props.precurationId
    })
    notificationsStore.addToast('Form failed to render. Please try refreshing.', 'error')
  }

  /**
   * Keyboard shortcuts
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
      if (props.precurationId) {
        // Update existing precuration draft
        const updated = await precurationsStore.saveDraft(props.precurationId, evidenceData.value)
        if (updated) {
          lockVersion.value = updated.lock_version || 0
          emit('saved')
        }
      } else {
        // Create new precuration as draft
        const created = await precurationsStore.createPrecuration({
          gene_id: props.geneId,
          scope_id: props.scopeId,
          precuration_schema_id: props.schemaId,
          evidence_data: evidenceData.value
        })
        // Navigate to edit the created precuration
        router.replace({
          name: 'precuration-edit',
          params: { scopeId: props.scopeId, precurationId: created.id }
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
   * Submit precuration
   */
  async function handleSubmit() {
    if (!canSubmit.value) return

    submitting.value = true
    try {
      if (props.precurationId) {
        await precurationsStore.submitForReview(props.precurationId)
      } else {
        // Create and submit
        const created = await precurationsStore.createPrecuration({
          gene_id: props.geneId,
          scope_id: props.scopeId,
          precuration_schema_id: props.schemaId,
          evidence_data: evidenceData.value
        })
        await precurationsStore.submitForReview(created.id)
      }

      notificationsStore.addToast('Precuration submitted for review', 'success')
      clearRecovery()
      clearHistory()
      emit('submit')
    } catch (error) {
      logger.error('Failed to submit precuration', { error: error.message })
      notificationsStore.addToast('Failed to submit precuration', 'error')
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
   * Load existing precuration data
   */
  async function loadPrecuration() {
    if (!props.precurationId) return

    try {
      const precuration = await precurationsStore.fetchPrecurationById(props.precurationId)
      if (precuration) {
        evidenceData.value = precuration.evidence_data || {}
        lockVersion.value = precuration.lock_version || 0
        isDraft.value = precuration.status === 'draft'
      }
    } catch (error) {
      logger.error('Failed to load precuration', { error: error.message })
      notificationsStore.addToast('Failed to load precuration', 'error')
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
      notificationsStore.addToast('Failed to load precuration schema', 'error')
    } finally {
      loadingSchema.value = false
    }
  }

  onMounted(async () => {
    await loadSchema()
    await loadPrecuration()
    logger.debug('SchemaDrivenPrecurationForm mounted', {
      schemaId: props.schemaId,
      precurationId: props.precurationId
    })
  })

  onBeforeUnmount(() => {
    logger.debug('SchemaDrivenPrecurationForm unmounted')
  })
</script>

<style scoped>
  /* No additional styles needed - inherits from DynamicForm and FormActions */
</style>
