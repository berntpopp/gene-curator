<template>
  <ErrorBoundary @error="handleFormError">
    <!-- Schema and curation not loaded yet: one skeleton, no score card or verdict -->
    <v-skeleton-loader v-if="!ready" type="card" />

    <v-form v-else @submit.prevent="handleSubmit" @keydown="handleKeydown">
      <v-card class="overflow-visible">
        <!-- Header and actions: the workspace frame has its own -->
        <template v-if="!frame">
          <v-card-title class="d-flex align-center flex-wrap ga-2 text-wrap">
            <span>{{ gene?.symbol }} - {{ schema?.name || 'Curation' }}</span>
            <v-chip v-if="isDraft" color="warning" size="small" class="ml-2"> Draft </v-chip>
            <v-spacer />
            <v-chip v-if="savedAt" color="success" size="small" variant="outlined">
              <v-icon start size="small">mdi-content-save</v-icon>
              Saved {{ formatRelativeTime(savedAt) }}
            </v-chip>
          </v-card-title>
          <v-divider />
        </template>

        <v-card-text>
          <DiseaseCorrection v-if="diseaseGap" :save="saveForm" @corrected="onCorrected" />
          <!-- Rendered and validated from the version the curation is pinned to -->
          <DynamicForm
            v-if="version"
            :schema-id="schemaId"
            :definition="version.snapshot"
            :methodology-version-id="version.id"
            :initial-data="evidenceData"
            :title="schema?.name || 'Curation Form'"
            :readonly="readonly"
            hide-scoring
            hide-actions
            @update:model-value="handleEvidenceChange"
            @validation-change="handleValidationChange"
            @validation-pending="frame?.setScorePending($event)"
            @submit="requestSubmit"
            @save-draft="handleSaveDraft"
          >
            <template #section="{ section }">
              <ScoreSummary
                v-if="section.component === 'ScoreSummary' && score"
                :scores="score"
                :classification="score.classification"
              />
              <LumpingSplittingSection
                v-else-if="section.component === 'LumpingSplittingSection'"
                :precuration-data="precurationData"
                readonly
              />
            </template>
          </DynamicForm>

          <v-alert v-else type="warning" variant="tonal">
            <template #prepend>
              <v-icon>mdi-alert</v-icon>
            </template>
            No schema assigned to this curation. Please contact an administrator.
          </v-alert>

          <!-- A new curation sends the call with its create (a re-curation keeps the source's) -->
          <CuratorClassificationField
            v-if="version"
            v-model="curatorCall"
            :calculated="score?.classification ?? curationsStore.currentCuration?.computed_verdict"
            :choices="curationsStore.currentCuration?.classification_choices"
            :readonly="readonly"
          />
        </v-card-text>

        <template v-if="!frame">
          <v-divider />
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
            @submit="requestSubmit"
            @cancel="handleCancel"
          />
        </template>
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

<script setup lang="ts">
  /**
   * SchemaDrivenCurationForm
   *
   * Schema-agnostic curation form: renders and validates the methodology version the curation
   * is pinned to (the schema's latest for a new one); the score is the backend preview.
   *
   * Key Features:
   * - Renders any schema (ClinGen, GenCC, custom) from config
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

  import { ref, computed, inject, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
  import { useSchemasStore } from '@/stores/schemas'
  import { useCurationsStore } from '@/stores/curations'
  import { usePrecurationsStore } from '@/stores/precurations'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useFormRecovery } from '@/composables/useFormRecovery'
  import { recoveryVersion } from '@/utils/formRecoveryStorage'
  import { useHistory } from '@/composables/useHistory'
  import { useLogger } from '@/composables/useLogger'
  import { migrateLegacyFormat, isLegacyFormat } from '@/utils/evidenceDataMigration'
  import type { Schema } from '@/types/api'
  import type { ApiErrorLike, PrecurationData } from './types'
  import { useCurationSubmission, type EvidenceData } from './useCurationSubmission'
  import { useDiseaseGap } from './useDiseaseGap'
  import DiseaseCorrection from './DiseaseCorrection.vue'
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import { hasContent, hasDisputingRow } from './hasContent'
  import { scoreSnapshot } from './scorePreview'
  import FormRecoveryDialog from '@/components/FormRecoveryDialog.vue'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import FormActions from '@/components/forms/FormActions.vue'
  import ScoreSummary from './ScoreSummary.vue'
  import LumpingSplittingSection from './LumpingSplittingSection.vue'
  import CuratorClassificationField, { type CuratorCall } from './CuratorClassificationField.vue'
  import { unexplainedOverride } from './curatorCall'
  import { useConfirm } from '@/composables/useConfirm'
  import { pmidsIn, usePmidLookup } from '@/composables/usePmidLookup'
  import { WORKSPACE_FRAME, type ScoreSnapshot } from '@/components/workspace/useWorkspaceFrame'

  type CurationSchema = Schema<'CurationSchema'>

  const props = withDefaults(
    defineProps<{
      schemaId: string
      workflowPairId?: string | null
      curationId?: string | null
      scopeId: string
      geneId?: string | null
      gene?: { symbol?: string | null } | null
      readonly?: boolean
      /** Re-curation: a new curation starts from this (active) curation's evidence and disease. */
      prefillFrom?: string | null
    }>(),
    {
      workflowPairId: null,
      curationId: null,
      prefillFrom: null,
      geneId: null,
      gene: null,
      readonly: false
    }
  )

  const emit = defineEmits<{
    submit: [id: string]
    cancel: []
    saved: []
    ready: []
  }>()

  const logger = useLogger()
  const schemasStore = useSchemasStore()
  const curationsStore = useCurationsStore()
  const precurationsStore = usePrecurationsStore()
  const notificationsStore = useNotificationsStore()

  // Form state
  const evidenceData = ref<EvidenceData>({})
  const curatorCall = ref<CuratorCall>({
    curator_classification: null,
    curator_classification_rationale: null
  })
  const isDraft = ref(true)
  const ready = ref(false) // schema and curation (and precuration) have been requested
  const isValid = ref(true) // Updated via validation-change event
  const lockVersion = ref(0)
  const savedAt = ref<number | null>(null) // set by a successful server save

  const version = ref<Schema<'MethodologyVersion'> | null>(null)
  const pinnedVersionId = ref<string | null>(null) // the loaded curation's
  const score = ref<ScoreSnapshot | null>(null) // backend preview of the evidence on screen

  const precurationData = ref<PrecurationData>({})
  const precurationId = ref<string | null>(null) // link for a new curation: the approved one
  const curationStatus = ref('draft')

  // Schema data
  const schema = computed<CurationSchema | undefined>(() =>
    schemasStore.getSchemaById(props.schemaId)
  )

  const hasContradictory = computed(() =>
    hasDisputingRow(evidenceData.value.contradictory_evidence)
  )

  // Form Recovery - schema-aware key to prevent cross-schema data restore; a new curation's
  // draft belongs to its scope and gene, never offered on another gene's new curation
  const recoveryKey = computed(
    () =>
      `curation-${props.curationId || `new-${props.scopeId}-${props.geneId}`}-schema-${props.schemaId}-v2`
  )

  const formRecovery = useFormRecovery(recoveryKey.value, evidenceData, {
    maxAge: 24 * 60 * 60 * 1000
  })
  const {
    showRecoveryDialog,
    recoveryTimestamp,
    recoveryStale,
    restoreRecovery,
    discardRecovery,
    clearRecovery,
    setBaseline,
    markSaved
  } = formRecovery
  let serverVersion: string | null = null // the loaded curation's, for the recovery baseline

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

  // ClinGen SOP: case-level or segregation evidence before review (the server only checks that
  // some evidence exists); applies to definitions with a genetic_evidence block
  const needsGenetic = computed(
    () =>
      !!(version.value?.snapshot.field_definitions as Record<string, unknown> | undefined)
        ?.genetic_evidence
  )
  const hasGenetic = computed(() => {
    const ge = evidenceData.value.genetic_evidence as Record<string, unknown> | undefined
    return hasContent(ge?.case_level) || hasContent(ge?.segregation)
  })

  // Submit eligibility: valid and something entered
  const unexplained = computed(() =>
    unexplainedOverride(
      curatorCall.value,
      score.value?.classification ?? curationsStore.currentCuration?.computed_verdict
    )
  )
  const canSubmit = computed(
    () =>
      isValid.value &&
      !props.readonly &&
      hasContent(evidenceData.value) &&
      (!needsGenetic.value || hasGenetic.value) &&
      !unexplained.value
  )

  // === Persistence (save draft / submit) ===

  const { savingDraft, conflict, submitting, handleSaveDraft, handleSubmit } =
    useCurationSubmission({
      curationId: () => props.curationId,
      geneId: () => props.geneId,
      scopeId: () => props.scopeId,
      workflowPairId: () => props.workflowPairId,
      precurationId: () => precurationId.value,
      evidenceData,
      curatorCall,
      lockVersion,
      canSubmit: () => canSubmit.value,
      clearRecovery,
      markSaved,
      clearHistory,
      onSaved: () => {
        savedAt.value = Date.now()
        emit('saved')
      },
      onSubmit: id => emit('submit', id)
    })

  // Cells commit on blur: let a focused cell's last edit land first
  async function commitFocusedCell() {
    ;(document.activeElement as HTMLElement | null)?.blur?.()
    await nextTick()
  }

  // The workspace frame (when the shell provides one) shows save state, the score and the
  // entity, and owns Ctrl+S and the Save/Submit buttons.
  const frame = inject(WORKSPACE_FRAME, null)
  const saveForm = async () => {
    await commitFocusedCell()
    return handleSaveDraft()
  }
  frame?.attachForm({
    // The leave guard and save state cover the curator's call too (#533)
    evidence: computed(() =>
      curatorCall.value.curator_classification || curatorCall.value.curator_classification_rationale
        ? { ...evidenceData.value, curator_call: curatorCall.value }
        : evidenceData.value
    ),
    saving: savingDraft,
    savedAt,
    conflict,
    save: saveForm
  })
  frame?.attachSubmit({ canSubmit, run: requestSubmit })
  // Unknown PMIDs anywhere in the draft block Submit on every tab, not only in opened tables
  const pmids = usePmidLookup()
  watch(
    () => [...new Set(pmidsIn(evidenceData.value).filter(p => pmids.statusOf(p) === 'notfound'))],
    list =>
      frame?.setBlocker(
        'curation-pmids',
        list.length
          ? `Fix ${list.length} unknown PMID${list.length > 1 ? 's' : ''} before submitting: ` +
              `PMID ${list.join(', ')} not found in Europe PMC`
          : null
      )
  )
  // Submit names what the ClinGen rule still misses, once there is evidence to check
  watch(
    () => needsGenetic.value && !hasGenetic.value && hasContent(evidenceData.value),
    missing =>
      frame?.setBlocker(
        'curation-genetic',
        missing ? 'Add case-level or segregation evidence before submitting' : null
      ),
    { immediate: true }
  )
  watch(unexplained, missing =>
    frame?.setBlocker(
      'curation-rationale',
      missing ? 'Add a rationale for the changed classification before submitting' : null
    )
  )
  // #453: a disease gap the read-only form cannot fix blocks Submit with the reason
  const diseaseGap = useDiseaseGap({
    curationId: () => (props.readonly ? undefined : (props.curationId ?? undefined)),
    linked: () => !!curationsStore.currentCuration?.precuration_id,
    checkAt: savedAt,
    report: message => frame?.setBlocker('curation-disease', message)
  })
  const onCorrected = () => loadCuration().then(() => (savedAt.value = Date.now()))
  watch(score, s => frame?.setScore(s))
  watch(
    precurationData,
    p =>
      frame?.setMeta({
        disease: p.disease_name ?? p.entity_definition?.disease_name ?? undefined,
        moi: p.mode_of_inheritance ?? p.entity_definition?.mode_of_inheritance ?? undefined,
        relationship: p.relationship_type ?? p.entity_definition?.relationship_type ?? undefined
      }),
    { immediate: true }
  )

  async function requestSubmit() {
    // A focused cell's edit may be what allows submitting (#406): commit it before checking.
    // The frame adds its blockers (unknown PMIDs); never submit over a save in flight
    await commitFocusedCell()
    if (savingDraft.value || !(frame ? frame.canSubmit.value : canSubmit.value)) return
    const ok = await confirm({
      title: 'Submit for review',
      text: `Submit this curation for ${props.gene?.symbol ?? 'this gene'} for review? It is locked for editing until the review is complete.`,
      confirmText: 'Submit'
    })
    if (ok) await handleSubmit()
  }

  /**
   * Handle evidence data changes from DynamicForm
   */
  function handleEvidenceChange(newData: EvidenceData) {
    evidenceData.value = { ...newData }
  }

  /**
   * Handle validation state changes from DynamicForm
   * Event-driven pattern instead of defineExpose
   */
  function handleValidationChange(
    validationResult: { is_valid?: boolean; score_calculations?: unknown } | null | undefined
  ) {
    isValid.value = validationResult?.is_valid !== false
    // Live score: validate-evidence (debounced per edit) scores with the pinned point model
    score.value = scoreSnapshot(
      validationResult?.score_calculations,
      hasContradictory.value,
      evidenceData.value
    )
  }

  /**
   * Handle form-level errors from ErrorBoundary
   */
  function handleFormError(error: Error) {
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
  function handleKeydown(event: KeyboardEvent) {
    if (props.readonly) return
    const ctrl = event.ctrlKey || event.metaKey

    if (ctrl && event.key === 's' && !frame) {
      event.preventDefault()
      handleSaveDraft()
    } else if (ctrl && event.key === 'Enter') {
      event.preventDefault()
      requestSubmit()
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

  const { confirm } = useConfirm()

  /**
   * Cancel editing
   */
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
   * Load precuration data for curation form
   * - For existing curations: Load via precuration_id link
   * - For new curations: Find approved precuration for gene+scope
   */
  async function loadPrecurationData() {
    try {
      // Case 1: Existing curation with linked precuration
      if (props.curationId) {
        const curation = curationsStore.currentCuration
        if (curation?.precuration_id) {
          const precuration = await precurationsStore.fetchPrecurationById(curation.precuration_id)
          if (precuration) {
            precurationData.value = { ...precuration.evidence_data, id: precuration.id }
            logger.debug('Loaded precuration data for existing curation', {
              precuration_id: curation.precuration_id
            })
          }
        }
        return
      }

      // Case 2a: Re-curation - the source's own disease entity (#530), set by loadPrefill
      if (precurationId.value) {
        const linked = await precurationsStore.fetchPrecurationById(precurationId.value)
        precurationData.value = { ...(linked?.evidence_data ?? {}), id: precurationId.value }
        return
      }

      // Case 2b: New curation - find approved precuration for gene+scope
      if (props.geneId && props.scopeId) {
        const approvedPrecuration = await precurationsStore.fetchCurationPrecuration(
          props.geneId,
          props.scopeId
        )
        if (approvedPrecuration?.status === 'approved') {
          // Link the new curation (re-curations too): a source's old link may no longer be approved
          precurationId.value = approvedPrecuration.id
          const fullPrecuration = await precurationsStore.fetchPrecurationById(
            approvedPrecuration.id
          )
          precurationData.value = {
            ...(fullPrecuration?.evidence_data ?? {}),
            id: approvedPrecuration.id
          }

          logger.debug('Loaded precuration data for new curation', {
            precuration_id: approvedPrecuration.id,
            disease_name: precurationData.value.disease_name,
            mondo_id: precurationData.value.mondo_id
          })
        }
      }
    } catch (error) {
      logger.warn('Failed to load precuration data', { error: (error as ApiErrorLike).message })
      // Non-fatal - continue without precuration data
    }
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
   * Load existing curation data
   */
  async function loadCuration() {
    if (!props.curationId) return

    try {
      // The parent view already fetched it; avoid a second /curations/:id
      const loaded = curationsStore.currentCuration
      const curation =
        loaded?.id === props.curationId
          ? loaded
          : await curationsStore.fetchCurationById(props.curationId)
      if (curation) {
        // Auto-migrate legacy format if needed
        if (isLegacyFormat(curation.evidence_data)) {
          logger.info('Migrating legacy evidence_data format', { curationId: props.curationId })
          evidenceData.value = migrateLegacyFormat(curation.evidence_data) ?? {}
        } else {
          evidenceData.value = curation.evidence_data || {}
        }

        serverVersion = recoveryVersion(curation)
        pinnedVersionId.value = curation.methodology_version_id ?? null
        lockVersion.value = curation.lock_version || 0
        curatorCall.value = {
          curator_classification: curation.curator_classification ?? null,
          curator_classification_rationale: curation.curator_classification_rationale ?? null
        }
        isDraft.value = curation.status === 'draft'
        curationStatus.value = curation.status || 'draft'

        // The linked precuration (disease entity, lumping and splitting)
        if (curation.precuration_id) {
          await loadPrecurationData()
        }
      }
    } catch (error) {
      logger.error('Failed to load curation', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast('Failed to load curation', 'error')
    }
  }

  /** Re-curation: copy the active curation's evidence into the new draft. */
  async function loadPrefill() {
    if (props.curationId || !props.prefillFrom) return
    try {
      const source = await curationsStore.fetchCurationById(props.prefillFrom)
      // The disease lives in the evidence (or the precuration): copying the resolved fields duplicated it
      evidenceData.value = { ...(source.evidence_data ?? {}) }
      // Approving an unchanged re-curation must publish the same call, not the calculated one
      curatorCall.value = {
        curator_classification: source.curator_classification ?? null,
        curator_classification_rationale: source.curator_classification_rationale ?? null
      }
      // A gene may hold several disease entities: re-curate this one (#530)
      precurationId.value = source.precuration_id ?? null
    } catch (error) {
      logger.error('Failed to load re-curation source', {
        error: (error as ApiErrorLike).message
      })
      notificationsStore.addToast('Failed to load the active curation', 'error')
    }
  }

  /**
   * Load the schema (name) and the version the curation renders with
   */
  async function loadSchema() {
    if (!props.schemaId) return

    try {
      await schemasStore.fetchSchemaById(props.schemaId)
      version.value = await schemasStore.fetchPinnedVersion(pinnedVersionId.value, props.schemaId)
    } catch (error) {
      logger.error('Failed to load schema', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast('Failed to load curation schema', 'error')
    }
  }

  onMounted(async () => {
    await loadCuration()
    await loadSchema()
    await loadPrefill()
    // Also load precuration data for new curations
    if (!props.curationId && props.geneId) {
      await loadPrecurationData()
    }
    if (!props.readonly) void pmids.checkAll(pmidsIn(evidenceData.value))
    ready.value = true
    // The form mounts now and fills in declared defaults: they belong to the loaded state (#470)
    await nextTick()
    // Local drafts are compared with what the form now shows; none until the saved one loaded
    if (!props.curationId || serverVersion) setBaseline(evidenceData.value, serverVersion)
    emit('ready')
    logger.debug('SchemaDrivenCurationForm mounted', {
      schemaId: props.schemaId,
      curationId: props.curationId,
      hasPrecurationData: Object.keys(precurationData.value).length > 0
    })
  })

  onBeforeUnmount(() => {
    logger.debug('SchemaDrivenCurationForm unmounted')
  })
</script>
