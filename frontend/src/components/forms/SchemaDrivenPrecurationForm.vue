<template>
  <ErrorBoundary @error="handleFormError">
    <v-form @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card>
        <!-- Header with precuration context -->
        <v-card-title class="d-flex align-center">
          <span>{{ gene?.symbol || 'Gene' }} - Precuration</span>
          <v-chip v-if="isDraft" color="warning" size="small" class="ml-2">Draft</v-chip>
          <v-spacer />
          <v-chip v-if="savedAt" color="success" size="small" variant="outlined">
            <v-icon start size="small">mdi-content-save</v-icon>
            Saved {{ formatRelativeTime(savedAt) }}
          </v-chip>
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-skeleton-loader v-if="loadingSchema" type="article" />

          <DynamicForm
            v-else-if="schemaId"
            :schema-id="schemaId"
            :initial-data="evidenceData"
            :title="''"
            :readonly="readonly"
            hide-actions
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
      :timestamp="recoveryTimestamp"
      @restore="restoreRecovery"
      @discard="discardRecovery"
    />
  </ErrorBoundary>
</template>

<script setup lang="ts">
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
  import { errorMessage } from '@/stores/apiError'
  import { useHistory } from '@/composables/useHistory'
  import { useLogger } from '@/composables/useLogger'
  import type { ApiErrorLike } from './types'
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import FormRecoveryDialog from '@/components/FormRecoveryDialog.vue'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import FormActions from '@/components/forms/FormActions.vue'

  type EvidenceData = Record<string, unknown>

  const props = withDefaults(
    defineProps<{
      schemaId: string
      precurationId?: string | null
      scopeId: string
      geneId?: string | null
      gene?: { symbol?: string | null } | null
      readonly?: boolean
    }>(),
    {
      precurationId: null,
      geneId: null,
      gene: null,
      readonly: false
    }
  )

  const emit = defineEmits<{
    submit: []
    cancel: []
    saved: []
  }>()

  const logger = useLogger()
  const router = useRouter()
  const schemasStore = useSchemasStore()
  const precurationsStore = usePrecurationsStore()
  const validationStore = useValidationStore()
  const notificationsStore = useNotificationsStore()

  // Form state
  const evidenceData = ref<EvidenceData>({})
  const isDraft = ref(true)
  const loadingSchema = ref(false)
  const savingDraft = ref(false)
  const submitting = ref(false)
  const createdId = ref<string | null>(null)
  const savedAt = ref<number | null>(null) // last successful server save
  const isValid = ref(true) // Updated via validation-change event

  // Form Recovery - schema-aware key to prevent cross-schema data restore
  const recoveryKey = computed(
    () => `precuration-${props.precurationId || 'new'}-schema-${props.schemaId}`
  )

  const { showRecoveryDialog, recoveryTimestamp, restoreRecovery, discardRecovery, clearRecovery } =
    useFormRecovery(recoveryKey.value, evidenceData, {
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
  } = useHistory(recoveryKey.value, (state: EvidenceData) => {
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
  function handleEvidenceChange(newData: EvidenceData) {
    evidenceData.value = newData
  }

  /**
   * Handle validation state changes from DynamicForm
   * Event-driven pattern instead of defineExpose
   */
  function handleValidationChange(validationResult: { is_valid?: boolean } | null | undefined) {
    isValid.value = validationResult?.is_valid !== false
  }

  /**
   * Handle form-level errors from ErrorBoundary
   */
  function handleFormError(error: Error) {
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
  function handleKeydown(event: KeyboardEvent) {
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

  /** Payload for a new precuration; the API requires a gene. */
  function createPayload() {
    if (!props.geneId) throw new Error('A gene is required')
    return {
      gene_id: props.geneId,
      scope_id: props.scopeId,
      precuration_schema_id: props.schemaId,
      evidence_data: evidenceData.value
    }
  }

  /**
   * Save draft
   */
  async function handleSaveDraft() {
    savingDraft.value = true
    try {
      const existingId = props.precurationId ?? createdId.value
      if (existingId) {
        // Update existing precuration draft
        const updated = await precurationsStore.saveDraft(existingId, evidenceData.value)
        if (updated) emit('saved')
      } else {
        // Create new precuration as draft
        const created = await precurationsStore.createPrecuration(createPayload())
        router.replace({
          name: 'precuration-edit',
          params: { scopeId: props.scopeId, precurationId: created.id }
        })
      }
      savedAt.value = Date.now()

      notificationsStore.addToast('Draft saved', 'success')
      clearRecovery()
    } catch (error) {
      logger.error('Failed to save draft', { error: (error as ApiErrorLike).message })
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
      // Keep the created id so a retry submits the same record, not a new draft
      let id = props.precurationId ?? createdId.value
      if (!id) {
        id = (await precurationsStore.createPrecuration(createPayload())).id
        createdId.value = id
      } else if (!props.precurationId) {
        // Retry after a failed submit: persist the edits made since
        await precurationsStore.saveDraft(id, evidenceData.value)
      }
      await precurationsStore.submitForReview(id)

      notificationsStore.addToast('Precuration submitted for review', 'success')
      clearRecovery()
      clearHistory()
      emit('submit')
    } catch (error) {
      logger.error('Failed to submit precuration', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(errorMessage(error, 'Failed to submit precuration'), 'error')
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
  function formatRelativeTime(timestamp: string | number | null | undefined): string {
    if (!timestamp) return ''
    const now = new Date()
    const then = new Date(timestamp)
    const diffSec = Math.floor((now.getTime() - then.getTime()) / 1000)

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
        evidenceData.value = precuration.evidence_data
        isDraft.value = precuration.status === 'draft'
      }
    } catch (error) {
      logger.error('Failed to load precuration', { error: (error as ApiErrorLike).message })
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
      logger.error('Failed to load schema', { error: (error as ApiErrorLike).message })
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
