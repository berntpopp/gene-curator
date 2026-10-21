<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-headline-large font-weight-bold">Review Queue</h1>
        <p class="text-body-large text-medium-emphasis mt-1">Curations awaiting peer review</p>
      </div>
      <v-spacer />
      <v-chip color="warning" variant="flat" size="large" class="px-4">
        <v-icon start>mdi-clipboard-check-outline</v-icon>
        {{ pendingCount }} pending review{{ pendingCount !== 1 ? 's' : '' }}
      </v-chip>
    </div>

    <!-- Filters -->
    <v-card class="mb-4" variant="outlined">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="4">
            <v-select
              v-model="selectedScope"
              :items="scopeOptions"
              item-title="name"
              item-value="id"
              label="Filter by Scope"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              prepend-inner-icon="mdi-folder-outline"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="searchQuery"
              label="Search by gene or curator"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              prepend-inner-icon="mdi-magnify"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="sortBy"
              :items="sortOptions"
              item-title="label"
              item-value="value"
              label="Sort by"
              variant="outlined"
              density="compact"
              hide-details
              prepend-inner-icon="mdi-sort"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Loading State -->
    <template v-if="loading">
      <v-row>
        <v-col v-for="n in 3" :key="n" cols="12">
          <v-skeleton-loader type="card" height="160" />
        </v-col>
      </v-row>
    </template>

    <!-- Empty State -->
    <v-alert
      v-else-if="filteredCurations.length === 0"
      type="success"
      variant="tonal"
      border="start"
      class="mt-4"
    >
      <v-alert-title>
        <v-icon size="large" class="mr-2">mdi-check-circle</v-icon>
        {{ searchQuery || selectedScope ? 'No matching curations' : 'All caught up!' }}
      </v-alert-title>
      <div v-if="!searchQuery && !selectedScope">
        There are no curations waiting for your review at this time.
      </div>
      <div v-else>Try adjusting your filters to see more results.</div>
      <template v-if="searchQuery || selectedScope" #append>
        <v-btn variant="outlined" @click="clearFilters">Clear filters</v-btn>
      </template>
    </v-alert>

    <!-- Review Cards -->
    <v-row v-else>
      <v-col v-for="curation in filteredCurations" :key="curation.id" cols="12">
        <v-card variant="outlined" hover>
          <v-card-text>
            <v-row align="center">
              <!-- Gene & Disease Info -->
              <v-col cols="12" md="4">
                <div class="d-flex align-center mb-2">
                  <v-icon icon="mdi-dna" color="primary" class="mr-2" />
                  <span class="text-title-large font-weight-bold">{{ curation.gene_symbol }}</span>
                  <v-chip
                    v-if="curation.kind === 'precuration'"
                    size="x-small"
                    color="info"
                    variant="tonal"
                    class="ml-2"
                  >
                    Precuration
                  </v-chip>
                </div>
                <div
                  v-if="curation.disease_name"
                  class="text-body-medium text-medium-emphasis ml-7"
                >
                  {{ curation.disease_name }}
                </div>
                <div class="text-body-small text-medium-emphasis ml-7 mt-1">
                  <v-icon icon="mdi-folder-outline" size="small" class="mr-1" />
                  {{ curation.scope_name }}
                </div>
              </v-col>

              <!-- Curator & Status -->
              <v-col cols="12" md="3">
                <div class="d-flex align-center mb-2">
                  <v-icon icon="mdi-account" size="small" class="mr-2" />
                  <span class="text-body-medium">{{ curation.curator_name || 'Unknown' }}</span>
                </div>
                <div class="d-flex align-center">
                  <v-chip color="warning" size="small" variant="flat">
                    <v-icon start size="small">mdi-clock-outline</v-icon>
                    {{ curationStatusLabel(curation.status) }}
                  </v-chip>
                </div>
              </v-col>

              <!-- Score Preview -->
              <v-col cols="12" md="2">
                <div v-if="curation.kind !== 'precuration'" class="text-center">
                  <div class="text-headline-large font-weight-bold">
                    {{ curation.total_score || 0 }}
                  </div>
                  <div class="text-body-small text-medium-emphasis">/ 18 points</div>
                  <ClassificationMark
                    v-if="curation.classification"
                    :classification="curation.classification"
                    class="mt-1"
                  />
                </div>
              </v-col>

              <!-- Submitted Time & Actions -->
              <v-col cols="12" md="3" class="text-right">
                <div class="text-body-small text-medium-emphasis mb-2">
                  Submitted {{ formatRelativeTime(curation.updated_at) }}
                </div>
                <div v-if="curation.kind === 'precuration'" class="d-flex justify-end ga-2">
                  <v-btn
                    variant="text"
                    :to="`/scopes/${curation.scope_id}/precurations/${curation.id}`"
                    data-test="open-precuration"
                  >
                    Open
                  </v-btn>
                  <v-btn
                    variant="outlined"
                    color="warning"
                    data-test="reject-precuration"
                    @click="openReject(curation)"
                  >
                    Request changes
                  </v-btn>
                  <v-btn
                    color="success"
                    :loading="busyId === curation.id"
                    data-test="approve-precuration"
                    @click="approve(curation)"
                  >
                    Approve
                  </v-btn>
                </div>
                <v-btn
                  v-else
                  color="primary"
                  :to="`/scopes/${curation.scope_id}/curations/${curation.id}`"
                >
                  <v-icon start>mdi-eye</v-icon>
                  Review
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Pagination -->
    <v-pagination
      v-if="totalPages > 1"
      v-model="currentPage"
      :length="totalPages"
      :total-visible="5"
      class="mt-6"
    />

    <BaseDialog v-model="showReject" title="Request changes" size="md">
      <v-textarea v-model="rejectReason" label="Feedback for the curator" rows="3" />
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
  import { formatDate } from '@/utils/format'
  import { curationsAPI } from '@/api'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { curationStatusLabel } from '@/config/status'
  import { useLogger } from '@/composables/useLogger'
  import { useConfirm } from '@/composables/useConfirm'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useScopesStore } from '@/stores/scopes'
  import { useWorkflowStore } from '@/stores/workflow'
  import { usePrecurationsStore } from '@/stores/precurations'
  import type { Schema } from '@/types/api'

  interface ReviewItem {
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
  const workflowStore = useWorkflowStore()
  const { confirm } = useConfirm()

  // State
  const loading = ref(true)
  const curations = ref<ReviewItem[]>([])
  const scopes = ref<Array<{ id: string; name: string }>>([])
  const selectedScope = ref<string | null>(null)
  const searchQuery = ref('')
  const sortBy = ref('submitted_desc')
  const currentPage = ref(1)
  const itemsPerPage = 10
  const busyId = ref<string | null>(null)
  const showReject = ref(false)
  const rejectReason = ref('')
  const rejectError = ref<string | null>(null)
  const rejectTarget = ref<ReviewItem | null>(null)

  // Sort options
  const sortOptions = [
    { label: 'Newest first', value: 'submitted_desc' },
    { label: 'Oldest first', value: 'submitted_asc' },
    { label: 'Gene (A-Z)', value: 'gene_asc' },
    { label: 'Score (high-low)', value: 'score_desc' }
  ]

  // Computed
  const scopeOptions = computed(() => scopes.value)

  const pendingCount = computed(() => curations.value.length)

  const filteredCurations = computed<ReviewItem[]>(() => {
    let result = [...curations.value]

    // Filter by scope
    if (selectedScope.value) {
      result = result.filter(c => c.scope_id === selectedScope.value)
    }

    // Filter by search query
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(
        c =>
          c.gene_symbol?.toLowerCase().includes(query) ||
          c.curator_name?.toLowerCase().includes(query) ||
          c.disease_name?.toLowerCase().includes(query)
      )
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy.value) {
        case 'submitted_asc':
          return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
        case 'gene_asc':
          return (a.gene_symbol || '').localeCompare(b.gene_symbol || '')
        case 'score_desc':
          return (b.total_score || 0) - (a.total_score || 0)
        case 'submitted_desc':
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      }
    })

    // Paginate
    const start = (currentPage.value - 1) * itemsPerPage
    return result.slice(start, start + itemsPerPage)
  })

  const totalPages = computed<number>(() => {
    let result = [...curations.value]
    if (selectedScope.value) {
      result = result.filter(c => c.scope_id === selectedScope.value)
    }
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(
        c =>
          c.gene_symbol?.toLowerCase().includes(query) ||
          c.curator_name?.toLowerCase().includes(query)
      )
    }
    return Math.ceil(result.length / itemsPerPage)
  })

  // Watch for filter changes to reset pagination
  watch([selectedScope, searchQuery], () => {
    currentPage.value = 1
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
    workflowStore.fetchPendingReviewCount()
  }

  function errorText(error: unknown): string {
    const e = error as { response?: { data?: { detail?: string } }; message?: string }
    return e.response?.data?.detail || e.message || 'unknown error'
  }

  function formatRelativeTime(dateString: string | null | undefined): string {
    if (!dateString) return 'unknown'

    const now = new Date()
    const date = new Date(dateString)
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMin / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 7) {
      return formatDate(dateString)
    }
    if (diffDays > 0) return `${diffDays}d ago`
    if (diffHours > 0) return `${diffHours}h ago`
    if (diffMin > 0) return `${diffMin}m ago`
    return 'just now'
  }

  function clearFilters() {
    selectedScope.value = null
    searchQuery.value = ''
  }

  // Lifecycle
  onMounted(() => {
    fetchPendingReviews()
  })
</script>

<style scoped>
  .v-card:hover {
    border-color: rgb(var(--v-theme-primary));
  }
</style>
