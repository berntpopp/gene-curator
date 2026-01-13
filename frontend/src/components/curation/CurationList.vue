<template>
  <div>
    <!-- Toolbar -->
    <v-toolbar flat color="transparent">
      <v-text-field
        v-model="search"
        prepend-inner-icon="mdi-magnify"
        label="Search curations"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="mr-4"
        style="max-width: 400px"
      />

      <v-select
        v-model="filterStatus"
        :items="statusOptions"
        label="Status"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="mr-4"
        style="max-width: 200px"
      />

      <v-select
        v-model="filterCurator"
        :items="curatorOptions"
        item-title="name"
        item-value="id"
        label="Curator"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="mr-4"
        style="max-width: 200px"
      />

      <v-spacer />

      <v-btn-toggle v-model="viewMode" mandatory density="compact" class="mr-2">
        <v-btn value="table" icon="mdi-table" aria-label="Table view" />
        <v-btn value="cards" icon="mdi-view-grid" aria-label="Card view" />
      </v-btn-toggle>

      <v-btn v-if="canCreateCuration" color="primary" :to="`/scopes/${scopeId}/genes`">
        <v-icon start>mdi-dna</v-icon>
        Start Curation
        <v-tooltip activator="parent" location="bottom">
          Go to Genes tab to start a new curation
        </v-tooltip>
      </v-btn>
    </v-toolbar>

    <!-- Table View -->
    <TableSkeleton
      v-if="viewMode === 'table'"
      :loading="loading"
      :items="filteredCurations"
      :headers="tableHeaders"
      :skeleton-count="10"
    >
      <template #item="{ item }">
        <tr>
          <td>
            <div class="d-flex align-center">
              <v-icon icon="mdi-dna" size="small" class="mr-2" />
              <router-link
                :to="`/scopes/${scopeId}/curations/${item.curation_id}`"
                class="text-decoration-none font-weight-medium"
              >
                {{ item.gene_symbol }}
              </router-link>
            </div>
          </td>
          <td>{{ item.disease_name || '—' }}</td>
          <td>
            <v-chip v-if="item.curator_name" size="small" color="primary" variant="tonal">
              <v-icon start size="small">mdi-account</v-icon>
              {{ item.curator_name }}
            </v-chip>
            <v-chip v-else size="small" variant="outlined">Unassigned</v-chip>
          </td>
          <td>
            <v-chip :color="getStatusColor(item.status)" size="small">
              {{ getStatusLabel(item.status) }}
            </v-chip>
          </td>
          <td>
            <v-chip
              v-if="item.classification"
              :color="getClassificationColor(item.classification)"
              size="small"
            >
              {{ item.classification }}
            </v-chip>
            <span v-else class="text-caption text-medium-emphasis">—</span>
          </td>
          <td>
            <div class="d-flex align-center">
              <span class="text-h6 font-weight-bold mr-1">{{ item.score || 0 }}</span>
              <span class="text-caption text-medium-emphasis">/ 18</span>
            </div>
          </td>
          <td>{{ formatDate(item.updated_at) }}</td>
          <td>
            <v-menu>
              <template #activator="{ props: menuProps }">
                <v-btn
                  v-bind="menuProps"
                  icon
                  variant="text"
                  size="small"
                  aria-label="Curation actions"
                >
                  <v-icon>mdi-dots-vertical</v-icon>
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item @click="viewCuration(item)">
                  <template #prepend>
                    <v-icon>mdi-eye</v-icon>
                  </template>
                  <v-list-item-title>View</v-list-item-title>
                </v-list-item>
                <v-list-item v-if="item.status === 'draft'" @click="editCuration(item)">
                  <template #prepend>
                    <v-icon>mdi-pencil</v-icon>
                  </template>
                  <v-list-item-title>Edit</v-list-item-title>
                </v-list-item>
                <v-divider />
                <v-list-item v-if="canDeleteCuration(item)" @click="deleteCuration(item)">
                  <template #prepend>
                    <v-icon color="error">mdi-delete</v-icon>
                  </template>
                  <v-list-item-title class="text-error">Delete</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </td>
        </tr>
      </template>
    </TableSkeleton>

    <!-- Card View -->
    <v-row v-else-if="viewMode === 'cards'">
      <template v-if="loading">
        <!-- Loading skeletons -->
        <v-col v-for="n in 6" :key="`skeleton-${n}`" cols="12" sm="6" md="4">
          <v-skeleton-loader type="card" />
        </v-col>
      </template>

      <template v-else>
        <!-- Curation cards -->
        <v-col
          v-for="curation in filteredCurations"
          :key="curation.curation_id"
          cols="12"
          sm="6"
          md="4"
        >
          <v-card hover>
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-dna" class="mr-2" />
              {{ curation.gene_symbol }}
              <v-spacer />
              <v-chip :color="getStatusColor(curation.status)" size="small">
                {{ getStatusLabel(curation.status) }}
              </v-chip>
            </v-card-title>

            <v-card-subtitle v-if="curation.disease_name">
              {{ curation.disease_name }}
            </v-card-subtitle>

            <v-card-text>
              <!-- Curator -->
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-account" size="small" class="mr-2" />
                <span class="text-caption">
                  {{ curation.curator_name || 'Unassigned' }}
                </span>
              </div>

              <!-- Classification -->
              <div v-if="curation.classification" class="d-flex align-center mb-2">
                <v-icon icon="mdi-medal" size="small" class="mr-2" />
                <v-chip :color="getClassificationColor(curation.classification)" size="small">
                  {{ curation.classification }}
                </v-chip>
              </div>

              <!-- Score -->
              <div class="mb-2">
                <div class="text-caption mb-1">ClinGen Score</div>
                <div class="d-flex align-center">
                  <span class="text-h4 font-weight-bold mr-2">{{ curation.score || 0 }}</span>
                  <span class="text-caption text-medium-emphasis">/ 18 points</span>
                </div>
                <v-progress-linear
                  :model-value="(curation.score / 18) * 100"
                  :color="getClassificationColor(curation.classification)"
                  height="8"
                  rounded
                  class="mt-2"
                />
              </div>

              <!-- Updated -->
              <div class="text-caption text-medium-emphasis">
                Updated {{ formatRelativeTime(curation.updated_at) }}
              </div>
            </v-card-text>

            <v-card-actions>
              <v-btn size="small" variant="text" @click="viewCuration(curation)">
                <v-icon start>mdi-eye</v-icon>
                View
              </v-btn>
              <v-spacer />
              <v-btn
                v-if="curation.status === 'draft'"
                size="small"
                color="primary"
                variant="tonal"
                @click="editCuration(curation)"
              >
                <v-icon start>mdi-pencil</v-icon>
                Edit
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </template>
    </v-row>

    <!-- Empty State -->
    <v-alert
      v-if="!loading && filteredCurations.length === 0"
      type="info"
      variant="tonal"
      border="start"
      class="mt-4"
    >
      <v-alert-title>
        <v-icon size="large" class="mr-2">mdi-inbox</v-icon>
        No curations {{ search || filterStatus || filterCurator ? 'match your filters' : 'yet' }}
      </v-alert-title>
      <div v-if="!search && !filterStatus && !filterCurator">
        Start by creating your first curation for this scope.
      </div>
      <div v-else>Try adjusting your search or filter criteria.</div>
      <template #append>
        <v-btn
          v-if="canCreateCuration && !search && !filterStatus"
          color="primary"
          :to="`/scopes/${scopeId}/genes`"
        >
          <v-icon start>mdi-dna</v-icon>
          Start Curation
        </v-btn>
        <v-btn v-else variant="outlined" @click="clearFilters">Clear Filters</v-btn>
      </template>
    </v-alert>
  </div>
