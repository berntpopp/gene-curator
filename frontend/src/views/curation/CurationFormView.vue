<template>
  <v-container fluid class="workspace">
    <WorkspaceHeader
      :crumbs="crumbs"
      :title="gene?.approved_symbol || (isEdit ? 'Curation' : 'New curation')"
      :subtitle="frame.meta.value.disease"
      :moi="frame.meta.value.moi"
      :stage="curation?.workflow_stage ?? 'curation'"
      :archived="curation?.status === 'archived'"
      :state="frame.state.value"
      :saved-at="frame.savedAt.value"
      :readonly="isActive"
      :show-submit="frame.hasSubmit.value"
      :can-submit="frame.canSubmit.value"
      :saving="frame.state.value === 'saving'"
      :save-blocked="frame.blockers.value.length > 0"
      @save="frame.save()"
      @submit="frame.submit()"
      @retry="frame.save()"
    />

    <v-alert v-if="isActive && !loading" type="info" variant="tonal" class="mb-4">
      This curation is active and read-only. Re-curation starts from the curation page.
      <template #append>
        <v-btn variant="text" @click="openDetail">Open curation</v-btn>
      </template>
    </v-alert>

    <div :class="['ws-grid', { 'ws-grid--panel': showPanel }]">
      <div class="ws-main">
        <!-- The one skeleton: until the schema is resolved and the form reports ready -->
        <v-skeleton-loader v-if="loading || (resolvedSchemaId && !formReady)" type="card" />

        <!-- Schema Selection (if not determined and multiple available) -->
        <CurationSchemaSelect
          v-else-if="!loading && !resolvedSchemaId && availableSchemas.length > 1"
          v-model="selectedSchemaId"
          :scope-id="scopeId"
          @update:model-value="handleSchemaSelected"
        />

        <!-- Dynamic Form (schema-driven), mounted hidden so it loads behind the skeleton -->
        <div v-if="!loading && resolvedSchemaId" v-show="formReady">
          <SchemaDrivenCurationForm
            :schema-id="resolvedSchemaId"
            :workflow-pair-id="resolvedWorkflowPairId"
            :curation-id="curationId"
            :scope-id="scopeId"
            :gene-id="effectiveGeneId"
            :readonly="isActive"
            :gene="formGene"
            @submit="handleSubmit"
            @cancel="handleCancel"
            @ready="handleReady"
          />
        </div>

        <!-- No Schema Available -->
        <v-alert
          v-if="!loading && !resolvedSchemaId && availableSchemas.length <= 1"
          type="error"
          variant="tonal"
        >
          <template #prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          <div class="font-weight-medium">No Curation Schema Available</div>
          <div class="text-body-medium mt-1">
            This scope does not have a curation schema configured. Please contact an administrator.
          </div>
        </v-alert>
      </div>

      <aside v-if="showPanel && frame.score.value" class="ws-panel" aria-label="Score">
        <ScorePanel
          :score="frame.score.value"
          :can-submit="frame.canSubmit.value"
          :readonly="isActive"
          :blockers="frame.blockers.value"
        />
      </aside>
    </div>
  </v-container>
</template>

