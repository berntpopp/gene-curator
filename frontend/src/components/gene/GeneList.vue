<template>
  <div>
    <!-- Toolbar -->
    <v-toolbar flat color="transparent">
      <v-text-field
        v-model="search"
        prepend-inner-icon="mdi-magnify"
        label="Search genes"
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

      <v-btn v-if="canAssignGenes" color="secondary" variant="outlined" class="mr-2" @click="showAddDrawer = true">
        <v-icon start>mdi-dna</v-icon>
        Add Genes
      </v-btn>

      <v-btn v-if="canAssignGenes" color="primary" @click="showAssignDrawer = true">
        <v-icon start>mdi-account-arrow-right</v-icon>
        Assign to Curator
      </v-btn>
    </v-toolbar>

    <!-- Table View -->
    <TableSkeleton
      v-if="viewMode === 'table'"
      :loading="loading"
      :items="filteredGenes"
      :headers="tableHeaders"
      :skeleton-count="10"
    >
      <template #item="{ item }">
        <tr>
          <td>
            <div class="d-flex align-center">
              <v-icon icon="mdi-dna" size="small" class="mr-2" />
              <router-link
                :to="`/scopes/${scopeId}/genes/${item.gene_id}`"
                class="text-decoration-none font-weight-medium"
              >
                {{ item.gene_symbol }}
              </router-link>
            </div>
          </td>
          <td>{{ item.gene_name || '—' }}</td>
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
          <td>{{ formatDate(item.due_date) }}</td>
          <td>
            <v-progress-linear
              :model-value="item.progress || 0"
              :color="getProgressColor(item.progress)"
              height="8"
              rounded
            />
            <div class="text-caption text-center mt-1">{{ item.progress || 0 }}%</div>
          </td>
          <td>
            <v-menu>
              <template #activator="{ props: menuProps }">
                <v-btn
                  v-bind="menuProps"
                  icon
                  variant="text"
                  size="small"
                  aria-label="Gene actions"
                >
                  <v-icon>mdi-dots-vertical</v-icon>
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item @click="viewGene(item)">
                  <template #prepend>
                    <v-icon>mdi-eye</v-icon>
                  </template>
                  <v-list-item-title>View Details</v-list-item-title>
                </v-list-item>
                <v-list-item @click="startPrecuration(item)">
                  <template #prepend>
                    <v-icon>mdi-clipboard-text</v-icon>
                  </template>
                  <v-list-item-title>Start Precuration</v-list-item-title>
                </v-list-item>
                <v-list-item @click="startCuration(item)">
                  <template #prepend>
                    <v-icon>mdi-pencil</v-icon>
                  </template>
                  <v-list-item-title>Start Curation</v-list-item-title>
                </v-list-item>
                <v-divider />
                <v-list-item v-if="canAssignGenes" @click="reassignGene(item)">
                  <template #prepend>
                    <v-icon>mdi-account-switch</v-icon>
                  </template>
                  <v-list-item-title>Reassign</v-list-item-title>
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
        <!-- Gene cards -->
        <v-col v-for="gene in filteredGenes" :key="gene.assignment_id" cols="12" sm="6" md="4">
          <v-card hover>
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-dna" class="mr-2" />
              {{ gene.gene_symbol }}
              <v-spacer />
              <v-chip :color="getStatusColor(gene.status)" size="small">
                {{ getStatusLabel(gene.status) }}
              </v-chip>
            </v-card-title>

            <v-card-subtitle v-if="gene.gene_name">
              {{ gene.gene_name }}
            </v-card-subtitle>

            <v-card-text>
              <!-- Curator -->
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-account" size="small" class="mr-2" />
                <span class="text-caption">
                  {{ gene.curator_name || 'Unassigned' }}
                </span>
              </div>

              <!-- Due date -->
              <div v-if="gene.due_date" class="d-flex align-center mb-2">
                <v-icon icon="mdi-calendar" size="small" class="mr-2" />
                <span class="text-caption">Due: {{ formatDate(gene.due_date) }}</span>
              </div>

              <!-- Progress -->
              <div class="mb-2">
                <div class="text-caption mb-1">Progress</div>
                <v-progress-linear
                  :model-value="gene.progress || 0"
                  :color="getProgressColor(gene.progress)"
                  height="12"
                  rounded
                >
                  <strong>{{ gene.progress || 0 }}%</strong>
                </v-progress-linear>
              </div>
            </v-card-text>

            <v-card-actions>
              <v-btn size="small" variant="text" @click="viewGene(gene)">
                <v-icon start>mdi-eye</v-icon>
                View
              </v-btn>
              <v-spacer />
              <v-btn size="small" color="primary" variant="tonal" @click="startCuration(gene)">
                <v-icon start>mdi-pencil</v-icon>
                Curate
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </template>
    </v-row>

    <!-- Empty State -->
    <v-alert
      v-if="!loading && filteredGenes.length === 0"
      type="info"
      variant="tonal"
      border="start"
      class="mt-4"
    >
      <v-alert-title>
        <v-icon size="large" class="mr-2">mdi-inbox</v-icon>
        No genes {{ search || filterStatus || filterCurator ? 'match your filters' : 'assigned' }}
      </v-alert-title>
      <div v-if="!search && !filterStatus && !filterCurator">
        Start by assigning genes to curators in this scope.
      </div>
      <div v-else>Try adjusting your search or filter criteria.</div>
      <template #append>
        <v-btn
          v-if="canAssignGenes && !search && !filterStatus"
          color="primary"
          @click="showAssignDrawer = true"
        >
          <v-icon start>mdi-plus</v-icon>
          Assign Genes
        </v-btn>
        <v-btn v-else variant="outlined" @click="clearFilters">Clear Filters</v-btn>
      </template>
    </v-alert>

    <!-- Add Genes Drawer -->
    <AddGenesDrawer
      v-model="showAddDrawer"
      @added="handleGenesAdded"
    />

    <!-- Assign Genes Drawer -->
    <AssignGenesDrawer
      v-model="showAssignDrawer"
      :scope-id="scopeId"
      @assigned="handleGenesAssigned"
    />
  </div>
