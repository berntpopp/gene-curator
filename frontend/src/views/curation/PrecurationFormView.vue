<template>
  <v-container>
    <!-- Loading State -->
    <template v-if="loading">
      <v-row>
        <v-col cols="12" class="text-center py-12">
          <v-progress-circular indeterminate size="64" color="primary" />
          <div class="text-h6 mt-4 text-medium-emphasis">Loading gene information...</div>
        </v-col>
      </v-row>
    </template>

    <!-- Error State -->
    <template v-else-if="loadError">
      <v-row>
        <v-col cols="12">
          <v-alert type="error" variant="tonal" prominent>
            <v-alert-title>Failed to Load Gene</v-alert-title>
            {{ loadError }}
            <template #append>
              <v-btn variant="outlined" @click="handleCancel">Go Back</v-btn>
            </template>
          </v-alert>
        </v-col>
      </v-row>
    </template>

    <!-- Main Content -->
    <template v-else>
      <v-row>
        <v-col cols="12">
          <!-- Prominent Header with Gene Context -->
          <v-card class="mb-6 bg-primary" variant="flat">
            <v-card-text class="pa-6">
              <div class="d-flex align-center">
                <v-btn
                  icon="mdi-arrow-left"
                  variant="tonal"
                  color="white"
                  class="mr-4"
                  aria-label="Go back"
                  @click="handleCancel"
                />
                <div class="flex-grow-1">
                  <!-- Gene Name - MOST PROMINENT -->
                  <div class="d-flex align-center mb-2">
                    <v-icon size="x-large" color="white" class="mr-3">mdi-dna</v-icon>
                    <h1 class="text-h3 font-weight-bold text-white">
                      {{ form.gene_symbol || 'Unknown Gene' }}
                    </h1>
                    <v-chip
                      v-if="form.gene_name"
                      color="white"
                      variant="flat"
                      class="ml-4 text-primary"
                    >
                      {{ form.gene_name }}
                    </v-chip>
                  </div>

                  <!-- Breadcrumb context -->
                  <div class="d-flex align-center text-white-darken-1">
                    <v-icon size="small" class="mr-1">mdi-folder-outline</v-icon>
                    <span class="mr-2">{{ scope?.display_name || 'Scope' }}</span>
                    <v-icon size="x-small">mdi-chevron-right</v-icon>
                    <span class="mx-2">Precuration</span>
                    <v-chip size="small" color="white" variant="flat" class="text-primary">
                      <v-icon start size="small">mdi-clipboard-text</v-icon>
                      New
                    </v-chip>
                  </div>
                </div>

                <!-- Gene external links -->
                <div v-if="form.hgnc_id" class="d-flex flex-column ga-2">
                  <v-btn
                    size="small"
                    variant="tonal"
                    color="white"
                    :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${form.hgnc_id}`"
                    target="_blank"
                  >
                    <v-icon start size="small">mdi-open-in-new</v-icon>
                    HGNC
                  </v-btn>
                  <v-btn
                    v-if="form.ncbi_gene_id"
                    size="small"
                    variant="tonal"
                    color="white"
                    :href="`https://www.ncbi.nlm.nih.gov/gene/${form.ncbi_gene_id}`"
                    target="_blank"
                  >
                    <v-icon start size="small">mdi-open-in-new</v-icon>
                    NCBI
                  </v-btn>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-icon start>mdi-clipboard-text</v-icon>
              Precuration Assessment
              <v-spacer />
              <v-chip size="small" color="info" variant="tonal">
                <v-icon start size="small">mdi-information</v-icon>
                Step 1 of Curation Workflow
              </v-chip>
            </v-card-title>
            <v-card-subtitle>
              Gather preliminary evidence to determine if full curation is warranted for
              <strong>{{ form.gene_symbol }}</strong>
            </v-card-subtitle>

            <v-card-text>
              <v-form ref="formRef" @submit.prevent="handleSubmit">
                <!-- Disease Entity Definition Section -->
                <v-expansion-panels v-model="expandedPanels" multiple class="mb-4">
                  <!-- Disease Information Panel -->
                  <v-expansion-panel value="disease">
                    <v-expansion-panel-title>
                      <v-icon start color="primary">mdi-medical-bag</v-icon>
                      <span class="font-weight-medium">Disease Entity Definition</span>
                      <v-chip
                        v-if="form.disease_name && form.mode_of_inheritance"
                        size="small"
                        color="success"
                        class="ml-2"
                      >
                        Complete
                      </v-chip>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-row>
                        <v-col cols="12" md="6">
                          <MONDOAutocomplete
                            v-model="form.mondo_id"
                            v-model:disease-name="form.mondo_disease_name"
                            label="MONDO Disease"
                            hint="Search for a disease to auto-populate name"
                            @select="handleMONDOSelect"
                          />
                        </v-col>
                        <v-col cols="12" md="6">
                          <v-text-field
                            v-model="form.disease_name"
                            label="Disease Name *"
                            variant="outlined"
                            :rules="[v => !!v || 'Disease name is required']"
                            prepend-inner-icon="mdi-medical-bag"
                            hint="Use dyadic naming: Gene-associated phenotype (e.g., SCN1A-related seizure disorder)"
                            persistent-hint
                          />
                        </v-col>
                      </v-row>

                      <v-row class="mt-2">
                        <v-col cols="12" md="6">
                          <HPOInheritanceSelect
                            v-model="form.mode_of_inheritance"
                            v-model:hpo-id="form.inheritance_hpo_id"
                            label="Mode of Inheritance *"
                            :required="true"
                            hint="Select the inheritance pattern"
                            @select="handleInheritanceSelect"
                          />
                        </v-col>
                        <v-col cols="12" md="6">
                          <v-text-field
                            v-model="form.evaluation_date"
                            label="Evaluation Date"
                            type="date"
                            variant="outlined"
                            prepend-inner-icon="mdi-calendar"
                            hint="Date precuration performed"
                            persistent-hint
                          />
                        </v-col>
                      </v-row>
                    </v-expansion-panel-text>
                  </v-expansion-panel>

                  <!-- Lumping & Splitting Panel (per ClinGen Guidelines) -->
                  <v-expansion-panel value="lumping">
                    <v-expansion-panel-title>
                      <v-icon start color="secondary">mdi-call-split</v-icon>
                      <span class="font-weight-medium">Lumping & Splitting</span>
                      <v-chip v-if="form.curation_type" size="small" color="info" class="ml-2">
                        {{ getCurationTypeShortLabel(form.curation_type) }}
                      </v-chip>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                        <template #prepend>
                          <v-icon size="small">mdi-information</v-icon>
                        </template>
                        <div class="text-body-2">
                          Per ClinGen guidelines, determine which disease entity will be used for
                          evaluation. Review current disease/phenotype assertions and select terms
                          to include or exclude.
                        </div>
                      </v-alert>

                      <!-- Curation Type (single choice per ClinGen) -->
                      <div class="text-subtitle-2 mb-2">
                        <v-icon size="small" class="mr-1">mdi-format-list-bulleted-type</v-icon>
                        Curation Type *
                      </div>
                      <v-radio-group
                        v-model="form.curation_type"
                        :rules="[v => !!v || 'Curation type is required']"
                        class="mb-4"
                      >
                        <v-radio
                          v-for="option in curationTypeOptions"
                          :key="option.value"
                          :value="option.value"
                          :label="option.title"
                          :color="option.color"
                        >
                          <template #label>
                            <div>
                              <span :class="option.discouraged ? 'text-warning' : ''">
                                {{ option.title }}
                              </span>
                              <v-chip
                                v-if="option.discouraged"
                                size="x-small"
                                color="warning"
                                class="ml-2"
                              >
                                Discouraged
                              </v-chip>
                            </div>
                          </template>
                        </v-radio>
                      </v-radio-group>

                      <!-- Rationale (multiple choice per ClinGen) -->
                      <div class="text-subtitle-2 mb-2">
                        <v-icon size="small" class="mr-1">mdi-lightbulb-outline</v-icon>
                        Rationale Criteria
                      </div>
                      <v-chip-group
                        v-model="form.rationale"
                        multiple
                        selected-class="text-primary"
                        class="mb-4"
                      >
                        <v-chip
                          v-for="option in rationaleOptions"
                          :key="option.value"
                          :value="option.value"
                          filter
                          variant="outlined"
                        >
                          {{ option.title }}
                        </v-chip>
                      </v-chip-group>
                      <div class="text-caption text-medium-emphasis mb-4">
                        Select all criteria that apply to the lumping/splitting decision
                      </div>

                      <!-- MIM Phenotypes -->
                      <v-row>
                        <v-col cols="12" md="6">
                          <div class="text-subtitle-2 mb-2">
                            <v-icon size="small" color="success" class="mr-1"
                              >mdi-check-circle</v-icon
                            >
                            Included OMIM Phenotypes
                          </div>
                          <OMIMAutocomplete
                            v-model="form.included_mim_phenotypes"
                            label="Search OMIM to Include"
                            hint="Search by disease name or OMIM number"
                            prepend-icon="mdi-plus-circle"
                            multiple
                          />
                        </v-col>
                        <v-col cols="12" md="6">
                          <div class="text-subtitle-2 mb-2">
                            <v-icon size="small" color="warning" class="mr-1"
                              >mdi-close-circle</v-icon
                            >
                            Excluded OMIM Phenotypes
                          </div>
                          <OMIMAutocomplete
                            v-model="form.excluded_mim_phenotypes"
                            label="Search OMIM to Exclude"
                            hint="Search by disease name or OMIM number"
                            prepend-icon="mdi-minus-circle"
                            multiple
                          />
                        </v-col>
                      </v-row>

                      <!-- Supporting Literature -->
                      <v-row class="mt-2">
                        <v-col cols="12">
                          <PMIDInput
                            v-model="form.supporting_pmids"
                            v-model:publications="form.supporting_publications"
                            label="Supporting PMIDs"
                            hint="Enter PubMed IDs and click Validate to verify"
                          />
                        </v-col>
                      </v-row>

                      <!-- Rationale Notes -->
                      <v-row class="mt-2">
                        <v-col cols="12">
                          <v-textarea
                            v-model="form.rationale_notes"
                            label="Rationale Notes"
                            variant="outlined"
                            rows="3"
                            auto-grow
                            prepend-inner-icon="mdi-note-text"
                            hint="Optional free text explanation of the lumping/splitting decision"
                            persistent-hint
                          />
                        </v-col>
                      </v-row>
                    </v-expansion-panel-text>
                  </v-expansion-panel>

                  <!-- Evidence Assessment Panel -->
                  <v-expansion-panel value="evidence">
                    <v-expansion-panel-title>
                      <v-icon start color="info">mdi-chart-line</v-icon>
                      <span class="font-weight-medium">Preliminary Evidence Assessment</span>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-row>
                        <v-col cols="12" md="6">
                          <v-select
                            v-model="form.evidence_strength"
                            :items="evidenceStrengthOptions"
                            label="Evidence Strength"
                            variant="outlined"
                            prepend-inner-icon="mdi-chart-line"
                            hint="Initial assessment of evidence quality"
                            persistent-hint
                          />
                        </v-col>
                        <v-col cols="12" md="6">
                          <v-select
                            v-model="form.recommendation"
                            :items="recommendationOptions"
                            label="Recommendation *"
                            variant="outlined"
                            prepend-inner-icon="mdi-lightbulb-on"
                            :rules="[v => !!v || 'Recommendation is required']"
                            hint="Should this proceed to full curation?"
                            persistent-hint
                          />
                        </v-col>
                      </v-row>

                      <v-row class="mt-2">
                        <v-col cols="12">
                          <v-textarea
                            v-model="form.literature_summary"
                            label="Literature Summary"
                            variant="outlined"
                            rows="4"
                            auto-grow
                            prepend-inner-icon="mdi-text-box-outline"
                            hint="Brief summary of key publications and evidence"
                            persistent-hint
                          />
                        </v-col>
                      </v-row>

                      <v-row class="mt-2">
                        <v-col cols="12">
                          <v-textarea
                            v-model="form.notes"
                            label="Additional Notes"
                            variant="outlined"
                            rows="3"
                            auto-grow
                            prepend-inner-icon="mdi-note-text"
                            hint="Any additional observations or concerns"
                            persistent-hint
                          />
                        </v-col>
                      </v-row>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>

                <!-- Action Buttons -->
                <v-divider class="my-6" />
                <div class="d-flex justify-end gap-2">
                  <v-btn variant="outlined" @click="handleCancel">Cancel</v-btn>
                  <v-btn
                    color="primary"
                    type="submit"
                    :loading="saving"
                    prepend-icon="mdi-content-save"
                  >
                    Save Precuration
                  </v-btn>
                </div>
              </v-form>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script setup>
  /**
   * PrecurationFormView
   *
   * Scope-aware form for creating precurations.
   * Precurations are preliminary assessments before full curation.
   *
   * Route: /scopes/:scopeId/genes/:geneId/precuration/new
   *
   * @example
   * router.push(`/scopes/${scopeId}/genes/${geneId}/precuration/new`)
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { genesAPI, precurationsAPI, scopesAPI, schemasAPI } from '@/api'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import MONDOAutocomplete from '@/components/evidence/MONDOAutocomplete.vue'
  import OMIMAutocomplete from '@/components/evidence/OMIMAutocomplete.vue'
  import HPOInheritanceSelect from '@/components/evidence/HPOInheritanceSelect.vue'
  import PMIDInput from '@/components/evidence/PMIDInput.vue'

  const router = useRouter()
  const route = useRoute()
  const notificationStore = useNotificationsStore()
  const logger = useLogger()

  // Route params
  const scopeId = computed(() => route.params.scopeId)
  const geneId = computed(() => route.params.geneId)

  // Scope and workflow data
  const scope = ref(null)
  const precurationSchemaId = ref(null)

  // Form state
  const formRef = ref(null)
  const saving = ref(false)
  const loading = ref(true)
  const loadError = ref(null)
  const expandedPanels = ref(['disease', 'lumping', 'evidence'])

  const form = ref({
    // Gene info (auto-filled)
    gene_id: null,
    gene_symbol: '',
    gene_name: '',
    hgnc_id: '',
    ncbi_gene_id: '',
    // Disease entity definition
    disease_name: '',
    mondo_id: '',
    mondo_disease_name: '', // Auto-filled from MONDO selection
    mode_of_inheritance: null,
    inheritance_hpo_id: '', // HPO ID for inheritance pattern
    evaluation_date: new Date().toISOString().split('T')[0],
    // Lumping & Splitting (per ClinGen guidelines)
    curation_type: null,
    rationale: [],
    included_mim_phenotypes: [],
    excluded_mim_phenotypes: [],
    supporting_pmids: [],
    supporting_publications: [],
    rationale_notes: '',
    // Evidence assessment
    evidence_strength: null,
    recommendation: null,
    literature_summary: '',
    notes: ''
  })

  // Note: Mode of Inheritance options are now fetched from HPO API
  // via the HPOInheritanceSelect component

  // ClinGen Curation Type options (single choice)
  const curationTypeOptions = [
    {
      title: 'Curate a single gene-disease entity from this list',
      value: 'single_from_list',
      color: 'primary',
      discouraged: false
    },
    {
      title: 'Curate a single gene-disease entity not on this list',
      value: 'single_not_on_list',
      color: 'info',
      discouraged: false
    },
    {
      title: 'Curate an isolated phenotype that is part of this disease entity',
      value: 'isolated_phenotype',
      color: 'warning',
      discouraged: true
    },
    {
      title: 'Curate a "lumped" disease entity from this list',
      value: 'lumped_entity',
      color: 'success',
      discouraged: false
    }
  ]

  // ClinGen Rationale options (multiple choice)
  const rationaleOptions = [
    { title: 'Assertion', value: 'assertion' },
    { title: 'Molecular Mechanism', value: 'molecular_mechanism' },
    { title: 'Phenotypic Variability', value: 'phenotypic_variability' },
    { title: 'Inheritance Pattern', value: 'inheritance_pattern' },
    { title: 'To dispute an asserted entity', value: 'dispute_entity' },
    { title: 'Insufficient evidence for multiple diseases', value: 'insufficient_evidence' }
  ]

  // Evidence strength options
  const evidenceStrengthOptions = [
    { title: 'Strong - Multiple high-quality studies', value: 'strong' },
    { title: 'Moderate - Some supporting evidence', value: 'moderate' },
    { title: 'Weak - Limited or conflicting evidence', value: 'weak' },
    { title: 'None - No credible evidence found', value: 'none' }
  ]

  // Recommendation options
  const recommendationOptions = [
    { title: 'Proceed to Full Curation', value: 'proceed' },
    { title: 'Needs More Evidence', value: 'more_evidence' },
    { title: 'Do Not Curate', value: 'do_not_curate' }
  ]

  /**
   * Get short label for curation type (for chip display)
   */
  function getCurationTypeShortLabel(type) {
    const labels = {
      single_from_list: 'Single Entity',
      single_not_on_list: 'New Entity',
      isolated_phenotype: 'Isolated',
      lumped_entity: 'Lumped'
    }
    return labels[type] || type
  }

  /**
   * Handle MONDO disease selection
   * Auto-populates disease name with gene-associated naming pattern
   */
  function handleMONDOSelect(mondoTerm) {
    if (mondoTerm && mondoTerm.label) {
      // Create dyadic name: Gene-associated disease name
      const geneSymbol = form.value.gene_symbol || 'Gene'
      const baseName = mondoTerm.label

      // Only auto-fill if disease_name is empty or matches previous auto-fill
      if (!form.value.disease_name || form.value.disease_name === form.value.mondo_disease_name) {
        form.value.disease_name = `${geneSymbol}-related ${baseName}`
      }

      logger.info('MONDO term selected, disease name updated', {
        mondo_id: mondoTerm.mondo_id,
        disease_name: form.value.disease_name
      })
    }
  }

  /**
   * Handle HPO inheritance pattern selection
   */
  function handleInheritanceSelect(inheritancePattern) {
    if (inheritancePattern) {
      logger.info('Inheritance pattern selected', {
        hpo_id: inheritancePattern.hpo_id,
        name: inheritancePattern.name,
        shortcode: inheritancePattern.shortcode
      })
    }
  }

  /**
   * Load scope and get precuration schema from workflow pair
   */
  async function loadScopeAndSchema() {
    try {
      scope.value = await scopesAPI.getScopeById(scopeId.value)

      if (scope.value?.default_workflow_pair_id) {
        const workflowPairs = await schemasAPI.getWorkflowPairs()
        const workflowPair = workflowPairs.find(
          wp => wp.id === scope.value.default_workflow_pair_id
        )
        if (workflowPair?.precuration_schema_id) {
          precurationSchemaId.value = workflowPair.precuration_schema_id
        }
      }

      logger.debug('Scope and schema loaded', {
        scope_id: scopeId.value,
        precuration_schema_id: precurationSchemaId.value
      })
    } catch (err) {
      logger.error('Failed to load scope', { error: err.message })
    }
  }

  /**
   * Load gene information
   */
  async function loadGene() {
    try {
      const gene = await genesAPI.getGeneById(geneId.value)
      form.value.gene_id = gene.id || gene.gene_id
      form.value.gene_symbol = gene.gene_symbol || gene.approved_symbol || ''
      form.value.gene_name = gene.gene_name || gene.approved_name || ''
      form.value.hgnc_id = gene.hgnc_id || ''
      form.value.ncbi_gene_id = gene.ncbi_gene_id || gene.entrez_id || ''

      logger.debug('Gene loaded for precuration', {
        gene_id: geneId.value,
        gene_symbol: form.value.gene_symbol
      })
    } catch (err) {
      logger.error('Failed to load gene', { error: err.message })
      loadError.value = `Could not load gene information: ${err.message}`
      throw err
    }
  }

  /**
   * Handle form submission
   */
  async function handleSubmit() {
    const { valid } = await formRef.value.validate()
    if (!valid) return

    saving.value = true
    try {
      // Build evidence_data with all ClinGen-compliant fields
      const evidenceData = {
        // Disease entity definition
        disease_name: form.value.disease_name,
        mondo_id: form.value.mondo_id,
        mode_of_inheritance: form.value.mode_of_inheritance,
        evaluation_date: form.value.evaluation_date,
        // Lumping & Splitting (per ClinGen guidelines)
        curation_type: form.value.curation_type,
        rationale: form.value.rationale,
        included_mim_phenotypes: form.value.included_mim_phenotypes.map(mim => ({
          mim_number: mim,
          name: '',
          inheritance: ''
        })),
        excluded_mim_phenotypes: form.value.excluded_mim_phenotypes.map(mim => ({
          mim_number: mim,
          name: '',
          inheritance: ''
        })),
        supporting_pmids: form.value.supporting_pmids,
        rationale_notes: form.value.rationale_notes,
        // Evidence assessment
        evidence_strength: form.value.evidence_strength,
        recommendation: form.value.recommendation,
        literature_summary: form.value.literature_summary,
        notes: form.value.notes
      }

      // Create precuration using the API
      const precuration = await precurationsAPI.createPrecuration({
        gene_id: form.value.gene_id,
        scope_id: scopeId.value,
        precuration_schema_id: precurationSchemaId.value,
        evidence_data: evidenceData
      })

      logger.info('Precuration created', {
        precuration_id: precuration.id,
        gene_id: geneId.value,
        scope_id: scopeId.value,
        curation_type: form.value.curation_type
      })

      // Mark precuration as complete (ready for curation without peer review)
      await precurationsAPI.completePrecuration(precuration.id)

      logger.info('Precuration marked as complete', {
        precuration_id: precuration.id
      })

      notificationStore.addToast('Precuration completed successfully', 'success')

      // Navigate back to scope dashboard genes tab
      router.push({
        name: 'scope-dashboard',
        params: { scopeId: scopeId.value, tab: 'genes' }
      })
    } catch (err) {
      logger.error('Failed to save precuration', { error: err.message })
      notificationStore.addToast(`Failed to save precuration: ${err.message}`, 'error')
    } finally {
      saving.value = false
    }
  }

  /**
   * Handle cancel
   */
  function handleCancel() {
    router.push({
      name: 'scope-dashboard',
      params: { scopeId: scopeId.value }
    })
  }

  // Lifecycle
  onMounted(async () => {
    loading.value = true
    loadError.value = null

    try {
      // Load scope and schema first
      await loadScopeAndSchema()

      // Then load gene info
      if (geneId.value) {
        await loadGene()
      } else {
        loadError.value = 'No gene specified. Please select a gene from the scope dashboard.'
      }
    } catch (err) {
      // Error already set by loadGene
      logger.error('Failed to initialize precuration form', { error: err.message })
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  /* Header styling */
  h1 {
    font-weight: 600;
  }

  .gap-2 {
    gap: 8px;
  }

  /* Ensure proper spacing */
  .v-container {
    max-width: 1200px;
  }

  /* Form sections */
  .text-subtitle-2 {
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface));
  }
</style>
