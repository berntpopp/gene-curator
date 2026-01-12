<template>
  <ErrorBoundary>
    <v-form ref="formRef" @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card elevation="2">
        <!-- Header -->
        <v-card-title class="d-flex align-center">
          <span>ClinGen Gene-Disease Curation</span>
          <v-chip v-if="isDraft" color="warning" size="small" class="ml-2">Draft</v-chip>
          <v-spacer />
          <v-chip v-if="lastSaved" color="success" size="small" variant="outlined">
            <v-icon start size="small">mdi-content-save</v-icon>
            Saved {{ formatRelativeTime(lastSaved) }}
          </v-chip>
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-row>
            <!-- Main Form Section (Left) -->
            <v-col cols="12" lg="8">
              <!-- Gene & Disease Information -->
              <v-card variant="outlined" class="mb-4">
                <v-card-title class="text-subtitle-1">Gene & Disease Information</v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <ValidatedInput
                        v-model="formData.gene_symbol"
                        label="Gene Symbol"
                        hint="Enter HGNC gene symbol (e.g., BRCA1)"
                        :required="true"
                        validation-type="hgnc"
                        @blur="handleGeneBlur"
                      />
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="formData.disease_name"
                        label="Disease Name"
                        hint="Associated disease or phenotype"
                        variant="outlined"
                        :required="true"
                      />
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12">
                      <HPOInput
                        v-model="formData.hpo_terms"
                        label="HPO Terms"
                        hint="Associated Human Phenotype Ontology terms"
                      />
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>

              <!-- Evidence Tabs -->
              <v-card variant="outlined" class="mb-4">
                <v-tabs v-model="activeTab" bg-color="primary" dark>
                  <v-tab value="genetic">
                    <v-icon start>mdi-dna</v-icon>
                    Genetic Evidence
                    <v-chip
                      v-if="geneticEvidenceCount > 0"
                      size="x-small"
                      color="white"
                      class="ml-2"
                    >
                      {{ geneticEvidenceCount }}
                    </v-chip>
                  </v-tab>
                  <v-tab value="experimental">
                    <v-icon start>mdi-flask</v-icon>
                    Experimental Evidence
                    <v-chip
                      v-if="experimentalEvidenceCount > 0"
                      size="x-small"
                      color="white"
                      class="ml-2"
                    >
                      {{ experimentalEvidenceCount }}
                    </v-chip>
                  </v-tab>
                  <v-tab value="contradictory">
                    <v-icon start>mdi-alert</v-icon>
                    Contradictory Evidence
                    <v-chip
                      v-if="contradictoryEvidenceCount > 0"
                      size="x-small"
                      color="white"
                      class="ml-2"
                    >
                      {{ contradictoryEvidenceCount }}
                    </v-chip>
                  </v-tab>
                </v-tabs>

                <v-window v-model="activeTab">
                  <!-- Genetic Evidence Tab -->
                  <v-window-item value="genetic">
                    <v-card-text>
                      <div class="d-flex justify-space-between align-center mb-4">
                        <div class="text-subtitle-2">Genetic Evidence Items (Max 12 points)</div>
                        <v-btn
                          color="primary"
                          variant="outlined"
                          size="small"
                          @click="addEvidenceItem('genetic')"
                        >
                          <v-icon start>mdi-plus</v-icon>
                          Add Evidence
                        </v-btn>
                      </div>

                      <!-- Genetic Evidence List -->
                      <div v-if="geneticEvidence.length > 0" class="evidence-list">
                        <EvidenceItemCard
                          v-for="(item, index) in geneticEvidence"
                          :key="item.id || index"
                          :evidence="item"
                          :index="index"
                          @edit="editEvidenceItem('genetic', index)"
                          @delete="deleteEvidenceItem('genetic', index)"
                        />
                      </div>
                      <v-alert v-else type="info" variant="tonal" density="compact">
                        No genetic evidence items yet. Add evidence to start building your curation.
                      </v-alert>
                    </v-card-text>
                  </v-window-item>

                  <!-- Experimental Evidence Tab -->
                  <v-window-item value="experimental">
                    <v-card-text>
                      <div class="d-flex justify-space-between align-center mb-4">
                        <div class="text-subtitle-2">
                          Experimental Evidence Items (Max 6 points)
                        </div>
                        <v-btn
                          color="primary"
                          variant="outlined"
                          size="small"
                          @click="addEvidenceItem('experimental')"
                        >
                          <v-icon start>mdi-plus</v-icon>
                          Add Evidence
                        </v-btn>
                      </div>

                      <!-- Experimental Evidence List -->
                      <div v-if="experimentalEvidence.length > 0" class="evidence-list">
                        <EvidenceItemCard
                          v-for="(item, index) in experimentalEvidence"
                          :key="item.id || index"
                          :evidence="item"
                          :index="index"
                          @edit="editEvidenceItem('experimental', index)"
                          @delete="deleteEvidenceItem('experimental', index)"
                        />
                      </div>
                      <v-alert v-else type="info" variant="tonal" density="compact">
                        No experimental evidence items yet. Add evidence to strengthen your
                        curation.
                      </v-alert>
                    </v-card-text>
                  </v-window-item>

                  <!-- Contradictory Evidence Tab -->
                  <v-window-item value="contradictory">
                    <v-card-text>
                      <div class="d-flex justify-space-between align-center mb-4">
                        <div class="text-subtitle-2">Contradictory Evidence Items</div>
                        <v-btn
                          color="primary"
                          variant="outlined"
                          size="small"
                          @click="addEvidenceItem('contradictory')"
                        >
                          <v-icon start>mdi-plus</v-icon>
                          Add Evidence
                        </v-btn>
                      </div>

                      <!-- Contradictory Evidence List -->
                      <div v-if="contradictoryEvidence.length > 0" class="evidence-list">
                        <EvidenceItemCard
                          v-for="(item, index) in contradictoryEvidence"
                          :key="item.id || index"
                          :evidence="item"
                          :index="index"
                          @edit="editEvidenceItem('contradictory', index)"
                          @delete="deleteEvidenceItem('contradictory', index)"
                        />
                      </div>
                      <v-alert v-else type="info" variant="tonal" density="compact">
                        No contradictory evidence items yet. Document evidence against association
                        if applicable.
                      </v-alert>
                    </v-card-text>
                  </v-window-item>
                </v-window>
              </v-card>

              <!-- Curator Notes -->
              <v-card variant="outlined">
                <v-card-title class="text-subtitle-1">Curator Notes</v-card-title>
                <v-card-text>
                  <v-textarea
                    v-model="formData.curator_notes"
                    label="Additional Notes"
                    hint="Internal notes for reviewers (optional)"
                    variant="outlined"
                    rows="4"
                    auto-grow
                  />
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Score Preview Sidebar (Right) -->
            <v-col cols="12" lg="4">
              <v-card variant="outlined" class="sticky-sidebar">
                <ScorePreview :evidence-items="allEvidenceItems" />

                <!-- Score Details -->
                <v-divider class="my-2" />
                <v-card-text>
                  <div class="text-caption text-medium-emphasis mb-2">Evidence Summary</div>
                  <v-row dense>
                    <v-col cols="6">
                      <v-card variant="tonal" color="primary">
                        <v-card-text class="text-center pa-2">
                          <div class="text-h6">{{ geneticEvidenceCount }}</div>
                          <div class="text-caption">Genetic</div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col cols="6">
                      <v-card variant="tonal" color="secondary">
                        <v-card-text class="text-center pa-2">
                          <div class="text-h6">{{ experimentalEvidenceCount }}</div>
                          <div class="text-caption">Experimental</div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col cols="12">
                      <v-card variant="tonal" color="warning">
                        <v-card-text class="text-center pa-2">
                          <div class="text-h6">{{ contradictoryEvidenceCount }}</div>
                          <div class="text-caption">Contradictory</div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider />

        <!-- Form Actions -->
        <v-card-actions class="px-4 py-3">
          <v-btn variant="outlined" @click="handleCancel">
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
                  @click="undo"
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
                  @click="redo"
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
                :loading="savingDraft"
                aria-label="Save Draft (Ctrl+S)"
                @click="handleSaveDraft"
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
                type="submit"
                :loading="submitting"
                aria-label="Submit Curation (Ctrl+Enter)"
              >
                <v-icon start>mdi-check-circle</v-icon>
                Submit for Review
              </v-btn>
            </template>
            <span>Submit for Review (Ctrl+Enter)</span>
          </v-tooltip>
        </v-card-actions>
      </v-card>
    </v-form>

    <!-- Form Recovery Dialog -->
    <FormRecoveryDialog
      v-model="showRecoveryDialog"
      :recovery-data="recoveryData"
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
      @extend="extendSession"
    />

    <!-- Evidence Item Dialog (for add/edit) -->
    <EvidenceItemDialog
      v-model="showEvidenceDialog"
      :evidence="editingEvidence"
      :evidence-type="evidenceDialogType"
      @save="saveEvidenceItem"
    />
  </ErrorBoundary>
