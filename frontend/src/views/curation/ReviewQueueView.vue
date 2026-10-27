<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <div class="d-flex align-center flex-wrap ga-3 mb-6">
      <div>
        <h1 class="page-title text-headline-large font-weight-bold">Review Queue</h1>
        <p class="text-body-large text-medium-emphasis mt-1">Curations awaiting peer review</p>
      </div>
      <v-spacer />
      <v-chip color="warning" variant="flat" size="large" class="px-4">
        <v-icon start>mdi-clipboard-check-outline</v-icon>
        {{ pendingCount }} pending review{{ pendingCount !== 1 ? 's' : '' }}
      </v-chip>
    </div>

    <template v-if="loading">
      <v-row>
        <v-col v-for="n in 3" :key="n" cols="12">
          <v-skeleton-loader type="card" height="160" />
        </v-col>
      </v-row>
    </template>

    <DataTable
      v-else
      v-model:search="searchQuery"
      v-model:page="currentPage"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="sortBy"
      v-model:density="density"
      v-model:filters="filters"
      :headers="HEADERS"
      :items="pageRows"
      :items-length="filtered.length"
      :filter-defs="filterDefs"
      :row-props="() => ({ 'data-testid': 'review-row' })"
      storage-key="review-queue"
    >
      <template #toolbar-actions>
        <v-switch
          v-model="mineOnly"
          data-testid="assigned-to-me"
          label="Assigned to me"
          density="compact"
          hide-details
          color="primary"
        />
      </template>

      <template #item.gene_symbol="{ item }">
        <span class="font-weight-bold">{{ item.gene_symbol }}</span>
        <v-chip
          v-if="item.kind === 'precuration'"
          size="x-small"
          color="info"
          variant="tonal"
          class="ml-2"
        >
          Precuration
        </v-chip>
      </template>
      <template #item.status="{ item }">
        <v-chip color="warning" size="small" variant="tonal">
          {{ curationStatusLabel(item.status) }}
        </v-chip>
      </template>
      <template #item.total_score="{ item }">
        <template v-if="item.kind !== 'precuration'">
          <span class="font-mono">{{ item.total_score || 0 }}</span>
          <ClassificationMark
            v-if="item.classification"
            :classification="item.classification"
            class="ml-2"
          />
        </template>
      </template>
      <template #item.updated_at="{ item }">
        <span class="text-medium-emphasis">Updated {{ relativeTime(item.updated_at) }}</span>
      </template>
      <template #item.actions="{ item }">
        <div v-if="item.kind === 'precuration'" class="d-flex justify-end ga-2">
          <v-btn
            variant="text"
            size="small"
            :to="`/scopes/${item.scope_id}/precurations/${item.id}`"
            data-test="open-precuration"
          >
            Open
          </v-btn>
          <v-btn
            variant="outlined"
            size="small"
            color="warning"
            data-test="reject-precuration"
            @click="openReject(item)"
          >
            Request changes
          </v-btn>
          <v-btn
            color="success"
            size="small"
            :loading="busyId === item.id"
            data-test="approve-precuration"
            @click="approve(item)"
          >
            Approve
          </v-btn>
        </div>
        <v-btn
          v-else
          color="primary"
          size="small"
          :to="`/scopes/${item.scope_id}/curations/${item.id}`"
        >
          Review
        </v-btn>
      </template>
      <template #no-data>
        <div class="text-center py-8" data-testid="queue-empty">
          <p class="text-body-large mb-2">
            {{ filtersOn ? 'No matching curations' : 'No reviews waiting' }}
          </p>
          <v-btn v-if="filtersOn" variant="text" @click="clearFilters">Clear filters</v-btn>
        </div>
      </template>
    </DataTable>

    <BaseDialog v-model="showReject" title="Request changes" size="md">
      <v-textarea
        v-model="rejectReason"
        label="Feedback for the curator"
        rows="3"
        :maxlength="REVIEW_TEXT_MAX"
        :counter="REVIEW_TEXT_MAX"
      />
      <v-alert v-if="rejectError" type="error" variant="tonal">{{ rejectError }}</v-alert>
      <template #actions>
        <v-btn variant="text" @click="showReject = false">Cancel</v-btn>
        <v-btn
          color="warning"
          variant="elevated"
          :disabled="!rejectReason.trim()"
          @click="confirmReject"
        >
          Request changes
        </v-btn>
      </template>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  /**
   * ReviewQueueView
   *
   * Shows curations pending peer review across all accessible scopes.
   * Allows reviewers to filter, search, and navigate to curations for approval.
   */

  import { ref, computed, onMounted, watch } from 'vue'
  import { curationsAPI } from '@/api'
  import DataTable from '@/components/common/DataTable.vue'
  import { clientPage, relativeTime } from '@/components/common/tableRows'
  import { useTableUrlState } from '@/composables/useTableUrlState'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { REVIEW_TEXT_MAX } from '@/components/review/reviewModel'
  import { curationStatusLabel } from '@/config/status'
  import { useLogger } from '@/composables/useLogger'
  import { useConfirm } from '@/composables/useConfirm'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useScopesStore } from '@/stores/scopes'
  import { useReviewStore } from '@/stores/review'
  import { readableApiError } from '@/utils/apiErrorText'
  import { useWorkCountsStore } from '@/stores/workCounts'
  import { usePrecurationsStore } from '@/stores/precurations'
  import type { Schema } from '@/types/api'

  // A type, not an interface: DataTable rows need an index signature
  type ReviewItem = {
    kind?: 'curation' | 'precuration'
    id: string
    gene_id: string
    gene_symbol?: string | null
    disease_name?: string | null
    scope_id?: string | null
    scope_name?: string | null
    curator_name?: string | null
    status: string
    workflow_stage?: string | null
    total_score: number
    classification?: string | null
    updated_at: string
    created_at?: string | null
    created_by?: string | null
  }

  const logger = useLogger()
  const notificationStore = useNotificationsStore()
  const precurationStore = usePrecurationsStore()
  const scopesStore = useScopesStore()
  const workCounts = useWorkCountsStore()
  const { confirm } = useConfirm()
  const reviewStore = useReviewStore()

  // State
  const loading = ref(true)
  const curations = ref<ReviewItem[]>([])
  const scopes = ref<Array<{ id: string; name: string }>>([])
  // Search, scope filter, sort and page live in the URL; My work deep-links here with ?q=<gene>
  const {
    search: searchQuery,
    page: currentPage,
    itemsPerPage,
    sortBy,
    density,
    filters
  } = useTableUrlState({ filterKeys: ['scope'], pageSize: 10 })
  const selectedScope = computed(() => filters.value.scope as string | undefined)
  const mineOnly = ref(false)
  const mineIds = ref<Set<string> | null>(null)
  const busyId = ref<string | null>(null)
  const showReject = ref(false)
  const rejectReason = ref('')
  const rejectError = ref<string | null>(null)
  const rejectTarget = ref<ReviewItem | null>(null)

  const HEADERS = [
    { title: 'Gene', key: 'gene_symbol' },
    { title: 'Disease', key: 'disease_name' },
    { title: 'Scope', key: 'scope_name' },
    { title: 'Curator', key: 'curator_name' },
    { title: 'Status', key: 'status', sortable: false },
    { title: 'Score', key: 'total_score' },
    { title: 'Updated', key: 'updated_at' },
    { title: '', key: 'actions', sortable: false, align: 'end' }
  ]
  const filterDefs = computed(() => [
    {
      key: 'scope',
      label: 'Scope',
      options: scopes.value.map(s => ({ value: s.id, title: s.name }))
    }
  ])
  const filtersOn = computed(() => !!(searchQuery.value || selectedScope.value || mineOnly.value))

  const pendingCount = computed(() => curations.value.length)

  // Filtered here, sorted and paged by the table; newest first until a column is sorted
  const filtered = computed<ReviewItem[]>(() => {
    const query = searchQuery.value?.toLowerCase()
    return curations.value
      .filter(c => !selectedScope.value || c.scope_id === selectedScope.value)
      .filter(c => !mineOnly.value || !mineIds.value || mineIds.value.has(c.id))
      .filter(
        c =>
          !query ||
          c.gene_symbol?.toLowerCase().includes(query) ||
          c.curator_name?.toLowerCase().includes(query) ||
          c.disease_name?.toLowerCase().includes(query)
      )
  })
  const pageRows = computed(() =>
    clientPage(filtered.value, {
      sortBy: sortBy.value.length ? sortBy.value : [{ key: 'updated_at', order: 'desc' }],
      page: currentPage.value,
      itemsPerPage: itemsPerPage.value
    })
  )

  // The URL page resets on search and scope changes; the local toggle resets it here
  watch(mineOnly, () => (currentPage.value = 1))

  // "Assigned to me": ids of my pending review assignments, read on first use
  watch(mineOnly, async on => {
    if (!on || mineIds.value) return
    try {
      mineIds.value = await reviewStore.fetchMyPending()
    } catch {
      mineOnly.value = false
      notificationStore.addToast('Could not load your assigned reviews', 'error')
    }
  })

  // Methods
  // The API returns the scope's machine name; show the display name when the user's scopes load
  async function loadScopeNames(): Promise<Map<string, string>> {
    try {
      if (!scopesStore.scopes.length) await scopesStore.fetchUserScopes()
    } catch {
      // fall back to the machine name
    }
    return new Map(scopesStore.scopes.map(sc => [sc.id, sc.display_name || sc.name]))
  }

  async function fetchPendingReviews() {
    loading.value = true
    try {
      const scopeNames = await loadScopeNames()
      // The server decides what needs my review (reviewer/admin scopes, not my own, 4-eyes);
      // walk every page so the queue is never silently capped
      const inReview: Schema<'CurationSummary'>[] = []
      const pageSize = 200
      for (;;) {
        const response = await curationsAPI.getCurations({
          curation_status: 'in_review',
          pending_review: true,
          skip: inReview.length,
          limit: pageSize
        })
        const rows = response.curations || []
        inReview.push(...rows)
        if (rows.length === 0 || inReview.length >= (response.total ?? 0)) break
      }

      curations.value = inReview.map((c: Schema<'CurationSummary'>): ReviewItem => ({
        id: c.id,
        gene_id: c.gene_id,
        gene_symbol: c.gene_symbol,
        disease_name: c.disease_name,
        scope_id: c.scope_id,
        scope_name: scopeNames.get(c.scope_id ?? '') ?? c.scope_name,
        curator_name: c.curator_name,
        status: c.status,
        workflow_stage: c.workflow_stage,
        total_score: Number(c.computed_scores?.total_score) || 0,
        classification: c.computed_verdict,
        updated_at: c.updated_at,
        created_at: c.created_at,
        created_by: c.created_by
      }))

      // Submitted precurations are reviewed here too (they gate curation, #231)
      // Walk every page so the queue is never silently capped
      const submitted: Schema<'PrecurationSummary'>[] = []
      let pages = 1
      for (let page = 1; page <= pages; page++) {
        precurationStore.pagination.page = page
        await precurationStore.fetchPrecurations({ status: 'submitted', pending_review: true })
        submitted.push(...precurationStore.precurations)
        pages = precurationStore.pagination.pages
      }
      precurationStore.pagination.page = 1
      curations.value.push(
        ...submitted
          .filter(p => p.status === 'submitted')
          .map((p): ReviewItem => ({
            kind: 'precuration',
            id: p.id,
            gene_id: p.gene_id,
            gene_symbol: p.gene_symbol,
            disease_name: p.disease_name,
            scope_id: p.scope_id,
            scope_name: scopeNames.get(p.scope_id) ?? p.scope_name,
            curator_name: p.curator_name,
            status: p.status,
            total_score: 0,
            updated_at: p.updated_at,
            created_at: p.created_at
          }))
      )

      // Extract unique scopes for filter
      const scopeMap = new Map<string, { id: string; name: string }>()
      curations.value.forEach(c => {
        if (c.scope_id && c.scope_name) {
          scopeMap.set(c.scope_id, { id: c.scope_id, name: c.scope_name })
        }
      })
      scopes.value = Array.from(scopeMap.values())

      logger.debug('Pending reviews loaded', { count: curations.value.length })
    } catch (error) {
      logger.error('Failed to fetch pending reviews', { error: (error as Error).message })
      notificationStore.addToast('Failed to load review queue', 'error')
    } finally {
      loading.value = false
    }
  }

  async function approve(item: ReviewItem) {
    const ok = await confirm({
      title: 'Approve precuration?',
      text: `Approve the precuration for ${item.gene_symbol}? This lets curation start.`,
      confirmText: 'Approve'
    })
    if (!ok) return
    busyId.value = item.id
    try {
      await precurationStore.approvePrecuration(item.id)
      removeItem(item.id)
      notificationStore.addToast(`Precuration for ${item.gene_symbol} approved`, 'success')
    } catch (error) {
      notificationStore.addToast(`Failed to approve: ${errorText(error)}`, 'error')
    } finally {
      busyId.value = null
    }
  }

  function openReject(item: ReviewItem) {
    rejectTarget.value = item
    rejectReason.value = ''
    rejectError.value = null
    showReject.value = true
  }

  async function confirmReject() {
    const item = rejectTarget.value
    if (!item) return
    try {
      await precurationStore.rejectPrecuration(item.id, rejectReason.value.trim())
      removeItem(item.id)
      showReject.value = false
      notificationStore.addToast('Changes requested', 'success')
    } catch (error) {
      rejectError.value = errorText(error)
    }
  }

  function removeItem(id: string) {
    curations.value = curations.value.filter(c => c.id !== id)
    workCounts.fetch()
  }

  const errorText = (error: unknown): string => readableApiError(error, 'unknown error')

  function clearFilters() {
    filters.value = {}
    searchQuery.value = ''
    mineOnly.value = false
  }

  // Lifecycle
  onMounted(() => {
    fetchPendingReviews()
  })
</script>

<style scoped>
  .page-title,
  [data-testid='review-row'] {
    overflow-wrap: anywhere;
  }

  .v-card:hover {
    border-color: rgb(var(--v-theme-primary));
  }
</style>
