<template>
  <v-container fluid class="clingen-curation-form pa-0">
    <!-- Header Section (the workspace frame has its own) -->
    <CurationHeader
      v-if="!frame"
      :gene="gene"
      :disease="diseaseEntity"
      :classification="currentClassification"
      :moi="modeOfInheritance"
      :schema="schema"
      :expert-panel="expertPanel"
      :curation-id="curationId"
      :status="status"
    />

    <v-divider v-if="!frame" class="my-4" />

    <!-- Main Content with Sidebar -->
    <v-row>
      <!-- Main Form Area -->
      <v-col cols="12" :lg="frame ? 12 : 9">
        <v-card>
          <!-- Tab Navigation -->
          <v-tabs v-model="activeTab" bg-color="primary" slider-color="white" show-arrows>
            <v-tab value="summary">Summary</v-tab>
            <v-tab value="genetic">
              Genetic
              <v-chip
                v-if="scores.genetic > 0"
                size="small"
                color="white"
                variant="flat"
                class="ml-2"
              >
                {{ scores.genetic.toFixed(2) }}
              </v-chip>
            </v-tab>
            <v-tab value="experimental">
              Experimental
              <v-chip
                v-if="scores.experimental > 0"
                size="small"
                color="white"
                variant="flat"
                class="ml-2"
              >
                {{ scores.experimental.toFixed(2) }}
              </v-chip>
            </v-tab>
            <v-tab value="contradictory">Contradictory</v-tab>
            <v-tab value="lumping">Lumping</v-tab>
          </v-tabs>

          <v-card-text class="pa-6">
            <v-window v-model="activeTab">
              <!-- Summary Tab -->
              <v-window-item value="summary">
                <v-checkbox
                  :model-value="!!evidenceData.replicated_over_time"
                  :disabled="readonly"
                  density="compact"
                  hide-details
                  label="Replicated over time (≥2 independent publications, >3 years)"
                  @update:model-value="updateReplicated"
                />
                <SummarySection
                  :evidence-summary="evidenceData.evidence_summary"
                  :genetic-score="scores.genetic"
                  :experimental-score="scores.experimental"
                  :total-score="scores.total"
                  :classification="currentClassification"
                  @update:evidence-summary="updateEvidenceSummary"
                />
              </v-window-item>

              <!-- Genetic Evidence Tab -->
              <v-window-item value="genetic">
                <GeneticEvidenceSection
                  v-model="evidenceData.genetic_evidence"
                  :readonly="readonly"
                  :moi="modeOfInheritance"
                  @update:model-value="handleGeneticUpdate"
                />
              </v-window-item>

              <!-- Experimental Evidence Tab -->
              <v-window-item value="experimental">
                <ExperimentalEvidenceSection
                  v-model="evidenceData.experimental_evidence"
                  :readonly="readonly"
                  @update:model-value="handleExperimentalUpdate"
                />
              </v-window-item>

              <!-- Contradictory Evidence Tab -->
              <v-window-item value="contradictory">
                <ContradictoryEvidenceSection
                  v-model="evidenceData.contradictory_evidence"
                  :readonly="readonly"
                  @update:model-value="handleContradictoryUpdate"
                />
              </v-window-item>

              <!-- Lumping & Splitting Tab -->
              <v-window-item value="lumping">
                <LumpingSplittingSection :precuration-data="precurationData" :readonly="true" />
              </v-window-item>
            </v-window>
          </v-card-text>

          <!-- Form Actions (the workspace frame has them in its header) -->
          <v-divider v-if="!frame" />
          <v-card-actions v-if="!frame" class="pa-4 flex-wrap ga-2">
            <v-btn variant="outlined" @click="handleCancel">
              <v-icon start>mdi-close</v-icon>
              Cancel
            </v-btn>
            <v-spacer />
            <v-chip v-if="lastSaved" color="success" size="small" variant="outlined" class="mr-2">
              <v-icon start size="small">mdi-content-save</v-icon>
              Saved {{ savedTime }}
            </v-chip>
            <v-btn
              variant="outlined"
              :loading="saving"
              :disabled="readonly"
              @click="handleSaveDraft"
            >
              <v-icon start>mdi-content-save</v-icon>
              Save draft
            </v-btn>
            <v-btn
              color="primary"
              :loading="submitting"
              :disabled="!canSubmit || readonly"
              @click="requestSubmit"
            >
              <v-icon start>mdi-check</v-icon>
              Submit for review
            </v-btn>
          </v-card-actions>
          <div
            v-if="!frame && !canSubmit && !readonly"
            class="text-body-small text-medium-emphasis px-4 pb-3 text-end"
          >
            Add at least one scored evidence item to submit
          </div>
        </v-card>
      </v-col>

      <!-- Score Sidebar (the frame's score panel replaces it) -->
      <v-col v-if="!frame" cols="12" lg="3">
        <div class="sticky-sidebar">
          <ScoreSummary
            :genetic-score="scores.genetic"
            :experimental-score="scores.experimental"
            :total-score="scores.total"
            :classification="currentClassification"
            :has-contradictory="hasContradictoryEvidence"
            :genetic-breakdown="scores.geneticBreakdown"
            :experimental-breakdown="scores.experimentalBreakdown"
          />

          <!-- Keyboard Shortcuts -->
          <v-card class="mt-4" variant="text">
            <v-card-text class="text-body-small text-medium-emphasis">
              <div><kbd>Ctrl</kbd>+<kbd>S</kbd> Save Draft</div>
              <div><kbd>Ctrl</kbd>+<kbd>Enter</kbd> Submit</div>
            </v-card-text>
          </v-card>
        </div>
      </v-col>
    </v-row>

    <BaseDialog v-model="showSubmitDialog" size="md" title="Submit for review">
      Submit this curation for <strong>{{ gene?.symbol }}</strong> for review? It is locked for
      editing until the review is complete.
      <template #actions>
        <v-btn variant="text" @click="showSubmitDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="elevated" :loading="submitting" @click="confirmSubmit">
          Submit
        </v-btn>
      </template></BaseDialog
    >
  </v-container>
</template>

<script setup lang="ts">
  /**
   * ClinGenCurationForm
   *
   * ClinGen SOP v11 compliant curation form with:
   * - Tabbed interface matching ClinGen Gene Validity UI
   * - Live scoring sidebar
   * - Genetic evidence (case-level, segregation, case-control)
   * - Experimental evidence (function, functional alteration, models, rescue)
   * - Contradictory evidence
   * - Lumping & Splitting (read-only from precuration)
   */

  import { ref, computed, inject, watch, onMounted, onBeforeUnmount } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import CurationHeader from './CurationHeader.vue'
  import SummarySection from './sections/SummarySection.vue'
  import GeneticEvidenceSection from './sections/GeneticEvidenceSection.vue'
  import ExperimentalEvidenceSection from './sections/ExperimentalEvidenceSection.vue'
  import { hasContent } from './hasContent'
  import ContradictoryEvidenceSection from './sections/ContradictoryEvidenceSection.vue'
  import LumpingSplittingSection from './sections/LumpingSplittingSection.vue'
  import ScoreSummary from './ScoreSummary.vue'
  import { createEmptyExperimentalEvidence, createEmptyGeneticEvidence } from './evidenceDefaults'
  import { normalizeLegacy } from './scoring'
  import { calculateExperimentalScore, calculateGeneticScore, classifyScore } from './scoring'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { WORKSPACE_FRAME } from '@/components/workspace/useWorkspaceFrame'
  import type {
    ClinGenEvidenceData,
    DiseaseInfo,
    EvidenceItem,
    ExperimentalEvidence,
    GeneInfo,
    GeneticEvidence,
    PrecurationData
  } from './types'

  const props = withDefaults(
    defineProps<{
      curationId?: string | null
      gene: GeneInfo
      schema?: { name: string; version: string } | null
      precurationData?: PrecurationData
      initialData?: Partial<ClinGenEvidenceData>
      readonly?: boolean
      status?: string
      saving?: boolean
      submitting?: boolean
      lastSaved?: string | number | null
    }>(),
    {
      curationId: null,
      schema: null,
      precurationData: () => ({}),
      initialData: () => ({}),
      readonly: false,
      status: 'draft',
      saving: false,
      submitting: false,
      lastSaved: null
    }
  )

  const emit = defineEmits<{
    submit: [data: ClinGenEvidenceData]
    'save-draft': [data: ClinGenEvidenceData]
    cancel: []
    'update:model-value': [data: ClinGenEvidenceData]
  }>()

  const logger = useLogger()

  // Form state
  const activeTab = ref('summary')
  const showSubmitDialog = ref(false)
  const savedTime = computed(() => new Date(props.lastSaved ?? 0).toLocaleTimeString())

  // Evidence data structure per ClinGen SOP v11
  const evidenceData = ref<ClinGenEvidenceData>({
    evidence_summary: '',
    genetic_evidence: createEmptyGeneticEvidence(),
    experimental_evidence: createEmptyExperimentalEvidence(),
    contradictory_evidence: []
  })

  // Computed properties from precuration
  const diseaseEntity = computed<DiseaseInfo>(() => ({
    name:
      props.precurationData?.disease_name || props.precurationData?.entity_definition?.disease_name,
    mondo_id: props.precurationData?.mondo_id || props.precurationData?.entity_definition?.mondo_id
  }))

  const modeOfInheritance = computed(
    () =>
      props.precurationData?.mode_of_inheritance ||
      props.precurationData?.entity_definition?.mode_of_inheritance ||
      'Unknown'
  )

  const expertPanel = computed(() => props.precurationData?.expert_panel || 'Not specified')

  const hasContradictoryEvidence = computed(() =>
    hasContent(evidenceData.value.contradictory_evidence)
  )

  // Score calculations
  const scores = computed(() => {
    const genetic = calculateGeneticScore(evidenceData.value.genetic_evidence)
    const experimental = calculateExperimentalScore(evidenceData.value.experimental_evidence)
    const total = Math.min(genetic.total + experimental.total, 18)

    return {
      genetic: Math.min(genetic.total, 12),
      experimental: Math.min(experimental.total, 6),
      total,
      geneticBreakdown: genetic,
      experimentalBreakdown: experimental
    }
  })

  // Classification based on score
  const currentClassification = computed(() =>
    classifyScore(
      scores.value.total,
      hasContradictoryEvidence.value,
      !!evidenceData.value.replicated_over_time
    )
  )

  const canSubmit = computed(() => {
    // Must have at least some genetic evidence
    const ge = evidenceData.value.genetic_evidence
    const caseLevel = ge.case_level

    // Check nested case_level structure for any evidence
    const hasCaseLevelEvidence =
      (caseLevel?.autosomal_dominant_or_x_linked?.predicted_or_proven_null?.length ?? 0) > 0 ||
      (caseLevel?.autosomal_dominant_or_x_linked?.other_variant_type?.length ?? 0) > 0 ||
      (caseLevel?.autosomal_recessive?.predicted_or_proven_null?.length ?? 0) > 0 ||
      (caseLevel?.autosomal_recessive?.other_variant_type?.length ?? 0) > 0

    const hasGenetic = hasCaseLevelEvidence || (ge.segregation?.length ?? 0) > 0

    return hasGenetic && !props.readonly
  })

  // Inside the workspace frame: it shows the score, the entity and the save/submit actions.
  const frame = inject(WORKSPACE_FRAME, null)
  if (frame) {
    frame.attachSubmit({ canSubmit, run: requestSubmit })
    watch(
      [scores, currentClassification, hasContradictoryEvidence],
      () =>
        frame.setScore({
          genetic: scores.value.genetic,
          experimental: scores.value.experimental,
          total: scores.value.total,
          classification: currentClassification.value,
          hasContradictory: hasContradictoryEvidence.value,
          geneticBreakdown: scores.value.geneticBreakdown,
          experimentalBreakdown: scores.value.experimentalBreakdown
        }),
      { immediate: true }
    )
    watch(
      [diseaseEntity, modeOfInheritance],
      () =>
        frame.setMeta({
          disease: diseaseEntity.value.name ?? undefined,
          moi: modeOfInheritance.value
        }),
      { immediate: true }
    )
  }

  // Event handlers
  function handleGeneticUpdate(data: GeneticEvidence) {
    evidenceData.value.genetic_evidence = data
    emitUpdate()
  }

  function handleExperimentalUpdate(data: ExperimentalEvidence) {
    evidenceData.value.experimental_evidence = data
    emitUpdate()
  }

  function handleContradictoryUpdate(data: EvidenceItem[]) {
    evidenceData.value.contradictory_evidence = data
    emitUpdate()
  }

  function updateReplicated(value: boolean | null) {
    evidenceData.value.replicated_over_time = !!value
    emitUpdate()
  }

  function updateEvidenceSummary(summary: string) {
    evidenceData.value.evidence_summary = summary
    emitUpdate()
  }

  function emitUpdate() {
    emit('update:model-value', { ...evidenceData.value })
  }

  // Cells commit on change: blur first so a focused cell's last edit is included
  function commitFocusedCell() {
    ;(document.activeElement as HTMLElement | null)?.blur?.()
  }

  function handleSaveDraft() {
    commitFocusedCell()
    emit('save-draft', evidenceData.value)
  }

  function requestSubmit() {
    commitFocusedCell()
    showSubmitDialog.value = true
  }

  function confirmSubmit() {
    showSubmitDialog.value = false
    emit('submit', evidenceData.value)
  }

  function handleCancel() {
    emit('cancel')
  }

  // Keyboard shortcuts
  function handleKeydown(event: KeyboardEvent) {
    if (props.readonly) return
    const ctrl = event.ctrlKey || event.metaKey

    if (ctrl && event.key === 's' && !frame) {
      event.preventDefault()
      handleSaveDraft()
    } else if (ctrl && event.key === 'Enter') {
      event.preventDefault()
      if (canSubmit.value) requestSubmit()
    }
  }

  // Initialize from props
  watch(
    () => props.initialData,
    newData => {
      if (newData && Object.keys(newData).length > 0) {
        evidenceData.value = {
          ...evidenceData.value,
          ...normalizeLegacy(newData)
        }
      }
    },
    { immediate: true }
  )

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
    logger.info('ClinGenCurationForm mounted', {
      curationId: props.curationId,
      gene: props.gene?.symbol
    })
  })

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown)
  })
</script>

<style scoped>
  .clingen-curation-form {
    max-width: 1600px;
    margin: 0 auto;
  }

  .sticky-sidebar {
    position: sticky;
    top: 80px;
    max-height: calc(100vh - 100px);
    overflow-y: auto;
  }

  kbd {
    padding: 2px 6px;
    background: rgba(var(--v-theme-on-surface), 0.1);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 0.85em;
  }
</style>