</template>

<script setup>
  /**
   * CurationForm Component
   *
   * Comprehensive gene-disease curation form following ClinGen SOP v11.
   * Integrates all Week 1 infrastructure (form recovery, undo/redo, conflict resolution,
   * session timeout, error boundaries).
   *
   * Features:
   * - Tabbed evidence sections (Genetic, Experimental, Contradictory)
   * - Real-time ClinGen score calculation
   * - Evidence item management (add/edit/delete)
   * - Auto-save every 5 seconds
   * - Optimistic locking with conflict resolution
   * - Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Shift+Z, Ctrl+Enter, Esc)
   *
   * @example
   * <CurationForm
   *   :curation-id="curationId"
   *   :scope-id="scopeId"
   *   @success="handleSuccess"
   *   @cancel="handleCancel"
   * />
   */

  import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
  import { useRouter } from 'vue-router'
  import { useCurationsStore } from '@/stores/curations'
  import { useFormRecovery } from '@/composables/useFormRecovery'
  import { useHistory } from '@/composables/useHistory'
  import { useOptimisticLocking } from '@/composables/useOptimisticLocking'
  import { useSessionTimeout } from '@/composables/useSessionTimeout'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import FormRecoveryDialog from '@/components/dialogs/FormRecoveryDialog.vue'
  import ConflictResolutionDialog from '@/components/dialogs/ConflictResolutionDialog.vue'
  import SessionTimeoutWarning from '@/components/dialogs/SessionTimeoutWarning.vue'
  import ValidatedInput from '@/components/ValidatedInput.vue'
  import HPOInput from '@/components/evidence/HPOInput.vue'
  import ScorePreview from '@/components/evidence/ScorePreview.vue'
  import EvidenceItemCard from '@/components/evidence/EvidenceItemCard.vue'
  import EvidenceItemDialog from '@/components/dialogs/EvidenceItemDialog.vue'

  const props = defineProps({
    curationId: {
      type: String,
      default: null
    },
    scopeId: {
      type: String,
      required: true
    },
    precurationId: {
      type: String,
      default: null
    }
  })

  const emit = defineEmits(['success', 'cancel'])

  const logger = useLogger()
  const router = useRouter()
  const curationsStore = useCurationsStore()
  const notificationsStore = useNotificationsStore()

  // Form state
  const formRef = ref(null)
  const formData = ref({
    gene_symbol: '',
    disease_name: '',
    hpo_terms: [],
    curator_notes: '',
    evidence_items: []
  })

  const activeTab = ref('genetic')
  const isDraft = ref(true)
  const isLoading = ref(false)
  const savingDraft = ref(false)
  const submitting = ref(false)
  const lockVersion = ref(0)

  // Evidence dialog state
  const showEvidenceDialog = ref(false)
  const evidenceDialogType = ref('genetic')
  const editingEvidence = ref(null)
  const editingEvidenceIndex = ref(null)

  // Week 1 Infrastructure Integration

  // 1. Form Recovery (auto-save every 5 seconds)
  const {
    showRecoveryDialog,
    recoveryData,
    lastSaved,
    restoreRecovery,
    discardRecovery,
    clearRecovery
  } = useFormRecovery(`curation-${props.curationId || 'new'}`, formData, {
    saveInterval: 5000,
    maxAge: 24 * 60 * 60 * 1000
  })

  // 2. Undo/Redo System
  const {
    canUndo,
    canRedo,
    recordAction,
    undo: undoAction,
    redo: redoAction,
    clearHistory
  } = useHistory(`curation-${props.curationId || 'new'}`, state => {
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

  // 3. Optimistic Locking (store handles locking, we use this for conflict UI)
  const { conflictDetected, conflictData, resolveConflict } = useOptimisticLocking()

  // 4. Session Timeout
  const { showTimeoutWarning, timeRemaining, extendSession } = useSessionTimeout()

  // Evidence filtering by type
  const geneticEvidence = computed(() =>
    formData.value.evidence_items.filter(e => e.evidence_type === 'genetic')
  )

  const experimentalEvidence = computed(() =>
    formData.value.evidence_items.filter(e => e.evidence_type === 'experimental')
  )

  const contradictoryEvidence = computed(() =>
    formData.value.evidence_items.filter(e => e.evidence_type === 'contradictory')
  )

  // Evidence counts
  const geneticEvidenceCount = computed(() => geneticEvidence.value.length)
  const experimentalEvidenceCount = computed(() => experimentalEvidence.value.length)
  const contradictoryEvidenceCount = computed(() => contradictoryEvidence.value.length)

  // All evidence items for scoring
  const allEvidenceItems = computed(() => formData.value.evidence_items)

  /**
   * Load existing curation data using store
   */
  async function loadCuration() {
    if (!props.curationId) return

    isLoading.value = true
    try {
      const curation = await curationsStore.fetchCurationById(props.curationId)
      if (curation) {
        formData.value = {
          gene_symbol: curation.gene_symbol || '',
          disease_name: curation.disease_name || '',
          hpo_terms: curation.hpo_terms || [],
          curator_notes: curation.curator_notes || '',
          evidence_items: curation.evidence_items || []
        }
        lockVersion.value = curation.lock_version || 0
        isDraft.value = curation.status === 'draft'

        logger.info('Curation loaded via store', { curation_id: props.curationId })
      }
    } catch (error) {
      logger.error('Failed to load curation', { error: error.message })
      notificationsStore.addToast('Failed to load curation', 'error')
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Evidence Item Management
   */
  function addEvidenceItem(type) {
    evidenceDialogType.value = type
    editingEvidence.value = {
      evidence_type: type,
      evidence_category: '',
      description: '',
      pmids: [],
      computed_score: 0
    }
    editingEvidenceIndex.value = null
    showEvidenceDialog.value = true
  }

  function editEvidenceItem(type, index) {
    const allItems = formData.value.evidence_items.filter(e => e.evidence_type === type)
    evidenceDialogType.value = type
    editingEvidence.value = { ...allItems[index] }
    editingEvidenceIndex.value = formData.value.evidence_items.findIndex(e => e === allItems[index])
    showEvidenceDialog.value = true
  }

  function saveEvidenceItem(evidenceItem) {
    if (editingEvidenceIndex.value !== null) {
      // Update existing
      formData.value.evidence_items[editingEvidenceIndex.value] = evidenceItem
    } else {
      // Add new
      formData.value.evidence_items.push(evidenceItem)
    }
    showEvidenceDialog.value = false
    logger.debug('Evidence item saved', { type: evidenceItem.evidence_type })
  }

  function deleteEvidenceItem(type, index) {
    const allItems = formData.value.evidence_items.filter(e => e.evidence_type === type)
    const itemToDelete = allItems[index]
    const globalIndex = formData.value.evidence_items.findIndex(e => e === itemToDelete)

    if (globalIndex !== -1) {
      formData.value.evidence_items.splice(globalIndex, 1)
      logger.debug('Evidence item deleted', { type, index })
    }
  }

  /**
   * Save draft using store
   */
  async function handleSaveDraft() {
    savingDraft.value = true
    try {
      const payload = {
        evidence_data: formData.value,
        lock_version: lockVersion.value
      }

      if (props.curationId) {
        // Use saveDraft for auto-save (doesn't require lock_version check)
        const updated = await curationsStore.saveDraft(props.curationId, payload)
        if (updated) {
          lockVersion.value = updated.lock_version
          logger.info('Curation draft updated via store', { curation_id: props.curationId })
        }
      } else {
        // Create new curation
        const created = await curationsStore.createCuration({
          gene_id: formData.value.gene_id,
          scope_id: props.scopeId,
          workflow_pair_id: formData.value.workflow_pair_id,
          evidence_data: formData.value
        })
        logger.info('Curation draft created via store', { curation_id: created.id })
        router.push(`/curations/${created.id}/edit`)
      }

      notificationsStore.addToast('Draft saved successfully', 'success')
      clearRecovery()
    } catch (error) {
      if (error.response?.status !== 409) {
        logger.error('Failed to save draft', { error: error.message })
        notificationsStore.addToast('Failed to save draft', 'error')
      }
    } finally {
      savingDraft.value = false
    }
  }

  /**
   * Submit curation using store
   */
  async function handleSubmit() {
    const { valid } = await formRef.value.validate()
    if (!valid) {
      notificationsStore.addToast('Please fix validation errors', 'warning')
      return
    }

    submitting.value = true
    try {
      if (props.curationId) {
        // Submit existing curation
        await curationsStore.submitCuration(props.curationId, {
          lock_version: lockVersion.value,
          notes: formData.value.curator_notes
        })
      } else {
        // Create and submit new curation
        const created = await curationsStore.createCuration({
          gene_id: formData.value.gene_id,
          scope_id: props.scopeId,
          workflow_pair_id: formData.value.workflow_pair_id,
          evidence_data: formData.value
        })
        // Then submit it
        await curationsStore.submitCuration(created.id, {
          lock_version: 0,
          notes: formData.value.curator_notes
        })
      }

      logger.info('Curation submitted via store', { curation_id: props.curationId })
      notificationsStore.addToast('Curation submitted successfully!', 'success')
      clearRecovery()
      clearHistory()
      emit('success')
    } catch (error) {
      // Check for conflict error from store
      if (curationsStore.isConflictError) {
        // Conflict is handled by the store error state
        logger.warn('Curation submission conflict detected')
      } else {
        logger.error('Failed to submit curation', { error: error.message })
        notificationsStore.addToast('Failed to submit curation', 'error')
      }
    } finally {
      submitting.value = false
    }
  }

  /**
   * Handle conflict resolution
   */
  function handleConflictResolution(resolution) {
    const resolved = resolveConflict(resolution)

    if (resolution === 'use_theirs') {
      formData.value = { ...resolved.theirChanges }
      lockVersion.value = resolved.theirVersion
    } else if (resolution === 'use_mine') {
      lockVersion.value = resolved.theirVersion
    }

    logger.info('Conflict resolved', { resolution })
  }

  /**
   * Cancel editing
   */
  function handleCancel() {
    if (confirm('Discard unsaved changes?')) {
      clearRecovery()
      clearHistory()
      emit('cancel')
    }
  }

  /**
   * Handle gene symbol blur
   */
  function handleGeneBlur() {
    logger.debug('Gene validated', { gene_symbol: formData.value.gene_symbol })
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
      handleSubmit()
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
    const previousState = undoAction()
    if (previousState) {
      logger.debug('Undo performed')
    }
  }

  function redo() {
    const nextState = redoAction()
    if (nextState) {
      logger.debug('Redo performed')
    }
  }

  /**
   * Format relative time (e.g., "2 minutes ago")
   */
  function formatRelativeTime(timestamp) {
    if (!timestamp) return ''

    const now = new Date()
    const then = new Date(timestamp)
    const diffMs = now - then
    const diffSec = Math.floor(diffMs / 1000)

    if (diffSec < 60) return 'just now'
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
    return `${Math.floor(diffSec / 86400)}d ago`
  }

  // Lifecycle
  onMounted(() => {
    loadCuration()
    logger.debug('CurationForm mounted', { curation_id: props.curationId })
  })

  onBeforeUnmount(() => {
    logger.debug('CurationForm unmounted')
  })
</script>

<style scoped>
  .evidence-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sticky-sidebar {
    position: sticky;
    top: 80px;
    max-height: calc(100vh - 100px);
    overflow-y: auto;
  }

  /* Smooth tab transitions */
  .v-window {
    overflow: visible;
  }

  /* Keyboard shortcut tooltips */
  kbd {
    padding: 2px 6px;
    background: #f5f5f5;
    border: 1px solid #ccc;
    border-radius: 3px;
    font-family: monospace;
    font-size: 0.875em;
  }
</style>
