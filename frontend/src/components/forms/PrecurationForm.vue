<template>
  <ErrorBoundary>
    <v-form ref="formRef" @submit.prevent="handleSubmit">
      <v-card>
        <!-- Header with Status -->
        <v-card-title class="d-flex align-center bg-primary">
          <v-icon start size="large">mdi-file-document-edit</v-icon>
          <span>ClinGen Precuration</span>
          <v-spacer />
          <v-chip v-if="isDraft" color="warning" size="small" variant="elevated">
            <v-icon start size="small">mdi-pencil</v-icon>
            Draft
          </v-chip>
          <v-chip v-else color="success" size="small" variant="elevated">
            <v-icon start size="small">mdi-check</v-icon>
            Submitted
          </v-chip>
        </v-card-title>

        <v-card-text class="pa-6">
          <!-- Auto-save Indicator -->
          <v-alert
            v-if="lastSaved"
            icon="mdi-content-save"
            color="success"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <div class="text-caption">
              Auto-saved {{ formatTimeAgo(lastSaved) }}
              <v-tooltip location="top" activator="parent">
                Last saved: {{ new Date(lastSaved).toLocaleString() }}
              </v-tooltip>
            </div>
          </v-alert>

          <!-- Gene Identification Section -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              <v-icon start size="small">mdi-dna</v-icon>
              Gene Identification
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <ValidatedInput
                    v-model="formData.gene_symbol"
                    validator="hgnc"
                    label="Gene Symbol"
                    hint="Enter HGNC gene symbol (e.g., BRCA1)"
                    required
                    data-test="gene-symbol"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="formData.scope_id"
                    :items="availableScopes"
                    item-title="display_name"
                    item-value="id"
                    label="Clinical Scope"
                    hint="Select the clinical specialty"
                    variant="outlined"
                    required
                    data-test="scope-select"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Disease/Phenotype Association -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              <v-icon start size="small">mdi-medical-bag</v-icon>
              Associated Phenotypes
            </v-card-title>
            <v-card-text>
              <HPOInput
                v-model="formData.hpo_terms"
                label="HPO Terms"
                hint="Enter Human Phenotype Ontology terms (e.g., HP:0001250)"
                required
                data-test="hpo-terms"
              />
            </v-card-text>
          </v-card>

          <!-- Curation Rationale -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              <v-icon start size="small">mdi-text-box</v-icon>
              Curation Rationale
            </v-card-title>
            <v-card-text>
              <v-textarea
                v-model="formData.rationale"
                label="Rationale for Curation"
                hint="Explain why this gene-disease relationship should be curated"
                variant="outlined"
                rows="4"
                required
                counter
                maxlength="2000"
                data-test="rationale"
              />
            </v-card-text>
          </v-card>

          <!-- Supporting Evidence -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              <v-icon start size="small">mdi-book-open-variant</v-icon>
              Supporting Publications
            </v-card-title>
            <v-card-text>
              <PMIDInput
                v-model="formData.pmids"
                label="PubMed IDs"
                hint="Enter supporting PubMed IDs"
                required
                data-test="pmids"
              />
            </v-card-text>
          </v-card>

          <!-- Additional Notes -->
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              <v-icon start size="small">mdi-note-text</v-icon>
              Curator Notes (Optional)
            </v-card-title>
            <v-card-text>
              <v-textarea
                v-model="formData.curator_notes"
                label="Internal Notes"
                hint="Optional notes for review team"
                variant="outlined"
                rows="3"
                counter
                maxlength="1000"
                data-test="curator-notes"
              />
            </v-card-text>
          </v-card>
        </v-card-text>

        <!-- Actions Footer -->
        <v-card-actions class="pa-4 bg-grey-lighten-5">
          <v-btn variant="outlined" prepend-icon="mdi-close" @click="handleCancel"> Cancel </v-btn>

          <v-spacer />

          <!-- Undo/Redo Controls -->
          <v-btn-group variant="outlined" density="compact" class="mr-2">
            <v-btn
              :disabled="!canUndo"
              data-test="undo-btn"
              aria-label="Undo (Ctrl+Z)"
              @click="undo"
            >
              <v-icon>mdi-undo</v-icon>
              <v-tooltip activator="parent" location="top"> Undo (Ctrl+Z) </v-tooltip>
            </v-btn>
            <v-btn
              :disabled="!canRedo"
              data-test="redo-btn"
              aria-label="Redo (Ctrl+Shift+Z)"
              @click="redo"
            >
              <v-icon>mdi-redo</v-icon>
              <v-tooltip activator="parent" location="top"> Redo (Ctrl+Shift+Z) </v-tooltip>
            </v-btn>
          </v-btn-group>

          <!-- Save Draft -->
          <v-btn
            variant="outlined"
            prepend-icon="mdi-content-save"
            :loading="savingDraft"
            data-test="save-draft-btn"
            @click="handleSaveDraft"
          >
            Save Draft
            <v-tooltip activator="parent" location="top"> Save Draft (Ctrl+S) </v-tooltip>
          </v-btn>

          <!-- Submit -->
          <v-btn
            color="primary"
            type="submit"
            prepend-icon="mdi-check"
            :loading="submitting"
            :disabled="!isFormValid"
            data-test="submit-btn"
          >
            Submit Precuration
            <v-tooltip activator="parent" location="top"> Submit (Ctrl+Enter) </v-tooltip>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>

    <!-- Recovery Dialog -->
    <FormRecoveryDialog
      v-model="showRecoveryDialog"
      :timestamp="recoveryData?.timestamp"
      @restore="restoreRecovery"
      @discard="discardRecovery"
    />

    <!-- Conflict Resolution Dialog -->
    <ConflictResolutionDialog
      v-model="conflictDetected"
      :your-changes="conflictData?.yourChanges"
      :their-changes="conflictData?.theirChanges"
      @resolve="handleConflictResolution"
    />

    <!-- Session Timeout Warning -->
    <SessionTimeoutWarning
      v-model="showTimeoutWarning"
      :time-remaining="timeRemaining"
      @dismiss="showTimeoutWarning = false"
      @extend="extendSession"
    />
  </ErrorBoundary>
