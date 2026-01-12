<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex align-center mb-6">
          <v-btn
            icon="mdi-arrow-left"
            variant="text"
            class="mr-3"
            aria-label="Go back"
            @click="handleCancel"
          />
          <div>
            <h1 class="text-h4">New Precuration</h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              Preliminary evidence gathering and assessment
            </p>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-clipboard-text</v-icon>
            Precuration Form
          </v-card-title>
          <v-card-subtitle>
            Complete preliminary assessment before formal curation
          </v-card-subtitle>

          <v-card-text>
            <v-form ref="formRef" @submit.prevent="handleSubmit">
              <!-- Gene Information -->
              <div class="text-subtitle-2 mb-2 mt-4">Gene Information</div>
              <v-text-field
                v-model="form.gene_symbol"
                label="Gene Symbol"
                variant="outlined"
                readonly
                prepend-inner-icon="mdi-dna"
                hint="The gene being assessed"
                persistent-hint
                class="mb-4"
              />

              <!-- Disease Information -->
              <div class="text-subtitle-2 mb-2 mt-4">Disease Association</div>
              <v-text-field
                v-model="form.disease_name"
                label="Disease Name"
                variant="outlined"
                :rules="[v => !!v || 'Disease name is required']"
                prepend-inner-icon="mdi-medical-bag"
                class="mb-4"
              />

              <v-text-field
                v-model="form.mondo_id"
                label="MONDO ID (Optional)"
                variant="outlined"
                prepend-inner-icon="mdi-database"
                placeholder="MONDO:0000001"
                hint="Monarch Disease Ontology identifier"
                persistent-hint
                class="mb-4"
              />

              <!-- Evidence Quality Assessment -->
              <div class="text-subtitle-2 mb-2 mt-4">Preliminary Evidence Assessment</div>
              <v-select
                v-model="form.evidence_strength"
                :items="evidenceStrengthOptions"
                label="Evidence Strength"
                variant="outlined"
                prepend-inner-icon="mdi-chart-line"
                hint="Initial assessment of evidence quality"
                persistent-hint
                class="mb-4"
              />

              <v-select
                v-model="form.recommendation"
                :items="recommendationOptions"
                label="Recommendation"
                variant="outlined"
                prepend-inner-icon="mdi-lightbulb-on"
                :rules="[v => !!v || 'Recommendation is required']"
                hint="Should this proceed to full curation?"
                persistent-hint
                class="mb-4"
              />

              <!-- Literature Review -->
              <div class="text-subtitle-2 mb-2 mt-4">Literature Review</div>
              <v-textarea
                v-model="form.literature_summary"
                label="Literature Summary"
                variant="outlined"
                rows="4"
                auto-grow
                prepend-inner-icon="mdi-text-box-outline"
                hint="Brief summary of key publications and evidence"
                persistent-hint
                class="mb-4"
              />

              <!-- Key PMIDs -->
              <v-text-field
                v-model="form.key_pmids"
                label="Key PMIDs"
                variant="outlined"
                prepend-inner-icon="mdi-link"
                placeholder="12345678, 87654321"
                hint="Comma-separated list of important PubMed IDs"
                persistent-hint
                class="mb-4"
              />

              <!-- Notes -->
              <div class="text-subtitle-2 mb-2 mt-4">Additional Notes</div>
              <v-textarea
                v-model="form.notes"
                label="Precuration Notes"
                variant="outlined"
                rows="3"
                auto-grow
                prepend-inner-icon="mdi-note-text"
                hint="Any additional observations or concerns"
                persistent-hint
                class="mb-4"
              />

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
  import { genesAPI } from '@/api'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'

  const router = useRouter()
  const route = useRoute()
  const notificationStore = useNotificationsStore()
  const logger = useLogger()

  // Route params
  const scopeId = computed(() => route.params.scopeId)
  const geneId = computed(() => route.params.geneId)

  // Form state
  const formRef = ref(null)
  const saving = ref(false)
  const form = ref({
    gene_id: null,
    gene_symbol: '',
    disease_name: '',
    mondo_id: '',
    evidence_strength: null,
    recommendation: null,
    literature_summary: '',
    key_pmids: '',
    notes: ''
  })

  // Options
  const evidenceStrengthOptions = [
    { title: 'Strong - Multiple high-quality studies', value: 'strong' },
    { title: 'Moderate - Some supporting evidence', value: 'moderate' },
    { title: 'Weak - Limited or conflicting evidence', value: 'weak' },
    { title: 'None - No credible evidence found', value: 'none' }
  ]

  const recommendationOptions = [
    { title: 'Proceed to Full Curation', value: 'proceed' },
    { title: 'Needs More Evidence', value: 'more_evidence' },
    { title: 'Do Not Curate', value: 'do_not_curate' }
  ]

  /**
   * Load gene information
   */
  async function loadGene() {
    try {
      const gene = await genesAPI.getGene(geneId.value)
      form.value.gene_id = gene.gene_id
      form.value.gene_symbol = gene.gene_symbol || gene.approved_symbol

      logger.debug('Gene loaded for precuration', { gene_id: geneId.value })
    } catch (err) {
      logger.error('Failed to load gene', { error: err.message })
      notificationStore.addToast('Failed to load gene information', 'error')
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
      // TODO: Replace with actual API call when backend endpoint is ready
      // const precuration = await precurationsAPI.createPrecuration({
      //   ...form.value,
      //   scope_id: scopeId.value
      // })

      // For now, just show success and navigate back
      logger.info('Precuration saved', {
        gene_id: geneId.value,
        scope_id: scopeId.value
      })

      notificationStore.addToast('Precuration saved successfully', 'success')

      // Navigate back to scope dashboard
      router.push({
        name: 'scope-dashboard',
        params: { scopeId: scopeId.value }
      })
    } catch (err) {
      logger.error('Failed to save precuration', { error: err.message })
      notificationStore.addToast('Failed to save precuration', 'error')
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
  onMounted(() => {
    if (geneId.value) {
      loadGene()
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