<script setup lang="ts">
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

  import { ref, computed, onMounted, provide } from 'vue'
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
  import WorkspaceHeader from '@/components/workspace/WorkspaceHeader.vue'
  import ScorePanel from '@/components/workspace/ScorePanel.vue'
  import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'
  import { useUnsavedGuard } from '@/components/workspace/useUnsavedGuard'
  import { useSaveShortcut } from '@/composables/useSaveShortcut'

  interface CurationFormRecord {
    curation_schema_id?: string | null
    workflow_pair_id?: string | null
    lock_version?: number | null
    gene_id?: string | null
    workflow_stage?: string | null
    status?: string | null
  }

  interface ScopeRecord {
    default_workflow_pair_id?: string | null
    display_name?: string | null
  }

  interface WorkflowPairRecord {
    id: string
    curation_schema_id?: string | null
  }

  interface SchemaRecord {
    id: string
  }

  interface PrecurationRecord {
    id?: string
    status: string
  }

  type ErrorLike = { message?: string }
  // undefined (not null) so values pass to child props, whose defaults are null
  type RouteId = string | undefined

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
  const scopeId = computed(() => route.params.scopeId as string)
  const curationId = computed<RouteId>(() => (route.params.curationId as string) || undefined)
  const geneId = computed<RouteId>(
    () => (route.params.geneId as string) || (route.query.gene_id as string) || undefined
  )

  const effectiveGeneId = computed<RouteId>(
    () => geneId.value ?? curation.value?.gene_id ?? undefined
  )

  // State
  const loading = ref(true)
  const formReady = ref(false)
  const selectedSchemaId = ref<string | undefined>(undefined)
  const curation = ref<CurationFormRecord | null>(null)
  const gene = ref<{ approved_symbol?: string } | undefined>(undefined)
  // The form shows `gene.symbol`; the API field is `approved_symbol`
  const formGene = computed(() => (gene.value ? { symbol: gene.value.approved_symbol } : undefined))
  const scope = ref<ScopeRecord | null>(null)
  const pendingPrecurationId = ref<string | undefined>(undefined)
  const precurationStatus = ref<'approved' | 'pending' | 'none' | null>(null) // null until checked

  const isActive = computed(() => curation.value?.workflow_stage === 'active')

  // Workspace frame: the form fills it in (save state, score, submit); the shell shows it
  const frame = createWorkspaceFrame()
  provide(WORKSPACE_FRAME, frame)
  useUnsavedGuard(frame.dirty)
  useSaveShortcut(
    () => frame.save(),
    () => formReady.value && !isActive.value
  )
  const showPanel = computed(() => formReady.value && !!frame.score.value)

  const crumbs = computed(() => [
    { text: scope.value?.display_name || 'Scope', to: `/scopes/${scopeId.value}` },
    ...(gene.value?.approved_symbol
      ? [
          {
            text: gene.value.approved_symbol,
            ...(effectiveGeneId.value ? { to: `/genes/${effectiveGeneId.value}` } : {})
          }
        ]
      : []),
    { text: 'Curation' }
  ])

  function handleReady() {
    formReady.value = true
    frame.markClean()
  }

  function openDetail() {
    router.push({
      name: 'curation-detail',
      params: { scopeId: scopeId.value, curationId: curationId.value }
    })
  }

  // Determine if edit mode
  const isEdit = computed(() => !!curationId.value)

  // Available curation schemas for this scope (curation or combined types)
  const availableSchemas = computed<SchemaRecord[]>(() => schemasStore.getCurationSchemas)

  // Schema resolution with clear 5-level priority chain
  const resolvedSchemaId = computed<string | undefined>(() => {
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
      return route.query.schema_id as string
    }

    // Priority 4: Workflow pair default for scope (FIXED: use scope.default_workflow_pair_id)
    if (scope.value?.default_workflow_pair_id) {
      const workflowPair = (schemasStore.workflowPairs as WorkflowPairRecord[]).find(
        wp => wp.id === scope.value?.default_workflow_pair_id
      )
      if (workflowPair?.curation_schema_id) {
        return workflowPair.curation_schema_id
      }
    }

    // Priority 5: Only one schema available - auto-select it
    if (availableSchemas.value.length === 1) {
      return availableSchemas.value[0]?.id
    }

    return undefined
  })

  // Resolve workflow pair ID from schema or scope default
  const resolvedWorkflowPairId = computed<string | undefined>(() => {
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
      const workflowPair = (schemasStore.workflowPairs as WorkflowPairRecord[]).find(
        wp => wp.curation_schema_id === resolvedSchemaId.value
      )
      if (workflowPair) {
        return workflowPair.id
      }
    }

    return undefined
  })

  function handleSchemaSelected(schemaId: string) {
    selectedSchemaId.value = schemaId
    logger.debug('Schema selected', { schemaId })
  }

  // The form emits `submit` without a payload; the saved curation is in the store
  function handleSubmit() {
    frame.markClean() // submitted: nothing left to lose
    notificationsStore.addToast('Curation submitted successfully', 'success')
    const id = curationsStore.currentCuration?.id || curationId.value
    if (!id) {
      router.push({ name: 'scope-dashboard', params: { scopeId: scopeId.value } })
      return
    }
    router.push({ name: 'curation-detail', params: { scopeId: scopeId.value, curationId: id } })
  }

  function handleCancel() {
    frame.markClean() // the form already asked before discarding
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

  async function loadData() {
    loading.value = true
    formReady.value = false
    try {
      // Load schemas, workflow pairs, and scope in parallel
      await Promise.all([
        schemasStore.fetchSchemas(),
        schemasStore.fetchWorkflowPairs(),
        loadScope()
      ])

      // Load existing curation if editing
      if (curationId.value) {
        curation.value = (await curationsStore.fetchCurationById(
          curationId.value
        )) as CurationFormRecord
      }

      // Load gene info if available
      if (effectiveGeneId.value) {
        gene.value =
          ((await genesStore.fetchGeneById(effectiveGeneId.value)) as {
            approved_symbol?: string
          } | null) ?? undefined
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
          // An existing, not yet approved precuration is reopened rather than duplicated
          router.push(
            pendingPrecurationId.value
              ? {
                  name: 'precuration-edit',
                  params: { scopeId: scopeId.value, precurationId: pendingPrecurationId.value }
                }
              : {
                  name: 'gene-precuration-create',
                  params: { scopeId: scopeId.value, geneId: geneId.value }
                }
          )
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
      logger.error('Failed to load curation data', { error: (error as ErrorLike).message })
      notificationsStore.addToast('Failed to load data', 'error')
    } finally {
      loading.value = false
    }
  }

  async function loadScope() {
    try {
      scope.value = (await scopesStore.fetchScope(scopeId.value)) as ScopeRecord
    } catch (error) {
      logger.error('Failed to load scope', { error: (error as ErrorLike).message })
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
      const precurations = (precurationsStore.precurations || []) as PrecurationRecord[]
      const approvedPrecuration = precurations.find(p => p.status === 'approved')

      if (approvedPrecuration) {
        precurationStatus.value = 'approved'
      } else if (precurations.length > 0) {
        precurationStatus.value = 'pending'
        pendingPrecurationId.value = precurations[0]?.id
      } else {
        precurationStatus.value = 'none'
      }

      logger.debug('Precuration status checked', {
        status: precurationStatus.value,
        precurationCount: precurations.length
      })
    } catch (error) {
      logger.error('Failed to check precuration status', { error: (error as ErrorLike).message })
      precurationStatus.value = 'none'
    }
  }

  onMounted(() => {
    loadData()
  })
</script>

<style scoped>
  .workspace {
    max-width: 1600px;
  }

  .ws-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 20px;
    align-items: start;
  }

  @media (min-width: 1280px) {
    .ws-grid--panel {
      grid-template-columns: minmax(0, 1fr) 340px;
    }

    .ws-panel {
      position: sticky;
      top: 16px;
    }
  }
</style>
