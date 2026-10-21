<template>
  <div class="experimental-evidence-section">
    <v-expansion-panels v-model="expandedPanels" multiple>
      <!-- Function Evidence -->
      <v-expansion-panel value="function">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="primary">mdi-cog</v-icon>
            <span class="font-weight-medium">Function</span>
            <v-spacer />
            <v-chip v-if="functionScore > 0" size="small" color="primary" class="mr-2">
              {{ functionScore.toFixed(2) }} pts (max 2)
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Biochemical Function -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Biochemical Function</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 0.5 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="primary"
                variant="tonal"
                @click="addBiochemical"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.function?.biochemical_function || []"
              :columns="functionColumns"
              :readonly="readonly"
              @update:items="updateBiochemical"
              @remove="removeBiochemical"
            />
          </div>

          <!-- Protein Interaction -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Protein Interaction</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 0.5 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="primary"
                variant="tonal"
                @click="addProteinInteraction"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.function?.protein_interaction || []"
              :columns="proteinColumns"
              :readonly="readonly"
              @update:items="updateProteinInteraction"
              @remove="removeProteinInteraction"
            />
          </div>

          <!-- Expression -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Expression</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 0.5 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="primary"
                variant="tonal"
                @click="addExpression"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.function?.expression || []"
              :columns="expressionColumns"
              :readonly="readonly"
              @update:items="updateExpression"
              @remove="removeExpression"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Functional Alteration -->
      <v-expansion-panel value="functional_alteration">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="secondary">mdi-chart-line-variant</v-icon>
            <span class="font-weight-medium">Functional Alteration</span>
            <v-spacer />
            <v-chip
              v-if="functionalAlterationScore > 0"
              size="small"
              color="secondary"
              class="mr-2"
            >
              {{ functionalAlterationScore.toFixed(2) }} pts (max 2)
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Patient Cells -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Patient Cells</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 1 pt</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="secondary"
                variant="tonal"
                @click="addPatientCells"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.functional_alteration?.patient_cells || []"
              :columns="patientCellsColumns"
              :readonly="readonly"
              @update:items="updatePatientCells"
              @remove="removePatientCells"
            />
          </div>

          <!-- Non-patient Cells -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Non-patient Cells</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 0.5 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-1</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="secondary"
                variant="tonal"
                @click="addNonPatientCells"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.functional_alteration?.non_patient_cells || []"
              :columns="nonPatientCellsColumns"
              :readonly="readonly"
              @update:items="updateNonPatientCells"
              @remove="removeNonPatientCells"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Models -->
      <v-expansion-panel value="models">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="info">mdi-flask-outline</v-icon>
            <span class="font-weight-medium">Models</span>
            <v-spacer />
            <v-chip v-if="modelsScore > 0" size="small" color="info" class="mr-2">
              {{ modelsScore.toFixed(2) }} pts (max 4)
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Non-human Model Organism -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Non-human Model Organism</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 2 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-4</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="info"
                variant="tonal"
                @click="addOrganism"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.models?.non_human_model_organism || []"
              :columns="organismColumns"
              :readonly="readonly"
              @update:items="updateOrganism"
              @remove="removeOrganism"
            />
          </div>

          <!-- Cell Culture Model -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Cell Culture Model</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 1 pt</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="info"
                variant="tonal"
                @click="addCellCulture"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.models?.cell_culture_model || []"
              :columns="cellCultureColumns"
              :readonly="readonly"
              @update:items="updateCellCulture"
              @remove="removeCellCulture"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Rescue -->
      <v-expansion-panel value="rescue">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon class="mr-2" color="success">mdi-lifebuoy</v-icon>
            <span class="font-weight-medium">Rescue</span>
            <v-spacer />
            <v-chip v-if="rescueScore > 0" size="small" color="success" class="mr-2">
              {{ rescueScore.toFixed(2) }} pts (max 4)
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Human Rescue -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Human</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 2 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-4</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="success"
                variant="tonal"
                @click="addHumanRescue"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.rescue?.human || []"
              :columns="rescueColumns"
              :readonly="readonly"
              @update:items="updateHumanRescue"
              @remove="removeHumanRescue"
            />
          </div>

          <!-- Non-human Organism Rescue -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Non-human Model Organism</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 2 pts</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-4</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="success"
                variant="tonal"
                @click="addOrganismRescue"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.rescue?.non_human_model_organism || []"
              :columns="organismRescueColumns"
              :readonly="readonly"
              @update:items="updateOrganismRescue"
              @remove="removeOrganismRescue"
            />
          </div>

          <!-- Cell Culture Rescue -->
          <div class="mb-4">
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Cell Culture</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 1 pt</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="success"
                variant="tonal"
                @click="addCellCultureRescue"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.rescue?.cell_culture || []"
              :columns="cellRescueColumns"
              :readonly="readonly"
              @update:items="updateCellCultureRescue"
              @remove="removeCellCultureRescue"
            />
          </div>

          <!-- Patient Cells Rescue -->
          <div>
            <div class="d-flex align-center mb-2">
              <span class="text-subtitle-2">Patient Cells</span>
              <v-chip size="x-small" variant="tonal" class="ml-2">Default: 1 pt</v-chip>
              <v-chip size="x-small" variant="outlined" class="ml-1">Range: 0-2</v-chip>
              <v-spacer />
              <v-btn
                v-if="!readonly"
                size="small"
                color="success"
                variant="tonal"
                @click="addPatientCellsRescue"
              >
                <v-icon start>mdi-plus</v-icon>
                Add Evidence
              </v-btn>
            </div>
            <EvidenceDataTable
              :items="modelValue.rescue?.patient_cells || []"
              :columns="patientRescueColumns"
              :readonly="readonly"
              @update:items="updatePatientCellsRescue"
              @remove="removePatientCellsRescue"
            />
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
  /**
   * ExperimentalEvidenceSection
   *
   * Handles experimental evidence entry per ClinGen SOP v11:
   * - Function (Biochemical, Protein Interaction, Expression)
   * - Functional Alteration (Patient cells, Non-patient cells)
   * - Models (Non-human organism, Cell culture)
   * - Rescue (Human, Organism, Cell culture, Patient cells)
   */

  import { ref, computed } from 'vue'
  import EvidenceDataTable from '../EvidenceDataTable.vue'
  import { openPanelsWithRows } from './openPanelsWithRows'
  import { sumPoints } from '../scoring'
  import { createEmptyExperimentalEvidence } from '../evidenceDefaults'
  import type { EvidenceItem, ExperimentalEvidence } from '../types'
  import {
    functionColumns,
    proteinColumns,
    expressionColumns,
    patientCellsColumns,
    nonPatientCellsColumns,
    organismColumns,
    cellCultureColumns,
    rescueColumns,
    organismRescueColumns,
    cellRescueColumns,
    patientRescueColumns
  } from './evidenceTableColumns'

  const props = withDefaults(
    defineProps<{ modelValue?: ExperimentalEvidence; readonly?: boolean }>(),
    {
      modelValue: createEmptyExperimentalEvidence,
      readonly: false
    }
  )

  const emit = defineEmits<{ 'update:model-value': [value: ExperimentalEvidence] }>()

  const expandedPanels = ref(['function'])
  openPanelsWithRows(expandedPanels, () => ({ ...props.modelValue }))

  // Score calculations
  const functionScore = computed(() => {
    const fn = props.modelValue.function
    const total =
      sumPoints(fn?.biochemical_function) +
      sumPoints(fn?.protein_interaction) +
      sumPoints(fn?.expression)
    return Math.min(total, 2)
  })

  const functionalAlterationScore = computed(() => {
    const fa = props.modelValue.functional_alteration
    return Math.min(sumPoints(fa?.patient_cells) + sumPoints(fa?.non_patient_cells), 2)
  })

  const modelsScore = computed(() => {
    const models = props.modelValue.models
    return Math.min(
      sumPoints(models?.non_human_model_organism) + sumPoints(models?.cell_culture_model),
      4
    )
  })

  const rescueScore = computed(() => {
    const rescue = props.modelValue.rescue
    const total =
      sumPoints(rescue?.human) +
      sumPoints(rescue?.non_human_model_organism) +
      sumPoints(rescue?.cell_culture) +
      sumPoints(rescue?.patient_cells)
    return Math.min(total, 4)
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
    emit('update:model-value', newValue as ExperimentalEvidence)
  }

  // Function handlers
  function addBiochemical() {
    const items = [...(props.modelValue.function?.biochemical_function || [])]
    items.push({
      label: '',
      pmid: '',
      gene_function_description: '',
      disease_mechanism_relevance: '',
      score_status: 'score',
      points: 0.5,
      explanation: ''
    })
    emitUpdate('function.biochemical_function', items)
  }
  function updateBiochemical(items: EvidenceItem[]) {
    emitUpdate('function.biochemical_function', items)
  }
  function removeBiochemical(index: number) {
    const items = [...(props.modelValue.function?.biochemical_function || [])]
    items.splice(index, 1)
    emitUpdate('function.biochemical_function', items)
  }

  function addProteinInteraction() {
    const items = [...(props.modelValue.function?.protein_interaction || [])]
    items.push({
      label: '',
      pmid: '',
      interacting_protein: '',
      interaction_method: '',
      disease_relevance: '',
      score_status: 'score',
      points: 0.5
    })
    emitUpdate('function.protein_interaction', items)
  }
  function updateProteinInteraction(items: EvidenceItem[]) {
    emitUpdate('function.protein_interaction', items)
  }
  function removeProteinInteraction(index: number) {
    const items = [...(props.modelValue.function?.protein_interaction || [])]
    items.splice(index, 1)
    emitUpdate('function.protein_interaction', items)
  }

  function addExpression() {
    const items = [...(props.modelValue.function?.expression || [])]
    items.push({
      label: '',
      pmid: '',
      tissue_organ: '',
      expression_method: '',
      disease_tissue_relevance: '',
      score_status: 'score',
      points: 0.5
    })
    emitUpdate('function.expression', items)
  }
  function updateExpression(items: EvidenceItem[]) {
    emitUpdate('function.expression', items)
  }
  function removeExpression(index: number) {
    const items = [...(props.modelValue.function?.expression || [])]
    items.splice(index, 1)
    emitUpdate('function.expression', items)
  }

  // Functional Alteration handlers
  function addPatientCells() {
    const items = [...(props.modelValue.functional_alteration?.patient_cells || [])]
    items.push({
      label: '',
      pmid: '',
      cell_type: '',
      variant_tested: '',
      functional_effect: '',
      assay_method: '',
      score_status: 'score',
      points: 1
    })
    emitUpdate('functional_alteration.patient_cells', items)
  }
  function updatePatientCells(items: EvidenceItem[]) {
    emitUpdate('functional_alteration.patient_cells', items)
  }
  function removePatientCells(index: number) {
    const items = [...(props.modelValue.functional_alteration?.patient_cells || [])]
    items.splice(index, 1)
    emitUpdate('functional_alteration.patient_cells', items)
  }

  function addNonPatientCells() {
    const items = [...(props.modelValue.functional_alteration?.non_patient_cells || [])]
    items.push({
      label: '',
      pmid: '',
      cell_line: '',
      variant_engineered: '',
      functional_effect: '',
      assay_method: '',
      score_status: 'score',
      points: 0.5
    })
    emitUpdate('functional_alteration.non_patient_cells', items)
  }
  function updateNonPatientCells(items: EvidenceItem[]) {
    emitUpdate('functional_alteration.non_patient_cells', items)
  }
  function removeNonPatientCells(index: number) {
    const items = [...(props.modelValue.functional_alteration?.non_patient_cells || [])]
    items.splice(index, 1)
    emitUpdate('functional_alteration.non_patient_cells', items)
  }

  // Models handlers
  function addOrganism() {
    const items = [...(props.modelValue.models?.non_human_model_organism || [])]
    items.push({
      label: '',
      pmid: '',
      organism: 'mouse',
      model_type: 'knockout',
      phenotype_observed: '',
      human_phenotype_match: '',
      score_status: 'score',
      points: 2
    })
    emitUpdate('models.non_human_model_organism', items)
  }
  function updateOrganism(items: EvidenceItem[]) {
    emitUpdate('models.non_human_model_organism', items)
  }
  function removeOrganism(index: number) {
    const items = [...(props.modelValue.models?.non_human_model_organism || [])]
    items.splice(index, 1)
    emitUpdate('models.non_human_model_organism', items)
  }

  function addCellCulture() {
    const items = [...(props.modelValue.models?.cell_culture_model || [])]
    items.push({
      label: '',
      pmid: '',
      cell_type: 'ipsc',
      modification: '',
      phenotype_observed: '',
      score_status: 'score',
      points: 1
    })
    emitUpdate('models.cell_culture_model', items)
  }
  function updateCellCulture(items: EvidenceItem[]) {
    emitUpdate('models.cell_culture_model', items)
  }
  function removeCellCulture(index: number) {
    const items = [...(props.modelValue.models?.cell_culture_model || [])]
    items.splice(index, 1)
    emitUpdate('models.cell_culture_model', items)
  }

  // Rescue handlers
  function addHumanRescue() {
    const items = [...(props.modelValue.rescue?.human || [])]
    items.push({
      label: '',
      pmid: '',
      rescue_method: '',
      phenotype_rescued: '',
      rescue_extent: '',
      score_status: 'score',
      points: 2
    })
    emitUpdate('rescue.human', items)
  }
  function updateHumanRescue(items: EvidenceItem[]) {
    emitUpdate('rescue.human', items)
  }
  function removeHumanRescue(index: number) {
    const items = [...(props.modelValue.rescue?.human || [])]
    items.splice(index, 1)
    emitUpdate('rescue.human', items)
  }

  function addOrganismRescue() {
    const items = [...(props.modelValue.rescue?.non_human_model_organism || [])]
    items.push({
      label: '',
      pmid: '',
      organism: '',
      rescue_method: '',
      phenotype_rescued: '',
      score_status: 'score',
      points: 2
    })
    emitUpdate('rescue.non_human_model_organism', items)
  }
  function updateOrganismRescue(items: EvidenceItem[]) {
    emitUpdate('rescue.non_human_model_organism', items)
  }
  function removeOrganismRescue(index: number) {
    const items = [...(props.modelValue.rescue?.non_human_model_organism || [])]
    items.splice(index, 1)
    emitUpdate('rescue.non_human_model_organism', items)
  }

  function addCellCultureRescue() {
    const items = [...(props.modelValue.rescue?.cell_culture || [])]
    items.push({
      label: '',
      pmid: '',
      cell_type: '',
      rescue_method: '',
      phenotype_rescued: '',
      score_status: 'score',
      points: 1
    })
    emitUpdate('rescue.cell_culture', items)
  }
  function updateCellCultureRescue(items: EvidenceItem[]) {
    emitUpdate('rescue.cell_culture', items)
  }
  function removeCellCultureRescue(index: number) {
    const items = [...(props.modelValue.rescue?.cell_culture || [])]
    items.splice(index, 1)
    emitUpdate('rescue.cell_culture', items)
  }

  function addPatientCellsRescue() {
    const items = [...(props.modelValue.rescue?.patient_cells || [])]
    items.push({
      label: '',
      pmid: '',
      cell_type: '',
      rescue_method: '',
      phenotype_rescued: '',
      score_status: 'score',
      points: 1
    })
    emitUpdate('rescue.patient_cells', items)
  }
  function updatePatientCellsRescue(items: EvidenceItem[]) {
    emitUpdate('rescue.patient_cells', items)
  }
  function removePatientCellsRescue(index: number) {
    const items = [...(props.modelValue.rescue?.patient_cells || [])]
    items.splice(index, 1)
    emitUpdate('rescue.patient_cells', items)
  }
</script>

<style scoped>
  .experimental-evidence-section :deep(.v-expansion-panel-title) {
    min-height: 48px;
  }
</style>
