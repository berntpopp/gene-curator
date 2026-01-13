<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Review Queue</h1>
        <p class="text-subtitle-1 text-medium-emphasis mt-1">Curations awaiting peer review</p>
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
        <v-btn variant="outlined" @click="clearFilters">Clear Filters</v-btn>
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
                  <span class="text-h6 font-weight-bold">{{ curation.gene_symbol }}</span>
                </div>
                <div v-if="curation.disease_name" class="text-body-2 text-medium-emphasis ml-7">
                  {{ curation.disease_name }}
                </div>
                <div class="text-caption text-medium-emphasis ml-7 mt-1">
                  <v-icon icon="mdi-folder-outline" size="small" class="mr-1" />
                  {{ curation.scope_name }}
                </div>
              </v-col>

              <!-- Curator & Status -->
              <v-col cols="12" md="3">
                <div class="d-flex align-center mb-2">
                  <v-icon icon="mdi-account" size="small" class="mr-2" />
                  <span class="text-body-2">{{ curation.curator_name || 'Unknown' }}</span>
                </div>
                <div class="d-flex align-center">
                  <v-chip color="warning" size="small" variant="flat">
                    <v-icon start size="small">mdi-clock-outline</v-icon>
                    Awaiting Review
                  </v-chip>
                </div>
              </v-col>

              <!-- Score Preview -->
              <v-col cols="12" md="2">
                <div class="text-center">
                  <div class="text-h4 font-weight-bold">
                    {{ curation.total_score || 0 }}
                  </div>
                  <div class="text-caption text-medium-emphasis">/ 18 points</div>
                  <v-chip
                    v-if="curation.classification"
                    :color="getClassificationColor(curation.classification)"
                    size="small"
                    class="mt-1"
                  >
                    {{ curation.classification }}
                  </v-chip>
                </div>
              </v-col>

              <!-- Submitted Time & Actions -->
              <v-col cols="12" md="3" class="text-right">
                <div class="text-caption text-medium-emphasis mb-2">
                  Submitted {{ formatRelativeTime(curation.updated_at) }}
                </div>
                <v-btn
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
  </v-container>
</template>

<script setup>
  /**
   * ReviewQueueView
   *
   * Shows curations pending peer review across all accessible scopes.
   * Allows reviewers to filter, search, and navigate to curations for approval.
   */

  import { ref, computed, onMounted, watch } from 'vue'
  import { curationsAPI } from '@/api'
  import { useAuthStore } from '@/stores/auth'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'

  const authStore = useAuthStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // State
  const loading = ref(true)
  const curations = ref([])
  const scopes = ref([])
  const selectedScope = ref(null)
  const searchQuery = ref('')
  const sortBy = ref('submitted_desc')
  const currentPage = ref(1)
  const itemsPerPage = 10

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

  const filteredCurations = computed(() => {
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
          return new Date(a.updated_at) - new Date(b.updated_at)
        case 'gene_asc':
          return (a.gene_symbol || '').localeCompare(b.gene_symbol || '')
        case 'score_desc':
          return (b.total_score || 0) - (a.total_score || 0)
        case 'submitted_desc':
        default:
          return new Date(b.updated_at) - new Date(a.updated_at)
      }
    })

    // Paginate
    const start = (currentPage.value - 1) * itemsPerPage
    return result.slice(start, start + itemsPerPage)
  })

  const totalPages = computed(() => {
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
  async function fetchPendingReviews() {
    loading.value = true
    try {
      // Fetch curations with submitted status (pending review)
      const response = await curationsAPI.getCurations({
        curation_status: 'submitted',
        limit: 200
      })

      curations.value = (response.curations || []).map(c => ({
        id: c.id,
        gene_id: c.gene_id,
        gene_symbol: c.gene_symbol,
        disease_name: c.disease_name,
        scope_id: c.scope_id,
        scope_name: c.scope_name,
        curator_name: c.curator_name,
        status: c.status,
        workflow_stage: c.workflow_stage,
        total_score: c.computed_scores?.total_score || 0,
        classification: c.computed_verdict,
        updated_at: c.updated_at,
        created_at: c.created_at
      }))

      // Filter out curations created by current user (can't review your own)
      const userId = authStore.user?.user_id
      curations.value = curations.value.filter(c => c.curator_id !== userId)

      // Extract unique scopes for filter
      const scopeMap = new Map()
      curations.value.forEach(c => {
        if (c.scope_id && c.scope_name) {
          scopeMap.set(c.scope_id, { id: c.scope_id, name: c.scope_name })
        }
      })
      scopes.value = Array.from(scopeMap.values())

      logger.debug('Pending reviews loaded', { count: curations.value.length })
    } catch (error) {
      logger.error('Failed to fetch pending reviews', { error: error.message })
      notificationStore.addToast('Failed to load review queue', 'error')
    } finally {
      loading.value = false
    }
  }

  function getClassificationColor(classification) {
    const colors = {
      Definitive: 'success',
      Strong: 'info',
      Moderate: 'warning',
      Limited: 'grey',
      'No Known Disease Relationship': 'error'
    }
    return colors[classification] || 'grey'
  }

  function formatRelativeTime(dateString) {
    if (!dateString) return 'unknown'

    const now = new Date()
    const date = new Date(dateString)
    const diffMs = now - date
    const diffMin = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMin / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 7) {
      return date.toLocaleDateString()
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
