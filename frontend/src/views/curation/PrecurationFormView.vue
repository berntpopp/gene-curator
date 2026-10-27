<template>
  <v-container>
    <NoCurateAccess
      v-if="guard.denied.value || guard.failed.value"
      :scope-id="scopeId"
      :failed="guard.failed.value"
      @retry="init"
    />

    <!-- Loading State -->
    <template v-else-if="loading">
      <v-row>
        <v-col cols="12" class="text-center py-12">
          <v-progress-circular indeterminate size="64" color="primary" />
          <div class="text-title-large mt-4 text-medium-emphasis">Loading gene information...</div>
        </v-col>
      </v-row>
    </template>

    <!-- Error State -->
    <template v-else-if="loadError">
      <v-row>
        <v-col cols="12">
          <v-alert type="error" variant="tonal" prominent>
            <v-alert-title>Could not open precuration</v-alert-title>
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
      <WorkspaceHeader
        :crumbs="crumbs"
        :title="formGene.symbol || 'Unknown gene'"
        stage="precuration"
        readonly
        :show-submit="false"
        :can-submit="false"
        :saving="false"
        :saved-at="null"
      />
      <p class="text-body-small mb-4">
        <span v-if="status" data-testid="precuration-status" class="mr-3">
          Status: {{ curationStatusLabel(status) }}
        </span>
        <a
          v-if="gene?.hgnc_id"
          :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.hgnc_id}`"
          target="_blank"
          rel="noopener"
        >
          HGNC
        </a>
      </p>

      <v-alert
        v-if="readonlyReason"
        data-testid="ws-readonly"
        type="info"
        variant="tonal"
        class="mb-4"
      >
        {{ readonlyReason }}
      </v-alert>

      <div v-if="canReview" class="d-flex flex-wrap align-center ga-2 mb-4">
        <span class="text-body-medium">This precuration is waiting for your review.</span>
        <v-spacer />
        <v-btn variant="outlined" data-testid="reject-precuration" @click="openReject">
          Request changes
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="reviewBusy"
          data-testid="approve-precuration"
          @click="approve"
        >
          Approve
        </v-btn>
      </div>

      <BaseDialog v-model="showReject" title="Request changes?" size="md">
        <v-textarea
          v-model="rejectReason"
          label="Feedback for the curator"
          rows="3"
          :maxlength="REVIEW_TEXT_MAX"
          :counter="REVIEW_TEXT_MAX"
        />
        <v-alert v-if="reviewError" type="error" variant="tonal">{{ reviewError }}</v-alert>
        <template #actions>
          <v-btn variant="text" @click="showReject = false">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :loading="reviewBusy"
            :disabled="!rejectReason.trim()"
            data-testid="reject-confirm"
            @click="confirmReject"
          >
            Request changes
          </v-btn>
        </template>
      </BaseDialog>

      <v-alert
        v-if="sentBackReason"
        type="warning"
        variant="tonal"
        class="mb-4"
        data-testid="sent-back-reason"
      >
        <v-alert-title>Changes requested{{ sentBackBy }}</v-alert-title>
        <span class="sent-back">{{ sentBackReason }}</span>
      </v-alert>

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
  import { formatDateTime } from '@/utils/format'
  import SchemaDrivenPrecurationForm from '@/components/forms/SchemaDrivenPrecurationForm.vue'
  import WorkspaceHeader from '@/components/workspace/WorkspaceHeader.vue'
  import NoCurateAccess from '@/components/workspace/NoCurateAccess.vue'
  import { useCurateGuard } from '@/components/workspace/useCurateGuard'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { REVIEW_TEXT_MAX } from '@/components/review/reviewModel'
  import { curationStatusLabel } from '@/config/status'
  import { useConfirm } from '@/composables/useConfirm'
  import { useScopesStore } from '@/stores/scopes'
  import { useWorkCountsStore } from '@/stores/workCounts'
  import { readableApiError } from '@/utils/apiErrorText'

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
  const guard = useCurateGuard(() => scopeId.value)
  // On the edit route the gene comes from the precuration itself
  const loadedGeneId = ref<string | undefined>(undefined)
  const geneId = computed(() => (route.params.geneId as string | undefined) ?? loadedGeneId.value)

  // State
  const scope = ref<ScopeRecord | null>(null)
  // Undefined until loaded. Typed non-null because vue-tsc drops v-if narrowing inside slot closures.
  const gene = ref(undefined as unknown as GeneRecord)
  // The API field is `approved_symbol`; the form reads `gene.symbol`
  const crumbs = computed(() => [
    { text: scope.value?.display_name || 'Scope', to: `/scopes/${scopeId.value}` },
    ...(geneId.value && gene.value?.approved_symbol
      ? [{ text: gene.value.approved_symbol, to: `/genes/${geneId.value}` }]
      : []),
    { text: 'Precuration' }
  ])
  const formGene = computed(() => ({ symbol: gene.value?.approved_symbol }))
  const precurationSchemaId = ref<string | undefined>(undefined)
  const sentBackReason = ref<string | null>(null)
  /** Who sent it back and when, as on the curation feedback panel: " by Bob on 21 Oct 2026, 10:00". */
  const sentBackBy = ref('')
  const loading = ref(true)
  const loadError = ref<string | null>(null)
  // Why the form is read-only; empty when the user may edit it
  const readonlyReason = ref('')
  const readonly = computed(() => !!readonlyReason.value)
  const status = ref<string | null>(null)
  // A scope reviewer or admin may review someone else's submitted precuration here (4-eyes)
  const canReview = ref(false)
  const reviewBusy = ref(false)
  const reviewError = ref<string | null>(null)
  const showReject = ref(false)
  const rejectReason = ref('')
  const { confirm } = useConfirm()

  async function approve() {
    const ok = await confirm({
      title: 'Approve precuration?',
      text: `Approve the precuration for ${formGene.value.symbol}? This lets curation start.`,
      confirmText: 'Approve'
    })
    if (ok)
      await review(() => precurationsStore.approvePrecuration(precurationId.value!), 'approved')
  }

  function openReject() {
    rejectReason.value = ''
    reviewError.value = null
    showReject.value = true
  }

  const confirmReject = () =>
    review(
      () => precurationsStore.rejectPrecuration(precurationId.value!, rejectReason.value.trim()),
      'returned to the curator'
    )

  async function review(action: () => Promise<unknown>, done: string) {
    reviewBusy.value = true
    reviewError.value = null
    try {
      await action()
      showReject.value = false
      notificationsStore.addToast(`Precuration ${done}`, 'success')
      useWorkCountsStore().fetch()
      router.push({ name: 'review-queue' })
    } catch (err) {
      reviewError.value = readableApiError(err, 'Request failed')
      if (!showReject.value) notificationsStore.addToast(reviewError.value, 'error')
    } finally {
      reviewBusy.value = false
    }
  }

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
  async function init() {
    loading.value = true
    loadError.value = null

    try {
      // Starting a precuration needs a curator role; opening an existing one (read-only) does not
      if (!precurationId.value) {
        await guard.check()
        if (!guard.allowed.value) return
      }

      // Load scope and schema first
      await loadScopeAndSchema()

      if (precurationId.value) {
        const precuration = await precurationsStore.fetchPrecurationById(precurationId.value)
        loadedGeneId.value = precuration.gene_id
        // Editable only by its author, in this scope, while draft or sent back (rejected)
        const mine = precuration.created_by === (authStore.user as { id?: string } | null)?.id
        readonlyReason.value =
          !mine || precuration.scope_id !== scopeId.value
            ? 'Read-only: only the curator who started this precuration can edit it.'
            : ['draft', 'rejected'].includes(precuration.status)
              ? ''
              : ['submitted', 'in_review'].includes(precuration.status)
                ? 'Read-only: this precuration is in review. It can be edited again if changes are requested.'
                : `Read-only: this precuration is ${precuration.status}.`
        status.value = precuration.status
        if (!mine && precuration.status === 'submitted') {
          const role = await useScopesStore()
            .fetchUserRole(precuration.scope_id)
            .catch(() => null)
          canReview.value = role === 'reviewer' || role === 'admin'
        }
        // The reviewer's reason stays visible while the precuration is sent back
        const { rejection_reason: reason, rejected_at: at } = precuration.computed_fields ?? {}
        const by = precuration.rejected_by_name
        sentBackBy.value =
          (by ? ` by ${by}` : '') + (typeof at === 'string' ? ` on ${formatDateTime(at)}` : '')
        sentBackReason.value =
          precuration.status === 'rejected' && typeof reason === 'string' ? reason : null
      }

      if (geneId.value) {
        await loadGene()
      } else {
        loadError.value = 'No gene specified. Please select a gene from the scope dashboard.'
      }
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      if ([403, 404].includes(status ?? 0))
        loadError.value =
          'Precuration not found. It does not exist, or you are not a member of its scope.'
      else loadError.value ||= `Could not load precuration: ${(err as ErrorLike).message}`
      logger.error('Failed to initialize precuration form', { error: (err as ErrorLike).message })
    } finally {
      loading.value = false
    }
  }

  onMounted(init)
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

  .sent-back {
    white-space: pre-line;
  }
</style>
