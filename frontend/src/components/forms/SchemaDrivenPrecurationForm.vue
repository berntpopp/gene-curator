<template>
  <ErrorBoundary @error="handleFormError">
    <v-form @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card class="overflow-visible">
        <!-- Header with precuration context -->
        <v-card-title class="d-flex align-center flex-wrap ga-2 text-wrap">
          <span>{{ gene?.symbol || 'Gene' }} - Precuration</span>
          <v-chip v-if="isDraft" color="warning" size="small" class="ml-2">Draft</v-chip>
          <v-spacer />
          <SaveState v-if="conflict" state="conflict" :saved-at="null" />
          <v-chip v-else-if="savedAt" color="success" size="small" variant="outlined">
            <v-icon start size="small">mdi-content-save</v-icon>
            Saved {{ formatRelativeTime(savedAt) }}
          </v-chip>
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-skeleton-loader v-if="loadingSchema" type="article" />

          <!-- Rendered and validated from the version the precuration is pinned to -->
          <DynamicForm
            v-else-if="version"
            :schema-id="schemaId"
            :definition="version.snapshot"
            :methodology-version-id="version.id"
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

          <!-- The server names the precuration this disease entity already has (monkey B5) -->
          <v-alert
            v-if="duplicate"
            type="warning"
            variant="tonal"
            class="mt-4"
            data-testid="duplicate-entity"
          >
            {{ duplicate.message }}.
            <router-link
              :to="{
                name: 'precuration-edit',
                params: { scopeId, precurationId: duplicate.id }
              }"
            >
              Open the existing precuration
            </router-link>
            <template v-if="draftId" #append>
              <v-btn variant="outlined" data-testid="discard-duplicate" @click="discardDuplicate()">
                Discard this draft
              </v-btn>
            </template>
          </v-alert>
        </v-card-text>

        <v-divider />

        <!-- Actions -->
        <FormActions
          v-if="!readonly"
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
      v-if="!readonly"
      :model-value="showRecoveryDialog"
      :timestamp="recoveryTimestamp"
      :stale="recoveryStale"
      @restore="handleRestore"
      @discard="discardRecovery"
    />
  </ErrorBoundary>
</template>

<script lang="ts">
  // Drafts this tab created: a later duplicate-entity refusal removes them (monkey B5)
  const createdHere = new Set<string>()
