<template>
  <v-container fluid class="workspace">
    <WorkspaceHeader
      v-if="!notFound"
      :crumbs="crumbs"
      :title="gene?.approved_symbol || (isEdit ? 'Curation' : 'New curation')"
      :subtitle="frame.meta.value.disease"
      :moi="frame.meta.value.moi"
      :relationship="frame.meta.value.relationship"
      :stage="curation?.workflow_stage ?? 'curation'"
      :archived="curation?.status === 'archived'"
      :state="guard.denied.value || guard.failed.value ? undefined : frame.state.value"
      :saved-at="frame.savedAt.value"
      :readonly="readonly"
      :show-submit="frame.hasSubmit.value"
      :can-submit="frame.canSubmit.value"
      :blockers="frame.blockers.value"
      :saving="frame.state.value === 'saving'"
      @save="frame.save()"
      @submit="frame.submit()"
      @retry="frame.save()"
    />

    <ReviewFeedbackPanel
      v-if="curationId && !loading && !isActive && !notFound"
      :curation-id="curationId"
      :scope-id="scopeId"
      :me="myId"
      :evidence="curation?.evidence_data"
    />

    <v-alert
      v-if="readonlyReason && !loading"
      data-testid="ws-readonly"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      {{ readonlyReason }}
      <template #append>
        <v-btn variant="text" @click="openDetail">Open curation</v-btn>
      </template>
    </v-alert>

    <NoCurateAccess
      v-if="guard.denied.value || guard.failed.value"
      :scope-id="scopeId"
      :failed="guard.failed.value"
      @retry="loadData"
    />
    <v-alert
      v-else-if="notFound"
      data-testid="curation-not-found"
      type="warning"
      variant="tonal"
      prominent
    >
      <v-alert-title>Curation not found</v-alert-title>
      This curation does not exist, or you are not a member of its scope.
      <template #append>
        <v-btn variant="outlined" :to="{ name: 'Home' }">Go home</v-btn>
      </template>
    </v-alert>
    <v-card v-else-if="choices.length" data-testid="entity-choices" variant="outlined">
      <v-card-title>Choose the disease entity</v-card-title>
      <v-card-subtitle>This gene has several disease entities in this scope.</v-card-subtitle>
      <v-list>
        <v-list-item
          v-for="c in choices"
          :key="c.id"
          :title="c.label"
          append-icon="mdi-chevron-right"
          @click="pick(c.to)"
        />
      </v-list>
    </v-card>
    <div v-else :class="['ws-grid', { 'ws-grid--panel': showPanel }]">
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
            :readonly="readonly"
            :gene="formGene"
            :prefill-from="prefillFrom"
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

      <aside v-if="showPanel" class="ws-panel" aria-label="Score">
        <ScorePanel
          :score="frame.score.value"
          :loading="frame.scorePending.value"
          :can-submit="frame.canSubmit.value"
          :readonly="readonly"
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
   * Schema resolution: the curation's or its precuration's pair, else the scope default (resolvedSchemaId).
   */

  import { ref, computed, watch, onMounted, provide } from 'vue'
  import { useRouter, useRoute, type RouteLocationRaw } from 'vue-router'
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
  import NoCurateAccess from '@/components/workspace/NoCurateAccess.vue'
  import { useCurateGuard } from '@/components/workspace/useCurateGuard'
  import ReviewFeedbackPanel from '@/components/workspace/ReviewFeedbackPanel.vue'
  import { useAuthStore } from '@/stores/auth'
  import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'
  import { useUnsavedGuard } from '@/components/workspace/useUnsavedGuard'
  import { useSaveShortcut } from '@/composables/useSaveShortcut'
  import { entityChoices, label } from './entityChoices'
  import { allowedPairIds, allowedPairs } from '@/components/scope/useWorkflowPairs'

  interface CurationFormRecord {
    curation_schema_id?: string | null
    workflow_pair_id?: string | null
    lock_version?: number | null
    can_edit?: boolean
    gene_id?: string | null
    workflow_stage?: string | null
    status?: string | null
    curator_name?: string | null
    evidence_data?: Record<string, unknown> | null
  }

  interface ScopeRecord {
    default_workflow_pair_id?: string | null
    allowed_workflow_pair_ids?: string[] | null
    display_name?: string | null
    is_active?: boolean
  }

  interface WorkflowPairRecord {
    id: string
    precuration_schema_id?: string | null
    curation_schema_id?: string | null
  }

  interface SchemaRecord {
    id: string
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
  const myId = computed(() => (useAuthStore().user as { id?: string } | null)?.id ?? '')

  // Route params
  const scopeId = computed(() => route.params.scopeId as string)
  const curationId = computed<RouteId>(() => (route.params.curationId as string) || undefined)
  const geneId = computed<RouteId>(
    () => (route.params.geneId as string) || (route.query.gene_id as string) || undefined
  )

  // Re-curation: the active curation the new one starts from
  const prefillFrom = computed<RouteId>(() => (route.query.from as string) || undefined)

  const effectiveGeneId = computed<RouteId>(
    () => geneId.value ?? curation.value?.gene_id ?? undefined
  )

  const guard = useCurateGuard(() => scopeId.value)

  // State
  const loading = ref(true)
  // The API hides curations and scopes the user may not see (404/403): show that, not an empty form
  const notFound = ref(false)
  const hidden = (error: unknown) =>
    [403, 404].includes((error as { response?: { status?: number } }).response?.status ?? 0)
  const formReady = ref(false)
  const selectedSchemaId = ref<string | undefined>(undefined)
  const curation = ref<CurationFormRecord | null>(null)
  const gene = ref<{ approved_symbol?: string } | undefined>(undefined)
  // The form shows `gene.symbol`; the API field is `approved_symbol`
  const formGene = computed(() => (gene.value ? { symbol: gene.value.approved_symbol } : undefined))
  const scope = ref<ScopeRecord | null>(null)
  const pendingPrecurationId = ref<string | undefined>(undefined)
  // Schema of the approved precuration a new curation starts from: it picks the pair (MUI-03)
  const precurationSchemaId = ref<string | undefined>(undefined)
  const precurationStatus = ref<'approved' | 'pending' | 'none' | null>(null) // null until checked
  // Several disease entities (#530): the user picks one instead of getting the first
  const choices = ref<{ id: string; label: string; to: RouteLocationRaw }[]>([])

  const isActive = computed(() => curation.value?.workflow_stage === 'active')
  // Saving is only possible for a draft or returned curation the user may edit (backend `can_edit`)
  const readonlyReason = computed(() => {
    if (curation.value?.status === 'archived') {
      return 'This curation is archived and read-only. A newer curation replaced it.'
    }
    if (isActive.value) {
      return 'This curation is active and read-only. Start a re-curation from the curation page.'
    }
    if (curation.value?.can_edit !== false) return ''
    // MUI-22: the scope's state outranks the author rule (the server answers 409 for it)
    if (scope.value?.is_active === false) {
      return 'This scope is inactive; its curations are read-only.'
    }
    if (!['draft', 'rejected'].includes(curation.value.status ?? '')) {
      return 'Read-only: this curation is in review. It can be edited again if changes are requested.'
    }
    // The author or a scope admin saves a draft (#284; e.g. the one approval created)
    return curation.value.curator_name
      ? `Read-only: this curation belongs to ${curation.value.curator_name}. Only its author or a scope admin can edit it.`
      : 'Read-only: you do not have permission to edit this curation.'
  })
  const readonly = computed(() => !!readonlyReason.value)

  // Workspace frame: the form fills it in (save state, score, submit); the shell shows it
  const frame = createWorkspaceFrame()
  provide(WORKSPACE_FRAME, frame)
  useUnsavedGuard(frame.dirty)
  useSaveShortcut(
    () => frame.save(),
    () => formReady.value && !readonly.value
  )
  // A create refused for an open curation (409, e.g. a legacy one covering the gene): open it
  watch(
    () => curationsStore.error?.openCurationId,
    id => {
      if (id && !curationId.value)
        router.replace({
          name: 'curation-edit',
          params: { scopeId: scopeId.value, curationId: id }
        })
    }
  )
  const showPanel = computed(() => formReady.value)

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
    // A new curation (a re-curation prefill too) has nothing on the server yet (#470)
    frame.markClean(curationId.value ? undefined : {})
  }

  function openDetail() {
    router.push({
      name: 'curation-detail',
      params: { scopeId: scopeId.value, curationId: curationId.value }
    })
  }

  // Determine if edit mode
  const isEdit = computed(() => !!curationId.value)

  // Pairs this scope allows (#284) and their curation schemas (curation or combined types)
  const scopePairs = computed(() =>
    allowedPairs(schemasStore.workflowPairs as WorkflowPairRecord[], scope.value)
  )
  const availableSchemas = computed<SchemaRecord[]>(() => {
    const all = schemasStore.getCurationSchemas as SchemaRecord[]
    if (!allowedPairIds(scope.value)) return all
    return all.filter(s => scopePairs.value.some(wp => wp.curation_schema_id === s.id))
  })

  const pairById = (id?: string | null) =>
    id ? (schemasStore.workflowPairs as WorkflowPairRecord[]).find(wp => wp.id === id) : undefined

  // The approved precuration's own pair (the scope default when it is one of them), as the
  // backend picks it when approval creates the curation (MUI-03, #609)
  const precurationPair = computed(() => {
    if (!precurationSchemaId.value) return undefined
    const own = scopePairs.value.filter(
      wp => wp.precuration_schema_id === precurationSchemaId.value
    )
    return own.find(wp => wp.id === scope.value?.default_workflow_pair_id) ?? own[0]
  })

  // The curation's (or its precuration's) pair decides; the scope default only when neither is known
  const resolvedSchemaId = computed<string | undefined>(() => {
    const fromPair = (id?: string | null) => pairById(id)?.curation_schema_id ?? undefined
    return (
      curation.value?.curation_schema_id ??
      fromPair(curation.value?.workflow_pair_id) ??
      selectedSchemaId.value ??
      ((route.query.schema_id as string | undefined) || undefined) ??
      precurationPair.value?.curation_schema_id ??
      fromPair(scope.value?.default_workflow_pair_id) ??
      (availableSchemas.value.length === 1 ? availableSchemas.value[0]?.id : undefined)
    )
  })

  const resolvedWorkflowPairId = computed<string | undefined>(
    () =>
      curation.value?.workflow_pair_id ??
      precurationPair.value?.id ??
      scope.value?.default_workflow_pair_id ??
      scopePairs.value.find(wp => wp.curation_schema_id === resolvedSchemaId.value)?.id
  )

  function handleSchemaSelected(schemaId: string) {
    selectedSchemaId.value = schemaId
    logger.debug('Schema selected', { schemaId })
  }

  // The form emits the submitted curation's id (the store's current one may be a re-curation source)
  function handleSubmit(submittedId?: string) {
    frame.markClean() // submitted: nothing left to lose
    notificationsStore.addToast('Curation submitted successfully', 'success')
    const id = submittedId || curationsStore.currentCuration?.id || curationId.value
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
    notFound.value = false
    try {
      // Starting a curation needs a curator role; opening an existing one does not
      if (!curationId.value) {
        await guard.check()
        if (!guard.allowed.value) return
      }

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
        // Nobody edits an active curation: /edit (e.g. a viewer's link) opens the detail (#485)
        if (curation.value.status === 'active') {
          router.replace({
            name: 'curation-detail',
            params: { scopeId: scopeId.value, curationId: curationId.value }
          })
          return
        }
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
        // One open curation per entity: open it (e.g. the draft approval created)
        const entityOf = { scope_id: scopeId.value, gene_id: geneId.value }
        const { curations } = await curationsStore.fetchCurations(entityOf)
        const candidates = curations.filter(c => !['active', 'archived'].includes(c.status))
        const actives = curations.filter(c => c.status === 'active')
        // ?recurate (gene list): re-curate the gene's active curation, or pick one
        const recurate = route.query.recurate !== undefined
        if (recurate && !prefillFrom.value && actives.length > 1) {
          await offer(actives, id => ({ query: { from: id } }))
          return
        }
        const from = prefillFrom.value ?? (recurate ? actives[0]?.id : undefined)
        if (from && from !== prefillFrom.value) router.replace({ query: { from } })
        // Several approved entities (#530): ask, then open, re-curate or start the chosen one
        const chosen = route.query.precuration_id as RouteId
        if (chosen) return await startEntity({ ...entityOf, precuration_id: chosen })
        if (!from) {
          const approved = { ...entityOf, status: 'approved' }
          const { precurations } = await precurationsStore.fetchPrecurations(approved)
          if (precurations.length > 1) {
            const kept = curations.filter(c => c.status !== 'archived')
            const linked = await Promise.all(kept.map(c => curationsStore.fetchCurationById(c.id)))
            choices.value = entityChoices(precurations, linked, scopeId.value)
            return
          }
        }
        if (!from && candidates.length > 1) {
          await offer(candidates, id => ({
            name: 'curation-edit',
            params: { scopeId: scopeId.value, curationId: id }
          }))
          return
        }
        const open = from ? await sameEntity(from, candidates) : candidates[0]
        if (open) {
          router.replace({
            name: 'curation-edit',
            params: { scopeId: scopeId.value, curationId: open.id }
          })
          return
        }

        await checkPrecurationStatus(geneId.value)

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
      if (hidden(error)) notFound.value = true
      else notificationsStore.addToast('Failed to load data', 'error')
    } finally {
      loading.value = false
    }
  }

  async function offer(rows: { id: string }[], to: (id: string) => RouteLocationRaw) {
    choices.value = await Promise.all(
      rows.map(async ({ id }) => {
        const c = await curationsStore.fetchCurationById(id)
        return { id, label: label(c, c.status), to: to(id) }
      })
    )
  }

  // The list shows summaries without the schema: read the precuration itself. Unreadable, the
  // backend still puts the curation on the precuration's own pair (#609)
  async function loadPrecurationPair(id: string) {
    const full = await precurationsStore.fetchPrecurationById(id).catch(() => undefined)
    precurationSchemaId.value = full?.precuration_schema_id ?? undefined
  }

  async function startEntity(body: { scope_id: string; gene_id: string; precuration_id: string }) {
    await loadPrecurationPair(body.precuration_id)
    const workflow_pair_id = resolvedWorkflowPairId.value ?? ''
    // a 409 names the entity's open curation, which the openCurationId watcher opens
    const created = await curationsStore
      .createCuration({ ...body, workflow_pair_id, evidence_data: {} })
      .catch(error => (curationsStore.error?.openCurationId ? null : Promise.reject(error)))
    const params = { scopeId: scopeId.value, curationId: created?.id }
    if (created) await router.replace({ name: 'curation-edit', params })
  }

  async function pick(to: RouteLocationRaw) {
    choices.value = []
    await router.replace(to)
    await loadData()
  }

  /** A re-curation only meets an open curation of its own disease entity (#530): the same
   * precuration, or the same MONDO id and mode of inheritance (AD and AR are two entities). */
  async function sameEntity<T extends { id: string }>(sourceId: string, candidates: T[]) {
    if (!candidates.length) return undefined
    const source = await curationsStore.fetchCurationById(sourceId)
    for (const c of candidates) {
      const other = await curationsStore.fetchCurationById(c.id)
      const same =
        (source.precuration_id && source.precuration_id === other.precuration_id) ||
        (source.mondo_id === other.mondo_id &&
          source.mode_of_inheritance === other.mode_of_inheritance)
      if (same) return c
    }
    return undefined
  }

  async function loadScope() {
    try {
      scope.value = (await scopesStore.fetchScope(scopeId.value)) as ScopeRecord
    } catch (error) {
      logger.error('Failed to load scope', { error: (error as ErrorLike).message })
      if (hidden(error)) notFound.value = true
    }
  }

  async function checkPrecurationStatus(curationGeneId: string) {
    try {
      const precuration = await precurationsStore.fetchCurationPrecuration(
        curationGeneId,
        scopeId.value
      )
      if (precuration?.status === 'approved') {
        precurationStatus.value = 'approved'
        await loadPrecurationPair(precuration.id)
      } else if (precuration) {
        precurationStatus.value = 'pending'
        pendingPrecurationId.value = precuration.id
      } else {
        precurationStatus.value = 'none'
      }

      logger.debug('Precuration status checked', {
        status: precurationStatus.value,
        precurationCount: precuration ? 1 : 0
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
