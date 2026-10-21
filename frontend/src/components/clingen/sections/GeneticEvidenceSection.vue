<template>
  <div class="genetic-evidence-section">
    <!-- Case-Level Evidence -->
    <v-expansion-panels v-model="expandedPanels" multiple>
      <!-- AD/X-linked Case-Level -->
      <v-expansion-panel value="ad_xl">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="primary">mdi-account</v-icon>
            <span class="font-weight-medium">Case-Level Data - Autosomal Dominant / X-Linked</span>
            <v-spacer />
            <v-chip v-if="adXlScore > 0" size="small" color="primary" class="mr-2">
              {{ adXlScore.toFixed(2) }} pts
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Predicted/Proven Null -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Predicted or Proven Null Variants</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 1.5 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-3</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="primary"
                variant="tonal"
                @click="addAdXlNull"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="
                modelValue.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null ||
                []
              "
              :columns="nullVariantColumns"
              :readonly="readonly"
              evidence-type="null_variant"
              @update:items="updateAdXlNull"
              @remove="removeAdXlNull"
            />
          </div>

          <!-- Other Variant Type -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Other Variant Types</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 0.1 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-1.5</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="primary"
                variant="tonal"
                @click="addAdXlOther"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="
                modelValue.case_level?.autosomal_dominant_or_x_linked?.other_variant_type || []
              "
              :columns="otherVariantColumns"
              :readonly="readonly"
              evidence-type="other_variant"
              @update:items="updateAdXlOther"
              @remove="removeAdXlOther"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Autosomal Recessive Case-Level -->
      <v-expansion-panel value="ar">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="secondary">mdi-account-multiple</v-icon>
            <span class="font-weight-medium">Case-Level Data - Autosomal Recessive</span>
            <v-spacer />
            <v-chip v-if="arScore > 0" size="small" color="secondary" class="mr-2">
              {{ arScore.toFixed(2) }} pts
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Predicted/Proven Null (AR) -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Predicted or Proven Null Variants (Biallelic)</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 1.5 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-3</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="secondary"
                variant="tonal"
                @click="addArNull"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.case_level?.autosomal_recessive?.predicted_or_proven_null || []"
              :columns="arNullVariantColumns"
              :readonly="readonly"
              evidence-type="ar_null_variant"
              @update:items="updateArNull"
              @remove="removeArNull"
            />
          </div>

          <!-- Other Variant Type (AR) -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Other Variant Types (Biallelic)</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 0.1 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-1.5</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="secondary"
                variant="tonal"
                @click="addArOther"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.case_level?.autosomal_recessive?.other_variant_type || []"
              :columns="arOtherVariantColumns"
              :readonly="readonly"
              evidence-type="ar_other_variant"
              @update:items="updateArOther"
              @remove="removeArOther"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Segregation Evidence -->
      <v-expansion-panel value="segregation">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="info">mdi-family-tree</v-icon>
            <span class="font-weight-medium">Segregation Evidence</span>
            <v-spacer />
            <v-chip v-if="segregationScore > 0" size="small" color="info" class="mr-2">
              {{ segregationScore.toFixed(2) }} pts (max 3)
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div class="d-flex align-center mb-2">
            <span class="text-subtitle-2">Family Segregation Studies</span>
            <v-chip size="x-small" variant="outlined" class="ml-2">Range: 0-3</v-chip>
            <v-spacer />
            <v-btn
              v-if="!readonly"
              size="small"
              color="info"
              variant="tonal"
              @click="addSegregation"
            >
              <v-icon start>mdi-plus</v-icon>
              Add Segregation
            </v-btn>
          </div>
          <EvidenceDataTable
            :items="modelValue.segregation || []"
            :columns="segregationColumns"
            :readonly="readonly"
            evidence-type="segregation"
            @update:items="updateSegregation"
            @remove="removeSegregation"
          />
          <v-alert type="info" variant="tonal" density="compact" class="mt-2">
            <template #prepend>
              <v-icon size="small">mdi-information</v-icon>
            </template>
            <div class="text-caption">
              LOD Score Thresholds: 0.6-1.2 = 1pt, 1.2-2.4 = 2pts, >2.4 = 3pts (max)
            </div>
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Case-Control Evidence -->
      <v-expansion-panel value="case_control">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="warning">mdi-chart-bar</v-icon>
            <span class="font-weight-medium">Case-Control Data</span>
            <v-spacer />
            <v-chip v-if="caseControlScore > 0" size="small" color="warning" class="mr-2">
              {{ caseControlScore.toFixed(2) }} pts (max 6)
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Single Variant Analysis -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Single Variant Analysis</span>
              <v-chip size="x-small" variant="outlined" class="ml-2">Range: 0-6</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="warning"
                variant="tonal"
                @click="addSingleVariant"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Study
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.case_control?.single_variant_analysis || []"
              :columns="caseControlColumns"
              :readonly="readonly"
              evidence-type="case_control_single"
              @update:items="updateSingleVariant"
              @remove="removeSingleVariant"
            />
          </div>

          <!-- Aggregate Variant Analysis -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Aggregate Variant Analysis</span>
              <v-chip size="x-small" variant="outlined" class="ml-2">Range: 0-6</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="warning"
                variant="tonal"
                @click="addAggregateVariant"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Study
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.case_control?.aggregate_variant_analysis || []"
              :columns="aggregateColumns"
              :readonly="readonly"
              evidence-type="case_control_aggregate"
              @update:items="updateAggregateVariant"
              @remove="removeAggregateVariant"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
  /**
   * GeneticEvidenceSection
   *
   * Handles genetic evidence entry per ClinGen SOP v11:
   * - Case-Level Data (AD/XL and AR inheritance patterns)
   * - Segregation Evidence (LOD scores)
   * - Case-Control Data (single and aggregate analysis)
   */

  import { ref, computed } from 'vue'
  import EvidenceDataTable from '../EvidenceDataTable.vue'
  import { openPanelsWithRows } from './openPanelsWithRows'
  import { sumPoints, sumProbandPoints } from '../scoring'
  import { createEmptyGeneticEvidence } from '../evidenceDefaults'
  import type { EvidenceItem, GeneticEvidence } from '../types'
  import {
    nullVariantColumns,
    otherVariantColumns,
    arNullVariantColumns,
    arOtherVariantColumns,
    segregationColumns,
    caseControlColumns,
    aggregateColumns
  } from './evidenceTableColumns'

  const props = withDefaults(
    defineProps<{ modelValue?: GeneticEvidence; readonly?: boolean; moi?: string }>(),
    {
      modelValue: createEmptyGeneticEvidence,
      readonly: false,
      moi: 'Unknown'
    }
  )

  const emit = defineEmits<{ 'update:model-value': [value: GeneticEvidence] }>()

  const expandedPanels = ref(['ad_xl'])
  openPanelsWithRows(expandedPanels, () => ({
    ad_xl: props.modelValue.case_level?.autosomal_dominant_or_x_linked,
    ar: props.modelValue.case_level?.autosomal_recessive,
    segregation: props.modelValue.segregation,
    case_control: props.modelValue.case_control
  }))

  // Score calculations
  const adXlScore = computed(() => {
    const adXl = props.modelValue.case_level?.autosomal_dominant_or_x_linked
    return (
      sumProbandPoints(adXl?.predicted_or_proven_null) + sumProbandPoints(adXl?.other_variant_type)
    )
  })

  const arScore = computed(() => {
    const ar = props.modelValue.case_level?.autosomal_recessive
    return sumProbandPoints(ar?.predicted_or_proven_null) + sumProbandPoints(ar?.other_variant_type)
  })

  const segregationScore = computed(() => Math.min(sumPoints(props.modelValue.segregation), 3))

  const caseControlScore = computed(() => {
    const cc = props.modelValue.case_control
    return Math.min(
      Math.max(sumPoints(cc?.single_variant_analysis), sumPoints(cc?.aggregate_variant_analysis)),
      6
    )
  })

  // Helper to emit updated model
  function emitUpdate(path: string, value: EvidenceItem[]) {
    const newValue: Record<string, unknown> = JSON.parse(JSON.stringify(props.modelValue))
    const keys = path.split('.')
    const last = keys.pop() as string
    let obj: Record<string, unknown> = newValue
    for (const key of keys) {
      if (!obj[key]) obj[key] = {}
      obj = obj[key] as Record<string, unknown>
    }
    obj[last] = value
    emit('update:model-value', newValue as GeneticEvidence)
  }

  // AD/XL handlers
  function addAdXlNull() {
    const items = [
      ...(props.modelValue.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null ||
        [])
    ]
    items.push({
      proband_label: '',
      variant_type: 'nonsense',
      variant: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 1.5,
      explanation: ''
    })
    emitUpdate('case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null', items)
  }

  function updateAdXlNull(items: EvidenceItem[]) {
    emitUpdate('case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null', items)
  }

  function removeAdXlNull(index: number) {
    const items = [
      ...(props.modelValue.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null ||
        [])
    ]
    items.splice(index, 1)
    emitUpdate('case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null', items)
  }

  function addAdXlOther() {
    const items = [
      ...(props.modelValue.case_level?.autosomal_dominant_or_x_linked?.other_variant_type || [])
    ]
    items.push({
      proband_label: '',
      variant_type: 'missense',
      variant: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 0.1,
      explanation: ''
    })
    emitUpdate('case_level.autosomal_dominant_or_x_linked.other_variant_type', items)
  }

  function updateAdXlOther(items: EvidenceItem[]) {
    emitUpdate('case_level.autosomal_dominant_or_x_linked.other_variant_type', items)
  }

  function removeAdXlOther(index: number) {
    const items = [
      ...(props.modelValue.case_level?.autosomal_dominant_or_x_linked?.other_variant_type || [])
    ]
    items.splice(index, 1)
    emitUpdate('case_level.autosomal_dominant_or_x_linked.other_variant_type', items)
  }

  // AR handlers
  function addArNull() {
    const items = [
      ...(props.modelValue.case_level?.autosomal_recessive?.predicted_or_proven_null || [])
    ]
    items.push({
      proband_label: '',
      variant_type: 'two_null',
      variant_1: '',
      variant_2: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 1.5,
      explanation: ''
    })
    emitUpdate('case_level.autosomal_recessive.predicted_or_proven_null', items)
  }

  function updateArNull(items: EvidenceItem[]) {
    emitUpdate('case_level.autosomal_recessive.predicted_or_proven_null', items)
  }

  function removeArNull(index: number) {
    const items = [
      ...(props.modelValue.case_level?.autosomal_recessive?.predicted_or_proven_null || [])
    ]
    items.splice(index, 1)
    emitUpdate('case_level.autosomal_recessive.predicted_or_proven_null', items)
  }

  function addArOther() {
    const items = [...(props.modelValue.case_level?.autosomal_recessive?.other_variant_type || [])]
    items.push({
      proband_label: '',
      variant_type: 'null_and_other',
      variant_1: '',
      variant_2: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 0.1,
      explanation: ''
    })
    emitUpdate('case_level.autosomal_recessive.other_variant_type', items)
  }

  function updateArOther(items: EvidenceItem[]) {
    emitUpdate('case_level.autosomal_recessive.other_variant_type', items)
  }

  function removeArOther(index: number) {
    const items = [...(props.modelValue.case_level?.autosomal_recessive?.other_variant_type || [])]
    items.splice(index, 1)
    emitUpdate('case_level.autosomal_recessive.other_variant_type', items)
  }

  // Segregation handlers
  function addSegregation() {
    const items = [...(props.modelValue.segregation || [])]
    items.push({
      family_label: '',
      pmid: '',
      lod_score: 0,
      segregations_counted: 0,
      points: 0,
      explanation: ''
    })
    emitUpdate('segregation', items)
  }

  function updateSegregation(items: EvidenceItem[]) {
    emitUpdate('segregation', items)
  }

  function removeSegregation(index: number) {
    const items = [...(props.modelValue.segregation || [])]
    items.splice(index, 1)
    emitUpdate('segregation', items)
  }

  // Case-Control handlers
  function addSingleVariant() {
    const items = [...(props.modelValue.case_control?.single_variant_analysis || [])]
    items.push({
      study_label: '',
      pmid: '',
      variant: '',
      cases_with_variant: 0,
      cases_total: 1,
      controls_with_variant: 0,
      controls_total: 1,
      odds_ratio: 0,
      p_value: 1,
      points: 0
    })
    emitUpdate('case_control.single_variant_analysis', items)
  }

  function updateSingleVariant(items: EvidenceItem[]) {
    emitUpdate('case_control.single_variant_analysis', items)
  }

  function removeSingleVariant(index: number) {
    const items = [...(props.modelValue.case_control?.single_variant_analysis || [])]
    items.splice(index, 1)
    emitUpdate('case_control.single_variant_analysis', items)
  }

  function addAggregateVariant() {
    const items = [...(props.modelValue.case_control?.aggregate_variant_analysis || [])]
    items.push({
      study_label: '',
      pmid: '',
      analysis_type: 'burden',
      cases_with_variants: 0,
      cases_total: 1,
      controls_with_variants: 0,
      controls_total: 1,
      p_value: 1,
      points: 0
    })
    emitUpdate('case_control.aggregate_variant_analysis', items)
  }

  function updateAggregateVariant(items: EvidenceItem[]) {
    emitUpdate('case_control.aggregate_variant_analysis', items)
  }

  function removeAggregateVariant(index: number) {
    const items = [...(props.modelValue.case_control?.aggregate_variant_analysis || [])]
    items.splice(index, 1)
    emitUpdate('case_control.aggregate_variant_analysis', items)
  }
</script>

<style scoped>
  .genetic-evidence-section :deep(.v-expansion-panel-title) {
    min-height: 48px;
  }
</style>