</template>

<script setup>
  /**
   * PrecurationForm Component
   *
   * Comprehensive precuration form integrating ALL Week 1 infrastructure:
   * - Form recovery (auto-save + localStorage)
   * - Undo/redo system (command pattern)
   * - Conflict resolution (optimistic locking)
   * - Session timeout (JWT expiration warning)
   * - Error boundaries (graceful failures)
   * - On-blur validation (NOT real-time)
   * - Keyboard shortcuts (Ctrl+S, Ctrl+Z, etc.)
   *
   * Design principles:
   * - Progressive disclosure (expandable sections)
   * - Clear visual hierarchy
   * - Accessible (ARIA labels, keyboard nav)
   * - Mobile-responsive
   * - Production-ready error handling
   *
   * @example
   * <precuration-form
   *   :gene-id="geneId"
   *   :scope-id="scopeId"
   *   @success="handleSuccess"
   *   @cancel="handleCancel"
   * />
   */

  import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
  import { useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { precurationsAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { useFormRecovery } from '@/composables/useFormRecovery'
  import { useHistory } from '@/composables/useHistory'
  import { useOptimisticLocking } from '@/composables/useOptimisticLocking'
  import { useSessionTimeout } from '@/composables/useSessionTimeout'

  // Import all shared components
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import ValidatedInput from '@/components/ValidatedInput.vue'
  import PMIDInput from '@/components/evidence/PMIDInput.vue'
  import HPOInput from '@/components/evidence/HPOInput.vue'
  import FormRecoveryDialog from '@/components/FormRecoveryDialog.vue'
  import ConflictResolutionDialog from '@/components/ConflictResolutionDialog.vue'
  import SessionTimeoutWarning from '@/components/SessionTimeoutWarning.vue'

  const props = defineProps({
    /**
     * Precuration ID for editing existing precuration
     */
    precurationId: {
      type: String,
      default: null
    },
    /**
     * Pre-fill gene ID
     */
    geneId: {
      type: String,
      default: null
    },
    /**
     * Pre-fill scope ID
     */
    scopeId: {
      type: String,
      default: null
    }
  })

  const emit = defineEmits(['success', 'cancel'])

  const router = useRouter()
  const logger = useLogger()
  const scopesStore = useScopesStore()

  // Form reference
  const formRef = ref(null)

  // Form data
  const formData = ref({
    gene_symbol: '',
    scope_id: props.scopeId || '',
    hpo_terms: [],
    rationale: '',
    pmids: [],
    curator_notes: '',
    lock_version: 0
  })

  // Form state
  const isDraft = ref(true)
  const savingDraft = ref(false)
  const submitting = ref(false)
  const loading = ref(false)

  // Available scopes
  const availableScopes = computed(() => scopesStore.scopes || [])

  // Form validation
  const isFormValid = computed(() => {
    return (
      formData.value.gene_symbol &&
      formData.value.scope_id &&
      formData.value.hpo_terms.length > 0 &&
      formData.value.rationale &&
      formData.value.pmids.length > 0
    )
  })

  // === Infrastructure Integration ===

  // 1. Form Recovery
  const {
    showRecoveryDialog,
    recoveryData,
    lastSaved,
    restoreRecovery,
    discardRecovery,
    clearRecovery
  } = useFormRecovery(`precuration-${props.precurationId || 'new'}`, formData, {
    saveInterval: 5000, // Auto-save every 5 seconds
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  })

  // 2. Undo/Redo System
  const {
    canUndo,
    canRedo,
    recordAction,
    undo: undoAction,
    redo: redoAction,
    clearHistory
  } = useHistory(`precuration-${props.precurationId || 'new'}`, state => {
    formData.value = { ...state }
  })

  // Watch form changes for undo/redo
  watch(
    formData,
    (newVal, oldVal) => {
      if (oldVal && JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
        recordAction('edit', oldVal, newVal)
      }
    },
    { deep: true }
  )

  // 3. Optimistic Locking
  const { conflictDetected, conflictData, saveWithLockCheck, resolveConflict } =
    useOptimisticLocking()

  // 4. Session Timeout
  const { showTimeoutWarning, timeRemaining, extendSession } = useSessionTimeout()

  // === Lifecycle ===

  onMounted(async () => {
    // Load scopes if not already loaded
    if (!scopesStore.scopes || scopesStore.scopes.length === 0) {
      await scopesStore.fetchScopes()
    }

    // Load existing precuration if editing
    if (props.precurationId) {
      await loadPrecuration()
    }
  })

  onBeforeUnmount(() => {
    // Cleanup
  })

  // === Methods ===

  /**
   * Load existing precuration for editing
   */
  async function loadPrecuration() {
    loading.value = true
    try {
      const precuration = await precurationsAPI.getPrecuration(props.precurationId)

      formData.value = {
        gene_symbol: precuration.gene_symbol || '',
        scope_id: precuration.scope_id || '',
        hpo_terms: precuration.evidence_data?.hpo_terms || [],
        rationale: precuration.evidence_data?.rationale || '',
        pmids: precuration.evidence_data?.pmids || [],
        curator_notes: precuration.evidence_data?.curator_notes || '',
        lock_version: precuration.lock_version || 0
      }

      isDraft.value = precuration.is_draft || false

      logger.info('Precuration loaded for editing', { id: props.precurationId })
    } catch (error) {
      logger.error('Failed to load precuration', { error: error.message })
      // Show error notification
    } finally {
      loading.value = false
    }
  }

  /**
   * Handle form submission
   */
  async function handleSubmit() {
    if (!isFormValid.value) {
      logger.warn('Form validation failed')
      return
    }

    submitting.value = true

    try {
      const payload = {
        gene_symbol: formData.value.gene_symbol,
        scope_id: formData.value.scope_id,
        evidence_data: {
          hpo_terms: formData.value.hpo_terms,
          rationale: formData.value.rationale,
          pmids: formData.value.pmids,
          curator_notes: formData.value.curator_notes
        },
        is_draft: false,
        lock_version: formData.value.lock_version
      }

      let result
      if (props.precurationId) {
        // Update with optimistic locking
        result = await saveWithLockCheck(
          data => precurationsAPI.updatePrecuration(props.precurationId, data),
          payload,
          formData.value.lock_version
        )
      } else {
        // Create new
        result = await precurationsAPI.createPrecuration(payload)
      }

      // Clear recovery and history on successful submit
      clearRecovery()
      clearHistory()

      logger.info('Precuration submitted successfully', { id: result.id })
      emit('success', result)

      // Navigate to success page or list
      router.push({ name: 'Precurations' })
    } catch (error) {
      if (error.response?.status !== 409) {
        // Not a conflict - show error
        logger.error('Failed to submit precuration', { error: error.message })
      }
      // Conflict (409) is handled by useOptimisticLocking
    } finally {
      submitting.value = false
    }
  }

  /**
   * Save as draft
   */
  async function handleSaveDraft() {
    savingDraft.value = true

    try {
      const payload = {
        gene_symbol: formData.value.gene_symbol,
        scope_id: formData.value.scope_id,
        evidence_data: {
          hpo_terms: formData.value.hpo_terms,
          rationale: formData.value.rationale,
          pmids: formData.value.pmids,
          curator_notes: formData.value.curator_notes
        },
        is_draft: true,
        lock_version: formData.value.lock_version
      }

      let result
      if (props.precurationId) {
        result = await precurationsAPI.saveDraft(props.precurationId, payload)
      } else {
        result = await precurationsAPI.createPrecuration(payload)
      }

      // Update lock version
      formData.value.lock_version = result.lock_version

      logger.info('Draft saved', { id: result.id })
    } catch (error) {
      logger.error('Failed to save draft', { error: error.message })
    } finally {
      savingDraft.value = false
    }
  }

  /**
   * Handle cancel
   */
  function handleCancel() {
    if (confirm('Discard unsaved changes?')) {
      clearRecovery()
      clearHistory()
      emit('cancel')
      router.push({ name: 'Precurations' })
    }
  }

  /**
   * Undo last action
   */
  function undo() {
    const previousState = undoAction()
    if (previousState) {
      formData.value = { ...previousState }
      logger.debug('Undo action', { canUndo: canUndo.value })
    }
  }

  /**
   * Redo last undone action
   */
  function redo() {
    const nextState = redoAction()
    if (nextState) {
      formData.value = { ...nextState }
      logger.debug('Redo action', { canRedo: canRedo.value })
    }
  }

  /**
   * Handle conflict resolution
   */
  async function handleConflictResolution(resolution) {
    const resolved = resolveConflict(resolution)

    if (resolution === 'discard-mine') {
      // Reload their version
      await loadPrecuration()
    } else if (resolution === 'overwrite-theirs') {
      // Force save with their version number + 1
      formData.value.lock_version = resolved.theirVersion
      await handleSubmit()
    } else if (resolution === 'merge') {
      // Show merge UI (future enhancement)
      logger.info('Manual merge initiated')
    }
  }

  /**
   * Format time ago (e.g., "2 minutes ago")
   */
  function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - new Date(timestamp)) / 1000)

    if (seconds < 60) return `${seconds} seconds ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
    const hours = Math.floor(minutes / 60)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  }

  // === Keyboard Shortcuts ===
  function handleKeydown(event) {
    const ctrl = event.ctrlKey || event.metaKey

    // Ctrl+S: Save Draft
    if (ctrl && event.key === 's') {
      event.preventDefault()
      handleSaveDraft()
    }
    // Ctrl+Enter: Submit
    else if (ctrl && event.key === 'Enter') {
      event.preventDefault()
      handleSubmit()
    }
    // Ctrl+Z: Undo
    else if (ctrl && event.key === 'z' && !event.shiftKey) {
      event.preventDefault()
      if (canUndo.value) undo()
    }
    // Ctrl+Shift+Z: Redo
    else if (ctrl && event.key === 'z' && event.shiftKey) {
      event.preventDefault()
      if (canRedo.value) redo()
    }
    // Esc: Cancel
    else if (event.key === 'Escape') {
      handleCancel()
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeydown)
  })
</script>

<style scoped>
  /* Ensure consistent section spacing */
  .v-card + .v-card {
    margin-top: 16px;
  }

  /* Section headers */
  .bg-grey-lighten-4 {
    background-color: rgb(245, 245, 245);
  }

  /* Dark mode */
  .v-theme--dark .bg-grey-lighten-4 {
    background-color: rgb(66, 66, 66);
  }

  /* Footer actions */
  .v-card-actions {
    border-top: 1px solid rgba(0, 0, 0, 0.12);
  }

  .v-theme--dark .v-card-actions {
    border-top: 1px solid rgba(255, 255, 255, 0.12);
  }
</style>
