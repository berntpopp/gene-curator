<template>
  <v-container fluid class="clingen-curation-form pa-0">
    <!-- Header Section -->
    <CurationHeader
      :gene="gene"
      :disease="diseaseEntity"
      :classification="currentClassification"
      :moi="modeOfInheritance"
      :sop-version="sopVersion"
      :expert-panel="expertPanel"
      :curation-id="curationId"
      :status="status"
    />

    <v-divider class="my-4" />

    <!-- Main Content with Sidebar -->
    <v-row>
      <!-- Main Form Area -->
      <v-col cols="12" lg="9">
        <v-card>
          <!-- Tab Navigation -->
          <v-tabs v-model="activeTab" bg-color="primary" slider-color="white">
            <v-tab value="summary">
              <v-icon start>mdi-file-document-outline</v-icon>
              Summary
            </v-tab>
            <v-tab value="genetic">
              <v-icon start>mdi-dna</v-icon>
              Genetic Evidence
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
              <v-icon start>mdi-flask</v-icon>
              Experimental Evidence
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
            <v-tab value="contradictory">
              <v-icon start>mdi-alert-circle-outline</v-icon>
              Contradictory
            </v-tab>
            <v-tab value="lumping">
              <v-icon start>mdi-call-split</v-icon>
              Lumping & Splitting
            </v-tab>
          </v-tabs>

          <v-card-text class="pa-6">
            <v-window v-model="activeTab">
              <!-- Summary Tab -->
              <v-window-item value="summary">
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

          <!-- Form Actions -->
          <v-divider />
          <v-card-actions class="pa-4">
            <v-btn variant="outlined" @click="handleCancel">
              <v-icon start>mdi-close</v-icon>
              Cancel
            </v-btn>
            <v-spacer />
            <v-btn
              color="secondary"
              variant="outlined"
              :loading="saving"
              :disabled="readonly"
              @click="handleSaveDraft"
            >
              <v-icon start>mdi-content-save</v-icon>
              Save Draft
            </v-btn>
            <v-btn
              color="primary"
              :loading="submitting"
              :disabled="!canSubmit || readonly"
              @click="handleSubmit"
            >
              <v-icon start>mdi-check</v-icon>
              Submit for Review
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Score Sidebar -->
      <v-col cols="12" lg="3">
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

          <!-- Quick Actions -->
          <v-card class="mt-4" variant="outlined">
            <v-card-title class="text-subtitle-1">
              <v-icon start size="small">mdi-lightning-bolt</v-icon>
              Quick Actions
            </v-card-title>
            <v-card-text class="py-2">
              <v-btn
                block
                variant="tonal"
                color="primary"
                size="small"
                class="mb-2"
                @click="addCaseLevelEvidence"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Case-Level Evidence
              </v-btn>
              <v-btn
                block
                variant="tonal"
                color="secondary"
                size="small"
                @click="addExperimentalEvidence"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Experimental Evidence
              </v-btn>
            </v-card-text>
          </v-card>

          <!-- Keyboard Shortcuts -->
          <v-card class="mt-4" variant="text">
            <v-card-text class="text-caption text-medium-emphasis">
              <div><kbd>Ctrl</kbd>+<kbd>S</kbd> Save Draft</div>
              <div><kbd>Ctrl</kbd>+<kbd>Enter</kbd> Submit</div>
              <div><kbd>Ctrl</kbd>+<kbd>Z</kbd> Undo</div>
            </v-card-text>
          </v-card>
        </div>
      </v-col>
    </v-row>
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

  import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import CurationHeader from './CurationHeader.vue'
  import SummarySection from './sections/SummarySection.vue'
  import GeneticEvidenceSection from './sections/GeneticEvidenceSection.vue'
  import ExperimentalEvidenceSection from './sections/ExperimentalEvidenceSection.vue'
  import ContradictoryEvidenceSection from './sections/ContradictoryEvidenceSection.vue'
  import LumpingSplittingSection from './sections/LumpingSplittingSection.vue'
  import ScoreSummary from './ScoreSummary.vue'
  import { createEmptyExperimentalEvidence, createEmptyGeneticEvidence } from './evidenceDefaults'
  import { calculateExperimentalScore, calculateGeneticScore, classifyScore } from './scoring'
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
      precurationData?: PrecurationData
      initialData?: Partial<ClinGenEvidenceData>
      readonly?: boolean
      status?: string
    }>(),
    {
      curationId: null,
      precurationData: () => ({}),
      initialData: () => ({}),
      readonly: false,
      status: 'draft'
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
  const saving = ref(false)
  const submitting = ref(false)

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

  const sopVersion = computed(() => 'SOP v11')
  const expertPanel = computed(() => props.precurationData?.expert_panel || 'Not specified')

  const hasContradictoryEvidence = computed(
    () => (evidenceData.value.contradictory_evidence?.length ?? 0) > 0
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
    classifyScore(scores.value.total, hasContradictoryEvidence.value)
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

  function updateEvidenceSummary(summary: string) {
    evidenceData.value.evidence_summary = summary
    emitUpdate()
  }

  function emitUpdate() {
    emit('update:model-value', { ...evidenceData.value })
  }

  async function handleSaveDraft() {
    saving.value = true
    try {
      emit('save-draft', evidenceData.value)
    } finally {
      saving.value = false
    }
  }

  async function handleSubmit() {
    submitting.value = true
    try {
      emit('submit', evidenceData.value)
    } finally {
      submitting.value = false
    }
  }

  function handleCancel() {
    emit('cancel')
  }

  function addCaseLevelEvidence() {
    activeTab.value = 'genetic'
    // Will be handled by GeneticEvidenceSection
  }

  function addExperimentalEvidence() {
    activeTab.value = 'experimental'
    // Will be handled by ExperimentalEvidenceSection
  }

  // Keyboard shortcuts
  function handleKeydown(event: KeyboardEvent) {
    const ctrl = event.ctrlKey || event.metaKey

    if (ctrl && event.key === 's') {
      event.preventDefault()
      handleSaveDraft()
    } else if (ctrl && event.key === 'Enter') {
      event.preventDefault()
      if (canSubmit.value) handleSubmit()
    }
  }

  // Initialize from props
  watch(
    () => props.initialData,
    newData => {
      if (newData && Object.keys(newData).length > 0) {
        evidenceData.value = {
          ...evidenceData.value,
          ...newData
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
    background: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.85em;
  }
</style>