</template>

<script setup>
  /**
   * CurationList Component
   *
   * Displays curations for a scope with filtering, sorting, and actions.
   * Supports both table and card views for responsive design.
   *
   * Features:
   * - Search by gene symbol/disease
   * - Filter by status and curator
   * - Table/card view toggle
   * - View/edit/delete curations
   * - ClinGen score display
   * - Classification badges
   *
   * @example
   * <CurationList :scope-id="scopeId" />
   */

  import { ref, computed, onMounted, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { storeToRefs } from 'pinia'
  import { useAuthStore } from '@/stores/auth'
  import { useCurationsStore } from '@/stores/curations'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import TableSkeleton from '@/components/skeletons/TableSkeleton.vue'

  const props = defineProps({
    scopeId: {
      type: String,
      required: true
    }
  })

  const router = useRouter()
  const authStore = useAuthStore()
  const curationsStore = useCurationsStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // Extract reactive state from store using storeToRefs
  const { curations, loading } = storeToRefs(curationsStore)

  // Local UI state (filters, view mode)
  const search = ref('')
  const filterStatus = ref(null)
  const filterCurator = ref(null)
  const viewMode = ref('table')
  const curators = ref([])

  // Table headers
  const tableHeaders = [
    { title: 'Gene', key: 'gene_symbol', sortable: true },
    { title: 'Disease', key: 'disease_name', sortable: true },
    { title: 'Curator', key: 'curator_name', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Classification', key: 'classification', sortable: true },
    { title: 'Score', key: 'score', sortable: true },
    { title: 'Updated', key: 'updated_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  // Status options
  const statusOptions = [
    { title: 'Draft', value: 'draft' },
    { title: 'Submitted', value: 'submitted' },
    { title: 'Under Review', value: 'under_review' },
    { title: 'Approved', value: 'approved' },
    { title: 'Active', value: 'active' }
  ]

  // Permissions
  const canCreateCuration = computed(() => {
    const userRole = authStore.user?.role
    return ['admin', 'scope_admin', 'curator'].includes(userRole)
  })

  function canDeleteCuration(curation) {
    const userRole = authStore.user?.role
    const userId = authStore.user?.user_id
    return (
      ['admin', 'scope_admin'].includes(userRole) ||
      (curation.curator_id === userId && curation.status === 'draft')
    )
  }

  // Curator options (for filter)
  const curatorOptions = computed(() => {
    return curators.value.map(c => ({
      id: c.user_id,
      name: c.user_name || c.user_email
    }))
  })

  // Transform store curations to component format
  const transformedCurations = computed(() => {
    return curations.value.map(curation => ({
      curation_id: curation.id || curation.curation_id,
      gene_id: curation.gene_id,
      gene_symbol: curation.gene_symbol || '—',
      disease_name: curation.disease_name,
      curator_id: curation.created_by || curation.curator_id,
      curator_name: curation.curator_name,
      status: curation.status,
      classification: curation.computed_verdict || curation.classification,
      score: curation.computed_scores?.total_score || curation.score || 0,
      updated_at: curation.updated_at,
      created_at: curation.created_at
    }))
  })

  // Filtered curations (applies local UI filters)
  const filteredCurations = computed(() => {
    let result = transformedCurations.value

    // Search filter
    if (search.value) {
      const searchLower = search.value.toLowerCase()
      result = result.filter(
        c =>
          c.gene_symbol?.toLowerCase().includes(searchLower) ||
          c.disease_name?.toLowerCase().includes(searchLower)
      )
    }

    // Status filter
    if (filterStatus.value) {
      result = result.filter(c => c.status === filterStatus.value)
    }

    // Curator filter
    if (filterCurator.value) {
      result = result.filter(c => c.curator_id === filterCurator.value)
    }

    return result
  })

  // Extract unique curators from curations for filter dropdown
  watch(
    transformedCurations,
    newCurations => {
      curators.value = Array.from(
        new Map(
          newCurations
            .filter(c => c.curator_id)
            .map(c => [c.curator_id, { user_id: c.curator_id, user_name: c.curator_name }])
        ).values()
      )
    },
    { immediate: true }
  )

  /**
   * Fetch curations for scope using the store
   */
  async function fetchCurations() {
    try {
      // Update store filters and fetch
      curationsStore.updateFilters({ scope_id: props.scopeId })
      await curationsStore.fetchCurations({ scope_id: props.scopeId })

      logger.debug('Curations loaded via store', {
        count: curations.value.length,
        scope_id: props.scopeId
      })
    } catch (error) {
      logger.error('Failed to fetch curations', { error: error.message })
      notificationStore.addToast('Failed to load curations', 'error')
    }
  }

  /**
   * Get status color
   */
  function getStatusColor(status) {
    const colors = {
      draft: 'grey',
      submitted: 'info',
      under_review: 'warning',
      approved: 'success',
      active: 'primary'
    }
    return colors[status] || 'grey'
  }

  /**
   * Get status label
   */
  function getStatusLabel(status) {
    const labels = {
      draft: 'Draft',
      submitted: 'Submitted',
      under_review: 'Under Review',
      approved: 'Approved',
      active: 'Active'
    }
    return labels[status] || status
  }

  /**
   * Get classification color
   */
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

  /**
   * Format date
   */
  function formatDate(dateString) {
    if (!dateString) return '—'
    return new Date(dateString).toLocaleDateString()
  }

  /**
   * Format relative time
   */
  function formatRelativeTime(dateString) {
    if (!dateString) return '—'

    const now = new Date()
    const date = new Date(dateString)
    const diffMs = now - date
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHours = Math.floor(diffMin / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 7) return formatDate(dateString)
    if (diffDays > 0) return `${diffDays}d ago`
    if (diffHours > 0) return `${diffHours}h ago`
    if (diffMin > 0) return `${diffMin}m ago`
    return 'just now'
  }

  /**
   * Clear all filters
   */
  function clearFilters() {
    search.value = ''
    filterStatus.value = null
    filterCurator.value = null
  }

  /**
   * View curation details
   */
  function viewCuration(curation) {
    router.push(`/scopes/${props.scopeId}/curations/${curation.curation_id}`)
  }

  /**
   * Edit curation
   */
  function editCuration(curation) {
    router.push(`/scopes/${props.scopeId}/curations/${curation.curation_id}/edit`)
  }

  /**
   * Delete curation using store action
   */
  async function deleteCuration(curation) {
    if (!confirm(`Delete curation for ${curation.gene_symbol}?`)) return

    try {
      await curationsStore.deleteCuration(curation.curation_id)
      notificationStore.addToast('Curation deleted successfully', 'success')
      // Store automatically updates the curations list
    } catch (error) {
      logger.error('Failed to delete curation', { error: error.message })
      notificationStore.addToast('Failed to delete curation', 'error')
    }
  }

  // Lifecycle
  onMounted(() => {
    fetchCurations()
  })
</script>

<style scoped>
  /* Table row hover */
  tr:hover {
    background-color: rgba(0, 0, 0, 0.02);
  }

  /* Card hover effect */
  .v-card:hover {
    transform: translateY(-2px);
    transition: transform 0.2s ease;
  }

  /* Link styling */
  a {
    color: rgb(var(--v-theme-primary));
  }

  a:hover {
    text-decoration: underline;
  }
</style>