</template>

<script setup>
  /**
   * GeneList Component
   *
   * Displays genes assigned to a scope with filtering, sorting, and actions.
   * Supports both table and card views for responsive design.
   *
   * Features:
   * - Search by gene symbol/name
   * - Filter by status and curator
   * - Table/card view toggle
   * - Assign genes drawer
   * - Start precuration/curation
   * - Progress tracking
   *
   * @example
   * <GeneList :scope-id="scopeId" />
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { assignmentsAPI } from '@/api'
  import { useAuthStore } from '@/stores/auth'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import TableSkeleton from '@/components/skeletons/TableSkeleton.vue'
  import AddGenesDrawer from '@/components/drawers/AddGenesDrawer.vue'
  import AssignGenesDrawer from '@/components/drawers/AssignGenesDrawer.vue'

  const props = defineProps({
    scopeId: {
      type: String,
      required: true
    }
  })

  const router = useRouter()
  const authStore = useAuthStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // State
  const genes = ref([])
  const loading = ref(false)
  const search = ref('')
  const filterStatus = ref(null)
  const filterCurator = ref(null)
  const viewMode = ref('table')
  const showAddDrawer = ref(false)
  const showAssignDrawer = ref(false)
  const curators = ref([])

  // Table headers
  const tableHeaders = [
    { title: 'Gene Symbol', key: 'gene_symbol', sortable: true },
    { title: 'Gene Name', key: 'gene_name', sortable: true },
    { title: 'Curator', key: 'curator_name', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Due Date', key: 'due_date', sortable: true },
    { title: 'Progress', key: 'progress', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  // Status options
  const statusOptions = [
    { title: 'Assigned', value: 'assigned' },
    { title: 'In Progress', value: 'in_progress' },
    { title: 'Under Review', value: 'under_review' },
    { title: 'Completed', value: 'completed' }
  ]

  // Permissions
  const canAssignGenes = computed(() => {
    const userRole = authStore.user?.role
    return ['admin', 'scope_admin', 'curator'].includes(userRole)
  })

  // Curator options (for filter)
  const curatorOptions = computed(() => {
    return curators.value.map(c => ({
      id: c.user_id,
      name: c.user_name || c.user_email
    }))
  })

  // Filtered genes
  const filteredGenes = computed(() => {
    let result = genes.value

    // Search filter
    if (search.value) {
      const searchLower = search.value.toLowerCase()
      result = result.filter(
        g =>
          g.gene_symbol?.toLowerCase().includes(searchLower) ||
          g.gene_name?.toLowerCase().includes(searchLower)
      )
    }

    // Status filter
    if (filterStatus.value) {
      result = result.filter(g => g.status === filterStatus.value)
    }

    // Curator filter
    if (filterCurator.value) {
      result = result.filter(g => g.curator_id === filterCurator.value)
    }

    return result
  })

  /**
   * Fetch genes assigned to scope
   */
  async function fetchGenes() {
    loading.value = true
    try {
      const response = await assignmentsAPI.getAssignmentsByScope(props.scopeId)
      genes.value = response.map(assignment => ({
        assignment_id: assignment.assignment_id,
        gene_id: assignment.gene_id,
        gene_symbol: assignment.gene?.gene_symbol || assignment.gene_symbol,
        gene_name: assignment.gene?.gene_name || '',
        curator_id: assignment.curator_id,
        curator_name: assignment.curator?.full_name || assignment.curator?.email,
        status: assignment.status || 'assigned',
        due_date: assignment.due_date,
        progress: calculateProgress(assignment)
      }))

      // Extract unique curators for filter
      curators.value = Array.from(
        new Map(
          genes.value
            .filter(g => g.curator_id)
            .map(g => [g.curator_id, { user_id: g.curator_id, user_name: g.curator_name }])
        ).values()
      )

      logger.debug('Genes loaded', { count: genes.value.length, scope_id: props.scopeId })
    } catch (error) {
      logger.error('Failed to fetch genes', { error: error.message })
      notificationStore.addToast('Failed to load genes', 'error')
    } finally {
      loading.value = false
    }
  }

  /**
   * Calculate gene progress based on workflow stage
   */
  function calculateProgress(assignment) {
    const statusProgress = {
      assigned: 0,
      in_progress: 25,
      under_review: 75,
      completed: 100
    }
    return statusProgress[assignment.status] || 0
  }

  /**
   * Get status color
   */
  function getStatusColor(status) {
    const colors = {
      assigned: 'grey',
      in_progress: 'warning',
      under_review: 'info',
      completed: 'success'
    }
    return colors[status] || 'grey'
  }

  /**
   * Get status label
   */
  function getStatusLabel(status) {
    const labels = {
      assigned: 'Assigned',
      in_progress: 'In Progress',
      under_review: 'Under Review',
      completed: 'Completed'
    }
    return labels[status] || status
  }

  /**
   * Get progress color
   */
  function getProgressColor(progress) {
    if (progress >= 75) return 'success'
    if (progress >= 50) return 'info'
    if (progress >= 25) return 'warning'
    return 'grey'
  }

  /**
   * Format date
   */
  function formatDate(dateString) {
    if (!dateString) return '—'
    return new Date(dateString).toLocaleDateString()
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
   * View gene details
   */
  function viewGene(gene) {
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}`)
  }

  /**
   * Start precuration for gene
   */
  function startPrecuration(gene) {
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}/precuration/new`)
  }

  /**
   * Start curation for gene
   */
  function startCuration(gene) {
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}/curation/new`)
  }

  /**
   * Reassign gene
   */
  function reassignGene() {
    // Open assign drawer with this gene pre-selected
    // TODO: Pre-select this gene in the drawer
    showAssignDrawer.value = true
  }

  /**
   * Handle genes added to catalog
   */
  function handleGenesAdded() {
    fetchGenes()
    notificationStore.addToast('Genes added to catalog. You can now assign them to curators.', 'success')
  }

  /**
   * Handle genes assigned
   */
  function handleGenesAssigned() {
    fetchGenes()
    notificationStore.addToast('Genes assigned successfully', 'success')
  }

  // Lifecycle
  onMounted(() => {
    fetchGenes()
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
