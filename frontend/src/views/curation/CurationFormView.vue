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
          <h1 class="text-h4">
            {{ isEdit ? 'Edit Curation' : 'New Curation' }}
          </h1>
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <!-- Loading State -->
        <v-skeleton-loader v-if="loading" type="card" />

        <!-- Schema Selection (if not determined and multiple available) -->
        <CurationSchemaSelect
          v-else-if="!resolvedSchemaId && availableSchemas.length > 1"
          v-model="selectedSchemaId"
          :scope-id="scopeId"
          @update:model-value="handleSchemaSelected"
        />

        <!-- Dynamic Form (schema-driven) -->
        <SchemaDrivenCurationForm
          v-else-if="resolvedSchemaId"
          :schema-id="resolvedSchemaId"
          :workflow-pair-id="resolvedWorkflowPairId"
          :curation-id="curationId"
          :scope-id="scopeId"
          :gene-id="geneId"
          :gene="gene"
          @submit="handleSubmit"
          @cancel="handleCancel"
          @saved="handleSaved"
        />

        <!-- No Schema Available -->
        <v-alert v-else type="error" variant="tonal">
          <template #prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          <div class="font-weight-medium">No Curation Schema Available</div>
          <div class="text-body-2 mt-1">
            This scope does not have a curation schema configured. Please contact an administrator.
          </div>
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  /**
   * CurationFormView
   *
   * Scope-aware wrapper for creating/editing curations.
   * Implements schema resolution with 5-level priority chain.
   *
   * Schema Resolution Priority:
   * 1. Existing curation's curation_schema_id
   * 2. User selected schema (selectedSchemaId ref)
   * 3. Route query param (schema_id)
   * 4. Workflow pair default for scope
   * 5. Single available schema auto-select
   *
   * Routes:
   * - /scopes/:scopeId/curations/new (new curation)
   * - /scopes/:scopeId/curations/:curationId/edit (edit existing)
   * - /scopes/:scopeId/genes/:geneId/curation/new (new from gene)
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { useSchemasStore } from '@/stores/schemas'
  import { useScopesStore } from '@/stores/scopes'
  import { useCurationsStore } from '@/stores/curations'
  import { usePrecurationsStore } from '@/stores/precurations'
  import { useGenesStore } from '@/stores/genes'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import SchemaDrivenCurationForm from '@/components/forms/SchemaDrivenCurationForm.vue'
  import CurationSchemaSelect from '@/components/forms/CurationSchemaSelect.vue'

  const router = useRouter()
  const route = useRoute()
  const logger = useLogger()
  const schemasStore = useSchemasStore()
  const scopesStore = useScopesStore()
  const curationsStore = useCurationsStore()
  const precurationsStore = usePrecurationsStore()
  const genesStore = useGenesStore()
  const notificationsStore = useNotificationsStore()

  // Route params
  const scopeId = computed(() => route.params.scopeId)
  const curationId = computed(() => route.params.curationId || null)
  const geneId = computed(() => route.params.geneId || route.query.gene_id || null)

  // State
  const loading = ref(true)
  const selectedSchemaId = ref(null)
  const curation = ref(null)
  const gene = ref(null)
  const scope = ref(null)
  const precurationStatus = ref(null) // 'approved', 'pending', 'none'

  // Determine if edit mode
  const isEdit = computed(() => !!curationId.value)

  // Available curation schemas for this scope (curation or combined types)
  const availableSchemas = computed(() => schemasStore.getCurationSchemas)

  // Schema resolution with clear 5-level priority chain
  const resolvedSchemaId = computed(() => {
    // Priority 1: Existing curation has schema
    if (curation.value?.curation_schema_id) {
      return curation.value.curation_schema_id
    }

    // Priority 2: User selected schema
    if (selectedSchemaId.value) {
      return selectedSchemaId.value
    }

    // Priority 3: Route query param (admin override)
    if (route.query.schema_id) {
      return route.query.schema_id
    }

    // Priority 4: Workflow pair default for scope (FIXED: use scope.default_workflow_pair_id)
    if (scope.value?.default_workflow_pair_id) {
      const workflowPair = schemasStore.workflowPairs.find(
        wp => wp.id === scope.value.default_workflow_pair_id
      )
      if (workflowPair?.curation_schema_id) {
        return workflowPair.curation_schema_id
      }
    }

    // Priority 5: Only one schema available - auto-select it
    if (availableSchemas.value.length === 1) {
      return availableSchemas.value[0].id
    }

    return null
  })

  // Resolve workflow pair ID from schema or scope default
  const resolvedWorkflowPairId = computed(() => {
    // Priority 1: Existing curation has workflow pair
    if (curation.value?.workflow_pair_id) {
      return curation.value.workflow_pair_id
    }

    // Priority 2: Scope's default workflow pair
    if (scope.value?.default_workflow_pair_id) {
      return scope.value.default_workflow_pair_id
    }

    // Priority 3: Find workflow pair that uses the resolved schema
    if (resolvedSchemaId.value) {
      const workflowPair = schemasStore.workflowPairs.find(
        wp => wp.curation_schema_id === resolvedSchemaId.value
      )
      if (workflowPair) {
        return workflowPair.id
      }
    }

    return null
  })

  function handleSchemaSelected(schemaId) {
    selectedSchemaId.value = schemaId
    logger.debug('Schema selected', { schemaId })
  }

  function handleSubmit(curationData) {
    notificationsStore.addToast('Curation submitted successfully', 'success')
    router.push({
      name: 'curation-detail',
      params: {
        scopeId: scopeId.value,
        curationId: curationData?.id || curationData?.curation_id || curationId.value
      }
    })
  }

  function handleCancel() {
    // Navigate back to scope dashboard or previous page
    if (geneId.value) {
      router.push({
        name: 'scope-dashboard',
        params: { scopeId: scopeId.value }
      })
    } else {
      router.back()
    }
  }

  function handleSaved() {
    notificationsStore.addToast('Draft saved', 'info')
  }

  async function loadData() {
    loading.value = true
    try {
      // Load schemas, workflow pairs, and scope in parallel
      await Promise.all([
        schemasStore.fetchSchemas(),
        schemasStore.fetchWorkflowPairs(),
        loadScope()
      ])

      // Load existing curation if editing
      if (curationId.value) {
        curation.value = await curationsStore.fetchCurationById(curationId.value)
      }

      // Load gene info if available
      if (geneId.value) {
        gene.value = await genesStore.fetchGeneById(geneId.value)
      }

      // Check precuration status for new curations (not edits)
      if (!curationId.value && geneId.value) {
        await checkPrecurationStatus()

        // Redirect if no approved precuration exists
        if (precurationStatus.value !== 'approved') {
          notificationsStore.addToast(
            'Please complete and approve a precuration before starting curation',
            'warning'
          )
          router.push({
            name: 'gene-precuration-create',
            params: { scopeId: scopeId.value, geneId: geneId.value }
          })
          return
        }
      }

      logger.debug('CurationFormView data loaded', {
        schemasCount: schemasStore.schemas.length,
        curationId: curationId.value,
        geneId: geneId.value,
        resolvedSchemaId: resolvedSchemaId.value,
        precurationStatus: precurationStatus.value
      })
    } catch (error) {
      logger.error('Failed to load curation data', { error: error.message })
      notificationsStore.addToast('Failed to load data', 'error')
    } finally {
      loading.value = false
    }
  }

  async function loadScope() {
    try {
      scope.value = await scopesStore.fetchScope(scopeId.value)
    } catch (error) {
      logger.error('Failed to load scope', { error: error.message })
    }
  }

  async function checkPrecurationStatus() {
    try {
      // Fetch precurations for this gene in this scope
      await precurationsStore.fetchPrecurations({
        scope_id: scopeId.value,
        gene_id: geneId.value
      })

      // Check for approved precuration
      const precurations = precurationsStore.precurations || []
      const approvedPrecuration = precurations.find(p => p.status === 'approved')

      if (approvedPrecuration) {
        precurationStatus.value = 'approved'
      } else if (precurations.length > 0) {
        precurationStatus.value = 'pending'
      } else {
        precurationStatus.value = 'none'
      }

      logger.debug('Precuration status checked', {
        status: precurationStatus.value,
        precurationCount: precurations.length
      })
    } catch (error) {
      logger.error('Failed to check precuration status', { error: error.message })
      precurationStatus.value = 'none'
    }
  }

  onMounted(() => {
    loadData()
  })
</script>

<style scoped>
  /* Header styling */
  h1 {
    font-weight: 600;
  }

  /* Ensure proper spacing */
  .v-container {
    max-width: 1400px;
  }
</style>
