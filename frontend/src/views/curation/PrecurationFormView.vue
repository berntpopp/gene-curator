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
          <!-- Prominent Header with Gene Context (KEPT from original) -->
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
                      {{ gene?.gene_symbol || gene?.symbol || 'Unknown Gene' }}
                    </h1>
                    <v-chip
                      v-if="gene?.gene_name || gene?.name"
                      color="white"
                      variant="flat"
                      class="ml-4 text-primary"
                    >
                      {{ gene?.gene_name || gene?.name }}
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
                      {{ precurationId ? 'Edit' : 'New' }}
                    </v-chip>
                  </div>
                </div>

                <!-- Gene external links -->
                <div v-if="gene?.hgnc_id" class="d-flex flex-column ga-2">
                  <v-btn
                    size="small"
                    variant="tonal"
                    color="white"
                    :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.hgnc_id}`"
                    target="_blank"
                  >
                    <v-icon start size="small">mdi-open-in-new</v-icon>
                    HGNC
                  </v-btn>
                  <v-btn
                    v-if="gene?.ncbi_gene_id || gene?.entrez_id"
                    size="small"
                    variant="tonal"
                    color="white"
                    :href="`https://www.ncbi.nlm.nih.gov/gene/${gene.ncbi_gene_id || gene.entrez_id}`"
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
          <!-- Schema-driven form replaces hardcoded panels -->
          <SchemaDrivenPrecurationForm
            v-if="precurationSchemaId"
            :schema-id="precurationSchemaId"
            :precuration-id="precurationId"
            :scope-id="scopeId"
            :gene-id="geneId"
            :gene="gene"
            :readonly="readonly"
            @submit="handleFormSubmit"
            @cancel="handleCancel"
            @saved="handleSaved"
          />

          <v-alert v-else type="warning" variant="tonal" prominent>
            <v-alert-title>No Schema Configured</v-alert-title>
            This scope does not have a precuration schema assigned. Please contact an administrator
            to configure a workflow pair with a precuration schema.
          </v-alert>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script setup>
  /**
   * PrecurationFormView
   *
   * Scope-aware view for creating and editing precurations.
   * Precurations are preliminary assessments before full curation.
   *
   * Route: /scopes/:scopeId/genes/:geneId/precuration/new
   *        /scopes/:scopeId/precurations/:precurationId/edit
   *
   * Responsibilities:
   * - Extract route params
   * - Load gene and scope data
   * - Resolve precuration schema ID from scope workflow pair
   * - Render SchemaDrivenPrecurationForm with proper context
   * - Handle navigation after submit/cancel
   *
   * @example
   * router.push(`/scopes/${scopeId}/genes/${geneId}/precuration/new`)
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { genesAPI, scopesAPI, schemasAPI } from '@/api'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import SchemaDrivenPrecurationForm from '@/components/forms/SchemaDrivenPrecurationForm.vue'

  const router = useRouter()
  const route = useRoute()
  const notificationsStore = useNotificationsStore()
  const logger = useLogger()

  // Route params
  const scopeId = computed(() => route.params.scopeId)
  const geneId = computed(() => route.params.geneId)
  const precurationId = computed(() => route.params.precurationId || null)

  // State
  const scope = ref(null)
  const gene = ref(null)
  const precurationSchemaId = ref(null)
  const loading = ref(true)
  const loadError = ref(null)
  const readonly = ref(false)

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
      loadError.value = `Could not load scope information: ${err.message}`
      throw err
    }
  }

  /**
   * Load gene information
   */
  async function loadGene() {
    if (!geneId.value) return

    try {
      gene.value = await genesAPI.getGeneById(geneId.value)

      logger.debug('Gene loaded for precuration', {
        gene_id: geneId.value,
        gene_symbol: gene.value?.gene_symbol || gene.value?.symbol
      })
    } catch (err) {
      logger.error('Failed to load gene', { error: err.message })
      loadError.value = `Could not load gene information: ${err.message}`
      throw err
    }
  }

  /**
   * Handle form submission
   * Navigate to scope dashboard or workflow confirmation
   */
  function handleFormSubmit() {
    notificationsStore.addToast('Precuration submitted successfully', 'success')
    router.push({
      name: 'scope-dashboard',
      params: { scopeId: scopeId.value },
      query: { tab: 'genes' }
    })
  }

  /**
   * Handle cancel
   * Navigate back to scope dashboard
   */
  function handleCancel() {
    router.push({
      name: 'scope-dashboard',
      params: { scopeId: scopeId.value }
    })
  }

  /**
   * Handle draft saved
   */
  function handleSaved() {
    logger.debug('Precuration draft saved', {
      precuration_id: precurationId.value,
      scope_id: scopeId.value
    })
  }

  // Lifecycle
  onMounted(async () => {
    loading.value = true
    loadError.value = null

    try {
      // Load scope and schema first
      await loadScopeAndSchema()

      // Then load gene info (if creating new precuration)
      if (geneId.value) {
        await loadGene()
      } else if (!precurationId.value) {
        loadError.value = 'No gene specified. Please select a gene from the scope dashboard.'
      }
    } catch (err) {
      // Error already set by load functions
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
</style>