</script>

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

  import { ref, computed, watch, inject, onMounted, onBeforeUnmount } from 'vue'
  import { useRouter } from 'vue-router'
  import { useSchemasStore } from '@/stores/schemas'
  import { usePrecurationsStore } from '@/stores/precurations'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useFormRecovery } from '@/composables/useFormRecovery'
  import { recoveryVersion } from '@/utils/formRecoveryStorage'
  import { apiDetail } from './apiDetail'
  import { missingRequiredLabels } from './requiredFields'
  import { useHistory } from '@/composables/useHistory'
  import { useLogger } from '@/composables/useLogger'
  import type { ApiErrorLike } from './types'
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import FormRecoveryDialog from '@/components/FormRecoveryDialog.vue'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import SaveState from '@/components/workspace/SaveState.vue'
  import { WORKSPACE_FRAME } from '@/components/workspace/useWorkspaceFrame'
  import { replaceKeepingChanges } from '@/components/workspace/useUnsavedGuard'
  import FormActions from '@/components/forms/FormActions.vue'
  import { useConfirm } from '@/composables/useConfirm'
  import type { Schema } from '@/types/api'

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
  const notificationsStore = useNotificationsStore()

  // Form state
  const evidenceData = ref<EvidenceData>({})
  const isDraft = ref(true)
  const loadingSchema = ref(false)
  const savingDraft = ref(false)
  // Another tab saved first: saving and submitting are blocked until the page is reloaded; the
  // local recovery copy is kept and offered back after the reload, flagged as older
  const conflict = ref(false)
  const submitting = ref(false)
  const createdId = ref<string | null>(null)
  const draftId = computed(() => props.precurationId ?? createdId.value)
  const duplicate = ref<{ message: string; id: string } | null>(null)
  const savedAt = ref<number | null>(null) // last successful server save
  const isValid = ref(true) // Updated via validation-change event
  const version = ref<Schema<'MethodologyVersion'> | null>(null)
  const pinnedVersionId = ref<string | null>(null) // the loaded precuration's

  // Form Recovery - schema-aware key to prevent cross-schema data restore; a new precuration's
  // draft belongs to its scope and gene, never offered on another gene's new precuration
  const recoveryKey = computed(
    () =>
      `precuration-${props.precurationId || `new-${props.scopeId}-${props.geneId}`}-schema-${props.schemaId}`
  )

  let serverVersion: string | null = null // the loaded precuration's, for the recovery baseline
  const {
    showRecoveryDialog,
    recoveryTimestamp,
    recoveryStale,
    restoreRecovery,
    discardRecovery,
    clearRecovery,
    setBaseline,
    markSaved
  } = useFormRecovery(recoveryKey.value, evidenceData, {
    maxAge: 24 * 60 * 60 * 1000
  })

  function handleRestore(): void {
    if (!props.readonly) restoreRecovery()
  }

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
      // A focused cell commits its typed text on blur: the save must include it (#469)
      ;(document.activeElement as HTMLElement | null)?.blur?.()
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
    }
    // No Escape here: it closes dialogs and menus only, never the form (monkey R2-6)
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

  // A copy for a save: nested edits typed during the request mutate the form's objects in place
  const evidenceCopy = () => JSON.parse(JSON.stringify(evidenceData.value)) as EvidenceData

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
  async function handleSaveDraft(): Promise<boolean> {
    if (conflict.value) return false // never save over the newer version; the user reloads
    savingDraft.value = true
    duplicate.value = null
    try {
      const existingId = props.precurationId ?? createdId.value
      if (existingId) {
        // Update existing precuration draft
        const sent = evidenceCopy()
        const updated = await precurationsStore.saveDraft(existingId, sent)
        // The store swallows save errors and returns nothing
        if (!updated) {
          const refused = precurationsStore.error
          if (refused?.isConflict) conflict.value = true
          if (refused?.existingId) {
            duplicate.value = { message: refused.message ?? '', id: refused.existingId }
            // Created on this page before the entity was complete: remove it, no orphan (B5)
            if (createdHere.has(existingId)) {
              await discardDuplicate(false)
              return false
            }
          }
          throw new Error(precurationsStore.error?.message || 'Draft not saved')
        }
        markSaved(sent, recoveryVersion(updated))
        emit('saved')
      } else {
        // Create new precuration as draft
        const created = await precurationsStore.createPrecuration(createPayload())
        createdHere.add(created.id)
        replaceKeepingChanges(router, {
          name: 'precuration-edit',
          params: { scopeId: props.scopeId, precurationId: created.id }
        })
        clearRecovery() // the editor loads the created precuration under its own key
      }
      savedAt.value = Date.now()

      notificationsStore.addToast('Draft saved', 'success')
      return true
    } catch (error) {
      logger.error('Failed to save draft', { error: (error as ApiErrorLike).message })
      const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data
        ?.detail as { message?: string; precuration_id?: string } | undefined
      if (detail?.precuration_id)
        duplicate.value = { message: detail.message ?? '', id: detail.precuration_id }
      notificationsStore.addToast(
        duplicate.value?.message || apiDetail(error, 'Failed to save draft'),
        'error'
      )
      return false
    } finally {
      savingDraft.value = false
    }
  }

  /**
   * Submit precuration
   */
  async function handleSubmit() {
    if (!canSubmit.value || conflict.value) return

    const snapshot = version.value?.snapshot
    const missing = missingRequiredLabels(
      snapshot?.field_definitions,
      evidenceData.value,
      snapshot?.validation_rules
    )
    if (missing.length > 0) {
      notificationsStore.addToast(`Required before submitting: ${missing.join(', ')}`, 'error')
      return
    }

    submitting.value = true
    try {
      // Keep the created id so a retry submits the same record, not a new draft
      let id = props.precurationId ?? createdId.value
      if (!id) {
        id = (await precurationsStore.createPrecuration(createPayload())).id
        createdId.value = id
      } else {
        // Persist the current edits first; the store swallows errors and returns nothing
        const sent = evidenceCopy()
        const updated = await precurationsStore.saveDraft(id, sent)
        if (!updated) {
          if (precurationsStore.error?.isConflict) conflict.value = true
          throw new Error(precurationsStore.error?.message || 'Draft not saved')
        }
        markSaved(sent, recoveryVersion(updated))
      }
      await precurationsStore.submitForReview(id)

      notificationsStore.addToast('Precuration submitted for review', 'success')
      clearRecovery()
      clearHistory()
      emit('submit')
    } catch (error) {
      logger.error('Failed to submit precuration', { error: (error as ApiErrorLike).message })
      if (precurationsStore.error?.isConflict) conflict.value = true
      notificationsStore.addToast(apiDetail(error, 'Failed to submit precuration'), 'error')
    } finally {
      submitting.value = false
    }
  }

  const { confirm } = useConfirm()

  // The view's leave guard (when it provides a workspace frame) compares with the saved draft
  const frame = inject(WORKSPACE_FRAME, null)
  frame?.attachForm({
    evidence: evidenceData,
    saving: savingDraft,
    savedAt,
    conflict,
    save: handleSaveDraft
  })

  /**
   * Cancel editing
   */
  /** Drop this duplicate draft and open the precuration the entity already has */
  async function discardDuplicate(ask = true) {
    const [id, existing] = [draftId.value, duplicate.value?.id]
    if (!id || !existing) return
    const ok =
      !ask ||
      (await confirm({
        title: 'Discard this draft?',
        text: 'This draft duplicates an existing precuration and will be removed.',
        confirmText: 'Discard'
      }))
    if (!ok) return
    try {
      await precurationsStore.deletePrecuration(id)
      createdHere.delete(id)
      if (!ask)
        notificationsStore.addToast(`${duplicate.value?.message}: this draft was removed`, 'error')
      frame?.markClean()
      router.push({
        name: 'precuration-edit',
        params: { scopeId: props.scopeId, precurationId: existing }
      })
    } catch (error) {
      notificationsStore.addToast(apiDetail(error, 'Could not discard the draft'), 'error')
    }
  }

  async function handleCancel() {
    if (Object.keys(evidenceData.value).length > 0) {
      if (
        !(await confirm({
          title: 'Discard unsaved changes?',
          confirmText: 'Discard',
          destructive: true
        }))
      )
        return
    }
    if (!props.readonly) clearRecovery()
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
        pinnedVersionId.value = precuration.methodology_version_id ?? null
        isDraft.value = precuration.status === 'draft'
        serverVersion = recoveryVersion(precuration)
      }
    } catch (error) {
      logger.error('Failed to load precuration', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast('Failed to load precuration', 'error')
    }
  }

  /**
   * Load the version the precuration renders with (the schema's latest for a new one)
   */
  async function loadSchema() {
    if (!props.schemaId) return

    loadingSchema.value = true
    try {
      version.value = await schemasStore.fetchPinnedVersion(pinnedVersionId.value, props.schemaId)
    } catch (error) {
      logger.error('Failed to load schema', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast('Failed to load precuration schema', 'error')
    } finally {
      loadingSchema.value = false
    }
  }

  onMounted(async () => {
    await loadPrecuration()
    await loadSchema()
    // Local drafts are compared with what the form now shows; none until the saved one loaded
    if (!props.precurationId || serverVersion) setBaseline(evidenceData.value, serverVersion)
    frame?.markClean(props.precurationId ? undefined : {})
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
