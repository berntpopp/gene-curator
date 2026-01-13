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
              <v-btn size="small" color="primary" variant="tonal" @click="addAdXlNull">
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
              <v-btn size="small" color="primary" variant="tonal" @click="addAdXlOther">
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
              <v-btn size="small" color="secondary" variant="tonal" @click="addArNull">
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
              <v-btn size="small" color="secondary" variant="tonal" @click="addArOther">
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
            <v-btn size="small" color="info" variant="tonal" @click="addSegregation">
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
              <v-btn size="small" color="warning" variant="tonal" @click="addSingleVariant">
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
              <v-btn size="small" color="warning" variant="tonal" @click="addAggregateVariant">
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

<script setup>
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

  const props = defineProps({
    modelValue: {
      type: Object,
      default: () => ({
        case_level: {
          autosomal_dominant_or_x_linked: {
            predicted_or_proven_null: [],
            other_variant_type: []
          },
          autosomal_recessive: {
            predicted_or_proven_null: [],
            other_variant_type: []
          }
        },
        segregation: [],
        case_control: {
          single_variant_analysis: [],
          aggregate_variant_analysis: []
        }
      })
    },
    readonly: {
      type: Boolean,
      default: false
    },
    moi: {
      type: String,
      default: 'Unknown'
    }
  })

  const emit = defineEmits(['update:model-value'])

  const expandedPanels = ref(['ad_xl'])

  // Column definitions for evidence tables
  const nullVariantColumns = [
    { key: 'proband_label', label: 'Proband', width: '100px' },
    {
      key: 'variant_type',
      label: 'Type',
      width: '140px',
      type: 'select',
      options: [
        { value: 'nonsense', label: 'Nonsense' },
        { value: 'frameshift', label: 'Frameshift' },
        { value: 'canonical_splice', label: 'Splice (+/-1,2)' },
        { value: 'initiation_codon', label: 'Init codon' },
        { value: 'single_exon_deletion', label: 'Single exon del' },
        { value: 'multi_exon_deletion', label: 'Multi-exon del' },
        { value: 'whole_gene_deletion', label: 'Whole gene del' }
      ]
    },
    { key: 'variant', label: 'Variant (HGVS)', width: '160px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' },
        { value: 'contradicts', label: 'Contradicts' }
      ]
    },
    {
      key: 'proband_counted_points',
      label: 'Points',
      width: '80px',
      type: 'number',
      min: 0,
      max: 3,
      step: 0.1
    },
    { key: 'explanation', label: 'Explanation', width: '200px' }
  ]

  const otherVariantColumns = [
    { key: 'proband_label', label: 'Proband', width: '100px' },
    {
      key: 'variant_type',
      label: 'Type',
      width: '140px',
      type: 'select',
      options: [
        { value: 'missense', label: 'Missense' },
        { value: 'in_frame_indel', label: 'In-frame indel' },
        { value: 'cryptic_splice', label: 'Cryptic splice' },
        { value: 'synonymous', label: 'Synonymous' },
        { value: '5_utr', label: "5' UTR" },
        { value: '3_utr', label: "3' UTR" },
        { value: 'intronic', label: 'Intronic' },
        { value: 'other', label: 'Other' }
      ]
    },
    { key: 'variant', label: 'Variant (HGVS)', width: '160px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' },
        { value: 'contradicts', label: 'Contradicts' }
      ]
    },
    {
      key: 'proband_counted_points',
      label: 'Points',
      width: '80px',
      type: 'number',
      min: 0,
      max: 1.5,
      step: 0.1
    },
    { key: 'explanation', label: 'Explanation', width: '200px' }
  ]

  const arNullVariantColumns = [
    { key: 'proband_label', label: 'Proband', width: '100px' },
    {
      key: 'variant_type',
      label: 'Type',
      width: '140px',
      type: 'select',
      options: [
        { value: 'two_null', label: 'Two null variants' },
        { value: 'null_and_null', label: 'Homozygous null' }
      ]
    },
    { key: 'variant_1', label: 'Variant 1', width: '140px' },
    { key: 'variant_2', label: 'Variant 2', width: '140px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' },
        { value: 'contradicts', label: 'Contradicts' }
      ]
    },
    {
      key: 'proband_counted_points',
      label: 'Points',
      width: '80px',
      type: 'number',
      min: 0,
      max: 3,
      step: 0.1
    },
    { key: 'explanation', label: 'Explanation', width: '180px' }
  ]

  const arOtherVariantColumns = [
    { key: 'proband_label', label: 'Proband', width: '100px' },
    {
      key: 'variant_type',
      label: 'Type',
      width: '150px',
      type: 'select',
      options: [
        { value: 'null_and_other', label: 'Null + Other' },
        { value: 'two_other', label: 'Two other variants' },
        { value: 'homozygous_other', label: 'Homozygous other' }
      ]
    },
    { key: 'variant_1', label: 'Variant 1', width: '140px' },
    { key: 'variant_2', label: 'Variant 2', width: '140px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' },
        { value: 'contradicts', label: 'Contradicts' }
      ]
    },
    {
      key: 'proband_counted_points',
      label: 'Points',
      width: '80px',
      type: 'number',
      min: 0,
      max: 1.5,
      step: 0.1
    },
    { key: 'explanation', label: 'Explanation', width: '180px' }
  ]

  const segregationColumns = [
    { key: 'family_label', label: 'Family', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'lod_score', label: 'LOD Score', width: '100px', type: 'number', min: 0, step: 0.1 },
    { key: 'segregations_counted', label: 'Seg. Counted', width: '100px', type: 'number', min: 0 },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 3, step: 0.1 },
    { key: 'explanation', label: 'Explanation', width: '200px' }
  ]

  const caseControlColumns = [
    { key: 'study_label', label: 'Study', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'variant', label: 'Variant', width: '140px' },
    { key: 'cases_with_variant', label: 'Cases+', width: '80px', type: 'number', min: 0 },
    { key: 'cases_total', label: 'Cases', width: '80px', type: 'number', min: 1 },
    { key: 'controls_with_variant', label: 'Ctrl+', width: '80px', type: 'number', min: 0 },
    { key: 'controls_total', label: 'Ctrl', width: '80px', type: 'number', min: 1 },
    { key: 'odds_ratio', label: 'OR', width: '80px', type: 'number', min: 0 },
    { key: 'p_value', label: 'P-value', width: '100px', type: 'number', min: 0, max: 1 },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 6, step: 0.5 }
  ]

  const aggregateColumns = [
    { key: 'study_label', label: 'Study', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'analysis_type',
      label: 'Analysis',
      width: '120px',
      type: 'select',
      options: [
        { value: 'burden', label: 'Burden test' },
        { value: 'collapsing', label: 'Collapsing' },
        { value: 'skat', label: 'SKAT' },
        { value: 'skat_o', label: 'SKAT-O' },
        { value: 'other', label: 'Other' }
      ]
    },
    { key: 'cases_with_variants', label: 'Cases+', width: '80px', type: 'number', min: 0 },
    { key: 'cases_total', label: 'Cases', width: '80px', type: 'number', min: 1 },
    { key: 'controls_with_variants', label: 'Ctrl+', width: '80px', type: 'number', min: 0 },
    { key: 'controls_total', label: 'Ctrl', width: '80px', type: 'number', min: 1 },
    { key: 'p_value', label: 'P-value', width: '100px', type: 'number', min: 0, max: 1 },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 6, step: 0.5 }
  ]

  // Score calculations
  const adXlScore = computed(() => {
    const nullItems =
      props.modelValue.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null || []
    const otherItems =
      props.modelValue.case_level?.autosomal_dominant_or_x_linked?.other_variant_type || []
    const nullScore = nullItems.reduce(
      (sum, item) => sum + (parseFloat(item.proband_counted_points) || 0),
      0
    )
    const otherScore = otherItems.reduce(
      (sum, item) => sum + (parseFloat(item.proband_counted_points) || 0),
      0
    )
    return nullScore + otherScore
  })

  const arScore = computed(() => {
    const nullItems =
      props.modelValue.case_level?.autosomal_recessive?.predicted_or_proven_null || []
    const otherItems = props.modelValue.case_level?.autosomal_recessive?.other_variant_type || []
    const nullScore = nullItems.reduce(
      (sum, item) => sum + (parseFloat(item.proband_counted_points) || 0),
      0
    )
    const otherScore = otherItems.reduce(
      (sum, item) => sum + (parseFloat(item.proband_counted_points) || 0),
      0
    )
    return nullScore + otherScore
  })

  const segregationScore = computed(() => {
    const items = props.modelValue.segregation || []
    return Math.min(
      items.reduce((sum, item) => sum + (parseFloat(item.points) || 0), 0),
      3
    )
  })

  const caseControlScore = computed(() => {
    const singleItems = props.modelValue.case_control?.single_variant_analysis || []
    const aggItems = props.modelValue.case_control?.aggregate_variant_analysis || []
    const singleScore = singleItems.reduce((sum, item) => sum + (parseFloat(item.points) || 0), 0)
    const aggScore = aggItems.reduce((sum, item) => sum + (parseFloat(item.points) || 0), 0)
    return Math.min(Math.max(singleScore, aggScore), 6)
  })

  // Helper to emit updated model
  function emitUpdate(path, value) {
    const newValue = JSON.parse(JSON.stringify(props.modelValue))
    const keys = path.split('.')
    let obj = newValue
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {}
      obj = obj[keys[i]]
    }
    obj[keys[keys.length - 1]] = value
    emit('update:model-value', newValue)
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

  function updateAdXlNull(items) {
    emitUpdate('case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null', items)
  }

  function removeAdXlNull(index) {
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

  function updateAdXlOther(items) {
    emitUpdate('case_level.autosomal_dominant_or_x_linked.other_variant_type', items)
  }

  function removeAdXlOther(index) {
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

  function updateArNull(items) {
    emitUpdate('case_level.autosomal_recessive.predicted_or_proven_null', items)
  }

  function removeArNull(index) {
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

  function updateArOther(items) {
    emitUpdate('case_level.autosomal_recessive.other_variant_type', items)
  }

  function removeArOther(index) {
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

  function updateSegregation(items) {
    emitUpdate('segregation', items)
  }

  function removeSegregation(index) {
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

  function updateSingleVariant(items) {
    emitUpdate('case_control.single_variant_analysis', items)
  }

  function removeSingleVariant(index) {
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

  function updateAggregateVariant(items) {
    emitUpdate('case_control.aggregate_variant_analysis', items)
  }

  function removeAggregateVariant(index) {
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
