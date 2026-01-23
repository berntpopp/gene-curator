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
              <v-btn size="small" color="primary" variant="tonal" @click="addBiochemical">
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
              <v-btn size="small" color="primary" variant="tonal" @click="addProteinInteraction">
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
              <v-btn size="small" color="primary" variant="tonal" @click="addExpression">
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
              <v-btn size="small" color="secondary" variant="tonal" @click="addPatientCells">
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
              <v-btn size="small" color="secondary" variant="tonal" @click="addNonPatientCells">
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
              <v-btn size="small" color="info" variant="tonal" @click="addOrganism">
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
              <v-btn size="small" color="info" variant="tonal" @click="addCellCulture">
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
              <v-btn size="small" color="success" variant="tonal" @click="addHumanRescue">
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
              <v-btn size="small" color="success" variant="tonal" @click="addOrganismRescue">
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
              <v-btn size="small" color="success" variant="tonal" @click="addCellCultureRescue">
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
              <v-btn size="small" color="success" variant="tonal" @click="addPatientCellsRescue">
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

<script setup>
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

  const props = defineProps({
    modelValue: {
      type: Object,
      default: () => ({
        function: {
          biochemical_function: [],
          protein_interaction: [],
          expression: []
        },
        functional_alteration: {
          patient_cells: [],
          non_patient_cells: []
        },
        models: {
          non_human_model_organism: [],
          cell_culture_model: []
        },
        rescue: {
          human: [],
          non_human_model_organism: [],
          cell_culture: [],
          patient_cells: []
        }
      })
    },
    readonly: {
      type: Boolean,
      default: false
    }
  })

  const emit = defineEmits(['update:model-value'])

  const expandedPanels = ref(['function'])

  // Column definitions
  const functionColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'gene_function_description', label: 'Function Description', width: '200px' },
    { key: 'disease_mechanism_relevance', label: 'Disease Relevance', width: '200px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 },
    { key: 'explanation', label: 'Explanation', width: '180px' }
  ]

  const proteinColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'interacting_protein', label: 'Interacting Protein', width: '150px' },
    { key: 'interaction_method', label: 'Method', width: '150px' },
    { key: 'disease_relevance', label: 'Disease Relevance', width: '180px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
  ]

  const expressionColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'tissue_organ', label: 'Tissue/Organ', width: '140px' },
    { key: 'expression_method', label: 'Method', width: '140px' },
    { key: 'disease_tissue_relevance', label: 'Relevance', width: '180px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
  ]

  const patientCellsColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'cell_type', label: 'Cell Type', width: '120px' },
    { key: 'variant_tested', label: 'Variant', width: '140px' },
    { key: 'functional_effect', label: 'Effect', width: '160px' },
    { key: 'assay_method', label: 'Assay', width: '140px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
  ]

  const nonPatientCellsColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'cell_line', label: 'Cell Line', width: '120px' },
    { key: 'variant_engineered', label: 'Variant', width: '140px' },
    { key: 'functional_effect', label: 'Effect', width: '160px' },
    { key: 'assay_method', label: 'Assay', width: '140px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 1, step: 0.5 }
  ]

  const organismColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'organism',
      label: 'Organism',
      width: '120px',
      type: 'select',
      options: [
        { value: 'mouse', label: 'Mouse' },
        { value: 'rat', label: 'Rat' },
        { value: 'zebrafish', label: 'Zebrafish' },
        { value: 'drosophila', label: 'Drosophila' },
        { value: 'c_elegans', label: 'C. elegans' },
        { value: 'xenopus', label: 'Xenopus' },
        { value: 'yeast', label: 'Yeast' },
        { value: 'other', label: 'Other' }
      ]
    },
    {
      key: 'model_type',
      label: 'Type',
      width: '120px',
      type: 'select',
      options: [
        { value: 'knockout', label: 'Knockout' },
        { value: 'knockin', label: 'Knockin' },
        { value: 'transgenic', label: 'Transgenic' },
        { value: 'morpholino', label: 'Morpholino' },
        { value: 'crispr', label: 'CRISPR' },
        { value: 'other', label: 'Other' }
      ]
    },
    { key: 'phenotype_observed', label: 'Phenotype', width: '180px' },
    { key: 'human_phenotype_match', label: 'Human Match', width: '160px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 4, step: 0.5 }
  ]

  const cellCultureColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    {
      key: 'cell_type',
      label: 'Cell Type',
      width: '120px',
      type: 'select',
      options: [
        { value: 'ipsc', label: 'iPSC-derived' },
        { value: 'organoid', label: 'Organoid' },
        { value: 'primary', label: 'Primary cells' },
        { value: 'cell_line', label: 'Cell line' },
        { value: 'other', label: 'Other' }
      ]
    },
    { key: 'modification', label: 'Modification', width: '140px' },
    { key: 'phenotype_observed', label: 'Phenotype', width: '180px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
  ]

  const rescueColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'rescue_method', label: 'Method', width: '150px' },
    { key: 'phenotype_rescued', label: 'Phenotype Rescued', width: '180px' },
    { key: 'rescue_extent', label: 'Rescue Extent', width: '140px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 4, step: 0.5 }
  ]

  const organismRescueColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'organism', label: 'Organism', width: '120px' },
    { key: 'rescue_method', label: 'Method', width: '150px' },
    { key: 'phenotype_rescued', label: 'Phenotype Rescued', width: '180px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 4, step: 0.5 }
  ]

  const cellRescueColumns = [
    { key: 'label', label: 'Label', width: '100px' },
    { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
    { key: 'cell_type', label: 'Cell Type', width: '120px' },
    { key: 'rescue_method', label: 'Method', width: '150px' },
    { key: 'phenotype_rescued', label: 'Phenotype Rescued', width: '180px' },
    {
      key: 'score_status',
      label: 'Status',
      width: '100px',
      type: 'select',
      options: [
        { value: 'score', label: 'Score' },
        { value: 'review', label: 'Review' }
      ]
    },
    { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
  ]

  const patientRescueColumns = cellRescueColumns

  // Score calculations
  const functionScore = computed(() => {
    const biochem = (props.modelValue.function?.biochemical_function || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const protein = (props.modelValue.function?.protein_interaction || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const expression = (props.modelValue.function?.expression || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    return Math.min(biochem + protein + expression, 2)
  })

  const functionalAlterationScore = computed(() => {
    const patient = (props.modelValue.functional_alteration?.patient_cells || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const nonPatient = (props.modelValue.functional_alteration?.non_patient_cells || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    return Math.min(patient + nonPatient, 2)
  })

  const modelsScore = computed(() => {
    const organism = (props.modelValue.models?.non_human_model_organism || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const cellCulture = (props.modelValue.models?.cell_culture_model || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    return Math.min(organism + cellCulture, 4)
  })

  const rescueScore = computed(() => {
    const human = (props.modelValue.rescue?.human || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const organism = (props.modelValue.rescue?.non_human_model_organism || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const cellCulture = (props.modelValue.rescue?.cell_culture || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    const patientCells = (props.modelValue.rescue?.patient_cells || []).reduce(
      (sum, item) => sum + (parseFloat(item.points) || 0),
      0
    )
    return Math.min(human + organism + cellCulture + patientCells, 4)
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
  function updateBiochemical(items) {
    emitUpdate('function.biochemical_function', items)
  }
  function removeBiochemical(index) {
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
  function updateProteinInteraction(items) {
    emitUpdate('function.protein_interaction', items)
  }
  function removeProteinInteraction(index) {
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
  function updateExpression(items) {
    emitUpdate('function.expression', items)
  }
  function removeExpression(index) {
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
  function updatePatientCells(items) {
    emitUpdate('functional_alteration.patient_cells', items)
  }
  function removePatientCells(index) {
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
  function updateNonPatientCells(items) {
    emitUpdate('functional_alteration.non_patient_cells', items)
  }
  function removeNonPatientCells(index) {
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
  function updateOrganism(items) {
    emitUpdate('models.non_human_model_organism', items)
  }
  function removeOrganism(index) {
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
  function updateCellCulture(items) {
    emitUpdate('models.cell_culture_model', items)
  }
  function removeCellCulture(index) {
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
  function updateHumanRescue(items) {
    emitUpdate('rescue.human', items)
  }
  function removeHumanRescue(index) {
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
  function updateOrganismRescue(items) {
    emitUpdate('rescue.non_human_model_organism', items)
  }
  function removeOrganismRescue(index) {
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
  function updateCellCultureRescue(items) {
    emitUpdate('rescue.cell_culture', items)
  }
  function removeCellCultureRescue(index) {
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
  function updatePatientCellsRescue(items) {
    emitUpdate('rescue.patient_cells', items)
  }
  function removePatientCellsRescue(index) {
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
