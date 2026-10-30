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
        Start curation
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
      <template #item="slotProps">
        <tr v-for="item in [slotProps.item as CurationRow]" :key="item.curation_id">
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
            <v-chip :color="curationStatusColor(item.status)" size="small">
              {{ curationStatusLabel(item.status) }}
            </v-chip>
          </td>
          <td>
            <ClassificationMark v-if="item.classification" :classification="item.classification" />
            <span v-else class="text-body-small text-medium-emphasis">—</span>
          </td>
          <td>
            <div class="d-flex align-center">
              <span class="text-title-large font-weight-bold mr-1">{{ item.score || 0 }}</span>
              <span class="text-body-small text-medium-emphasis">/ 18</span>
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
                <v-list-item v-if="canEditCuration(item)" @click="editCuration(item)">
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
              <v-chip :color="curationStatusColor(curation.status)" size="small">
                {{ curationStatusLabel(curation.status) }}
              </v-chip>
            </v-card-title>

            <v-card-subtitle v-if="curation.disease_name">
              {{ curation.disease_name }}
            </v-card-subtitle>

            <v-card-text>
              <!-- Curator -->
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-account" size="small" class="mr-2" />
                <span class="text-body-small">
                  {{ curation.curator_name || 'Unassigned' }}
                </span>
              </div>

              <!-- Classification -->
              <div v-if="curation.classification" class="d-flex align-center mb-2">
                <v-icon icon="mdi-medal" size="small" class="mr-2" />
                <ClassificationMark :classification="curation.classification" />
              </div>

              <!-- Score -->
              <div class="mb-2">
                <div class="text-body-small mb-1">ClinGen Score</div>
                <div class="d-flex align-center">
                  <span class="text-headline-large font-weight-bold mr-2">{{
                    curation.score || 0
                  }}</span>
                  <span class="text-body-small text-medium-emphasis">/ 18 points</span>
                </div>
                <v-progress-linear
                  :model-value="(curation.score / 18) * 100"
                  :color="getClassification(curation.classification).color"
                  height="8"
                  rounded
                  class="mt-2"
                />
              </div>

              <!-- Updated -->
              <div class="text-body-small text-medium-emphasis">
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
                v-if="canEditCuration(curation)"
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
          Start curation
        </v-btn>
        <v-btn v-else variant="outlined" @click="clearFilters">Clear filters</v-btn>
      </template>
    </v-alert>
  </div>
</template>

<script setup lang="ts">
  import { formatDate } from '@/utils/format'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { compareClassifications, getClassification } from '@/config/classification'
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
  import { CURATION_STATUS, curationStatusColor, curationStatusLabel } from '@/config/status'
  import { useScopesStore } from '@/stores/scopes'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useCurationsStore } from '@/stores/curations'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import TableSkeleton from '@/components/skeletons/TableSkeleton.vue'
  import { useConfirm } from '@/composables/useConfirm'

  /** Row shape shared by the table and the card view (transformed from the store). */
  interface CurationRow {
    curation_id: string
    gene_id?: string
    gene_symbol: string
    disease_name?: string | null
    curator_id?: string | null
    curator_name?: string | null
    status: string
    classification?: string | null
    score: number
    updated_at?: string
    created_at?: string
  }

  interface CuratorOption {
    user_id: string
    user_name?: string | null
    user_email?: string | null
  }

  const props = defineProps<{
    scopeId: string
  }>()

  const router = useRouter()
  const authStore = useAuthStore()
  const scopeStore = useScopesStore()
  const curationsStore = useCurationsStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // Extract reactive state from store using storeToRefs
  const { curations, loading } = storeToRefs(curationsStore)

  // Local UI state (filters, view mode)
  const search = ref('')
  const filterStatus = ref<string | null>(null)
  const filterCurator = ref<string | null>(null)
  const viewMode = ref('table')
  const curators = ref<CuratorOption[]>([])

  // Table headers
  const tableHeaders = [
    { title: 'Gene', key: 'gene_symbol', sortable: true },
    { title: 'Disease', key: 'disease_name', sortable: true },
    { title: 'Curator', key: 'curator_name', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    {
      title: 'Classification',
      key: 'classification',
      sortable: true,
      sort: compareClassifications
    },
    { title: 'Score', key: 'score', sortable: true },
    { title: 'Updated', key: 'updated_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  // Status options
  const statusOptions = [
    { title: 'Draft', value: 'draft' },
    { title: 'Submitted', value: 'submitted' },
    { title: CURATION_STATUS.in_review.label, value: 'in_review' },
    { title: 'Approved', value: 'approved' },
    { title: 'Active', value: 'active' }
  ]

  // Permissions
  const { canCurate, canManageScope } = useScopePermissions(
    computed(() => scopeStore.currentUserRole)
  )
  // An inactive scope's curations are read-only for everyone (#483)
  const scopeActive = computed(() => scopeStore.currentScope?.is_active !== false)
  const canCreateCuration = computed(() => canCurate.value && scopeActive.value)

  function canEditCuration(curation: CurationRow) {
    return scopeActive.value && curation.status === 'draft'
  }

  function canDeleteCuration(curation: CurationRow) {
    return (
      scopeActive.value &&
      (canManageScope.value ||
        (curation.curator_id === authStore.user?.id && curation.status === 'draft'))
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
  const transformedCurations = computed<CurationRow[]>(() => {
    // The list endpoint returns CurationSummary rows
    return curations.value.map(curation => ({
      curation_id: curation.id,
      gene_id: curation.gene_id,
      gene_symbol: curation.gene_symbol || '—',
      disease_name: curation.disease_name,
      curator_id: curation.created_by,
      curator_name: curation.curator_name,
      status: curation.status,
      classification: curation.final_classification ?? curation.computed_verdict,
      score: Number(curation.computed_scores?.total_score) || 0,
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
            .map(c => [
              c.curator_id,
              { user_id: c.curator_id as string, user_name: c.curator_name }
            ])
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
      logger.error('Failed to fetch curations', { error: (error as Error).message })
      notificationStore.addToast('Failed to load curations', 'error')
    }
  }

  /**
   * Format date
   */
  /**
   * Format relative time
   */
  function formatRelativeTime(dateString: string | null | undefined): string {
    if (!dateString) return '—'

    const now = new Date()
    const date = new Date(dateString)
    const diffMs = now.getTime() - date.getTime()
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
  function viewCuration(curation: CurationRow) {
    router.push(`/scopes/${props.scopeId}/curations/${curation.curation_id}`)
  }

  /**
   * Edit curation
   */
  function editCuration(curation: CurationRow) {
    router.push(`/scopes/${props.scopeId}/curations/${curation.curation_id}/edit`)
  }

  const { confirm } = useConfirm()

  /**
   * Delete curation using store action
   */
  async function deleteCuration(curation: CurationRow) {
    if (
      !(await confirm({
        title: `Delete curation for ${curation.gene_symbol}?`,
        confirmText: 'Delete',
        destructive: true
      }))
    )
      return

    try {
      await curationsStore.deleteCuration(curation.curation_id)
      notificationStore.addToast('Curation deleted successfully', 'success')
      // Store automatically updates the curations list
    } catch (error) {
      logger.error('Failed to delete curation', { error: (error as Error).message })
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
    background-color: rgba(var(--v-theme-on-surface), 0.04);
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
