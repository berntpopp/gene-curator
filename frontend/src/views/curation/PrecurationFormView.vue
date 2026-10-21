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
              <v-btn variant="outlined" @click="handleCancel">Go back</v-btn>
            </template>
          </v-alert>
        </v-col>
      </v-row>
    </template>

    <!-- Main Content -->
    <template v-else>
      <v-row>
        <v-col cols="12">
          <div class="d-flex align-center mb-4">
            <v-btn
              icon="mdi-arrow-left"
              variant="text"
              class="mr-2"
              aria-label="Go back"
              @click="handleCancel"
            />
            <h1 class="text-h5">{{ formGene.symbol || 'Unknown gene' }}</h1>
            <span class="text-medium-emphasis ml-3">
              {{ scope?.display_name || 'Scope' }} &middot; Precuration
            </span>
            <v-spacer />
            <a
              v-if="gene?.hgnc_id"
              :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.hgnc_id}`"
              target="_blank"
              rel="noopener"
            >
              HGNC
            </a>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <!-- Schema-driven form replaces hardcoded panels -->
          <SchemaDrivenPrecurationForm
            v-if="precurationSchemaId"
            :schema-id="precurationSchemaId"
            :scope-id="scopeId"
            :precuration-id="precurationId"
            :gene-id="geneId"
            :gene="formGene"
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

<script setup lang="ts">
  /**
   * PrecurationFormView
   *
   * Scope-aware view for creating precurations.
   * Precurations are preliminary assessments before full curation.
   *
   * Route: /scopes/:scopeId/genes/:geneId/precuration/new
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
  import { usePrecurationsStore } from '@/stores/precurations'
  import { useAuthStore } from '@/stores/auth'
  import SchemaDrivenPrecurationForm from '@/components/forms/SchemaDrivenPrecurationForm.vue'

  interface ScopeRecord {
    default_workflow_pair_id?: string | null
    display_name?: string | null
  }

  interface GeneRecord {
    approved_symbol?: string | null
    hgnc_id?: string | null
  }

  interface WorkflowPairRecord {
    id: string
    precuration_schema_id?: string | null
  }

  interface ErrorLike {
    message?: string
  }

  const router = useRouter()
  const route = useRoute()
  const notificationsStore = useNotificationsStore()
  const logger = useLogger()
  const precurationsStore = usePrecurationsStore()
  const authStore = useAuthStore()

  // Route params
  const scopeId = computed(() => route.params.scopeId as string)
  const precurationId = computed(() => route.params.precurationId as string | undefined)
  // On the edit route the gene comes from the precuration itself
  const loadedGeneId = ref<string | undefined>(undefined)
  const geneId = computed(() => (route.params.geneId as string | undefined) ?? loadedGeneId.value)

  // State
  const scope = ref<ScopeRecord | null>(null)
  // Undefined until loaded. Typed non-null because vue-tsc drops v-if narrowing inside slot closures.
  const gene = ref(undefined as unknown as GeneRecord)
  // The API field is `approved_symbol`; the form reads `gene.symbol`
  const formGene = computed(() => ({ symbol: gene.value?.approved_symbol }))
  const precurationSchemaId = ref<string | undefined>(undefined)
  const loading = ref(true)
  const loadError = ref<string | null>(null)
  const readonly = ref(false)

  /**
   * Load scope and get precuration schema from workflow pair
   */
  async function loadScopeAndSchema() {
    try {
      scope.value = await scopesAPI.getScopeById(scopeId.value)

      if (scope.value?.default_workflow_pair_id) {
        const workflowPairs = (await schemasAPI.getWorkflowPairs()) as WorkflowPairRecord[]
        const workflowPair = workflowPairs.find(
          wp => wp.id === scope.value?.default_workflow_pair_id
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
      const e = err as ErrorLike
      logger.error('Failed to load scope', { error: e.message })
      loadError.value = `Could not load scope information: ${e.message}`
      throw err
    }
  }

  /**
   * Load gene information
   */
  async function loadGene() {
    if (!geneId.value) return

    try {
      gene.value = (await genesAPI.getGeneById(geneId.value)) as GeneRecord
      logger.debug('Gene loaded for precuration', {
        gene_id: geneId.value,
        gene_symbol: gene.value?.approved_symbol
      })
    } catch (err) {
      const e = err as ErrorLike
      logger.error('Failed to load gene', { error: e.message })
      loadError.value = `Could not load gene information: ${e.message}`
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

      if (precurationId.value) {
        const precuration = await precurationsStore.fetchPrecurationById(precurationId.value)
        loadedGeneId.value = precuration.gene_id
        // Editable only by its author, in this scope, while draft or sent back (rejected)
        const mine = precuration.created_by === (authStore.user as { id?: string } | null)?.id
        readonly.value =
          !mine ||
          precuration.scope_id !== scopeId.value ||
          !['draft', 'rejected'].includes(precuration.status)
      }

      if (geneId.value) {
        await loadGene()
      } else {
        loadError.value = 'No gene specified. Please select a gene from the scope dashboard.'
      }
    } catch (err) {
      loadError.value ||= `Could not load precuration: ${(err as ErrorLike).message}`
      logger.error('Failed to initialize precuration form', { error: (err as ErrorLike).message })
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

  /* Ensure proper spacing */
  .v-container {
    max-width: 1200px;
  }
</style>
