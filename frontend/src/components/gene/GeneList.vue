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

      <v-btn
        v-if="canAssignGenes"
        color="secondary"
        variant="outlined"
        class="mr-2"
        @click="showAddModal = true"
      >
        <v-icon start>mdi-dna</v-icon>
        Add Genes
      </v-btn>

      <v-btn v-if="canAssignGenes" color="primary" @click="openAssignModal()">
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
              <a
                href="#"
                class="text-decoration-none font-weight-medium gene-link"
                @click.prevent="viewGene(item)"
              >
                {{ item.gene_symbol }}
              </a>
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
          <td>
            <v-chip v-if="isPrecurationApproved(item)" size="small" color="success" variant="tonal">
              <v-icon start size="small">mdi-check-circle</v-icon>
              Ready for Curation
            </v-chip>
            <v-chip v-else-if="hasPrecuration(item)" size="small" color="warning" variant="tonal">
              <v-icon start size="small">mdi-clipboard-text</v-icon>
              {{ getPrecurationStatusLabel(item) }}
            </v-chip>
            <v-chip v-else size="small" variant="outlined" color="grey">
              <v-icon start size="small">mdi-clipboard-outline</v-icon>
              No Precuration
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
                <v-list-item v-if="!hasPrecuration(item)" @click="startPrecuration(item)">
                  <template #prepend>
                    <v-icon>mdi-clipboard-text</v-icon>
                  </template>
                  <v-list-item-title>Start Precuration</v-list-item-title>
                </v-list-item>
                <v-list-item
                  v-else-if="hasPrecuration(item) && !isPrecurationApproved(item)"
                  @click="continuePrecuration(item)"
                >
                  <template #prepend>
                    <v-icon>mdi-clipboard-edit</v-icon>
                  </template>
                  <v-list-item-title>Continue Precuration</v-list-item-title>
                </v-list-item>
                <v-list-item v-if="isPrecurationApproved(item)" @click="startCuration(item)">
                  <template #prepend>
                    <v-icon>mdi-pencil</v-icon>
                  </template>
                  <v-list-item-title>Start Curation</v-list-item-title>
                </v-list-item>
                <v-list-item v-else disabled>
                  <template #prepend>
                    <v-icon>mdi-pencil</v-icon>
                  </template>
                  <v-list-item-title> Curation (requires approved precuration) </v-list-item-title>
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
              <a href="#" class="text-decoration-none gene-link" @click.prevent="viewGene(gene)">
                {{ gene.gene_symbol }}
              </a>
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
              <!-- Workflow-aware action button -->
              <v-btn
                v-if="!hasPrecuration(gene)"
                size="small"
                color="primary"
                variant="tonal"
                @click="startPrecuration(gene)"
              >
                <v-icon start>mdi-clipboard-text</v-icon>
                Start Precuration
              </v-btn>
              <v-btn
                v-else-if="hasPrecuration(gene) && !isPrecurationApproved(gene)"
                size="small"
                color="warning"
                variant="tonal"
                @click="continuePrecuration(gene)"
              >
                <v-icon start>mdi-clipboard-edit</v-icon>
                Continue Precuration
              </v-btn>
              <v-btn
                v-else-if="isPrecurationApproved(gene)"
                size="small"
                color="success"
                variant="tonal"
                @click="startCuration(gene)"
              >
                <v-icon start>mdi-pencil</v-icon>
                Start Curation
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
          @click="openAssignModal()"
        >
          <v-icon start>mdi-plus</v-icon>
          Assign Genes
        </v-btn>
        <v-btn v-else variant="outlined" @click="clearFilters">Clear Filters</v-btn>
      </template>
    </v-alert>

    <!-- Add Genes Modal (replaces drawer for better UX) -->
    <AddGeneModal v-model="showAddModal" :scope-id="scopeId" @added="handleGenesAdded" />

    <!-- Assign Curator Modal (replaces drawer for better UX) -->
    <AssignCuratorModal
      v-model="showAssignModal"
      :scope-id="scopeId"
      :pre-selected-genes="preSelectedGeneIds"
      @assigned="handleGenesAssigned"
    />

    <!-- Gene Detail Modal -->
    <GeneDetailModal
      v-model="showGeneDetailModal"
      :hgnc-id="selectedGeneForDetail?.gene_hgnc_id"
      :gene-symbol="selectedGeneForDetail?.gene_symbol"
      :gene-id="selectedGeneForDetail?.gene_id"
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
   * - Add genes modal with HGNC search and bulk upload
   * - Assign curator modal with multi-gene selection
   * - Start precuration/curation workflow
   * - Progress tracking
   *
   * @example
   * <GeneList :scope-id="scopeId" />
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { assignmentsAPI, precurationsAPI } from '@/api'
  import { useAuthStore } from '@/stores/auth'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import TableSkeleton from '@/components/skeletons/TableSkeleton.vue'
  import AddGeneModal from '@/components/gene/AddGeneModal.vue'
  import AssignCuratorModal from '@/components/gene/AssignCuratorModal.vue'
  import GeneDetailModal from '@/components/gene/GeneDetailModal.vue'

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
  const curators = ref([])
  const genePrecurations = ref({}) // Map of gene_id -> precuration status

  // Modal state
  const showAddModal = ref(false)
  const showAssignModal = ref(false)
  const showGeneDetailModal = ref(false)
  const selectedGeneForDetail = ref(null)
  const preSelectedGeneIds = ref([])

  /**
   * Open assign curator modal with optional pre-selected genes
   */
  function openAssignModal(geneIds = []) {
    preSelectedGeneIds.value = geneIds
    showAssignModal.value = true
  }

  // Table headers
  const tableHeaders = [
    { title: 'Gene Symbol', key: 'gene_symbol', sortable: true },
    { title: 'Gene Name', key: 'gene_name', sortable: true },
    { title: 'Curator', key: 'curator_name', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Workflow', key: 'workflow', sortable: false },
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
        assignment_id: assignment.id || assignment.assignment_id,
        gene_id: assignment.gene_id,
        gene_symbol: assignment.gene_symbol || assignment.gene?.gene_symbol || '',
        gene_name: assignment.gene_name || assignment.gene?.gene_name || '',
        gene_hgnc_id: assignment.gene_hgnc_id || assignment.gene?.hgnc_id || '',
        curator_id: assignment.assigned_curator_id || assignment.curator_id,
        curator_name:
          assignment.curator_name ||
          assignment.curator?.full_name ||
          assignment.curator?.email ||
          '',
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

      // Fetch precuration status for all genes in scope
      await fetchPrecurationStatuses()

      logger.debug('Genes loaded', { count: genes.value.length, scope_id: props.scopeId })
    } catch (error) {
      logger.error('Failed to fetch genes', { error: error.message })
      notificationStore.addToast('Failed to load genes', 'error')
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch precuration statuses for genes in this scope
   * Maps gene_id -> latest precuration status
   */
  async function fetchPrecurationStatuses() {
    try {
      const response = await precurationsAPI.getPrecurations({
        scope_id: props.scopeId,
        limit: 200 // Backend max limit is 200
      })

      // Build map of gene_id -> most recent precuration
      const precurationMap = {}
      for (const precuration of response.precurations || []) {
        const existing = precurationMap[precuration.gene_id]
        // Keep the most recent or highest-status precuration
        if (!existing || shouldReplacePrecuration(existing, precuration)) {
          precurationMap[precuration.gene_id] = {
            id: precuration.id,
            status: precuration.status,
            workflow_stage: precuration.workflow_stage,
            updated_at: precuration.updated_at
          }
        }
      }
      genePrecurations.value = precurationMap
      logger.debug('Precuration statuses loaded', { count: Object.keys(precurationMap).length })
    } catch (error) {
      logger.error('Failed to fetch precuration statuses', { error: error.message })
      // Don't fail the whole page if precurations fail to load
    }
  }

  /**
   * Determine if a new precuration should replace an existing one
   * Prioritizes approved > submitted > draft, then by date
   */
  function shouldReplacePrecuration(existing, newPrecuration) {
    const statusPriority = { approved: 3, submitted: 2, draft: 1, rejected: 0 }
    const existingPriority = statusPriority[existing.status] || 0
    const newPriority = statusPriority[newPrecuration.status] || 0

    if (newPriority > existingPriority) return true
    if (newPriority < existingPriority) return false

    // Same status - use most recent
    return new Date(newPrecuration.updated_at) > new Date(existing.updated_at)
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
   * View gene details in modal
   */
  function viewGene(gene) {
    selectedGeneForDetail.value = gene
    showGeneDetailModal.value = true
  }

  /**
   * Check if gene has a precuration
   */
  function hasPrecuration(gene) {
    return !!genePrecurations.value[gene.gene_id]
  }

  /**
   * Check if gene's precuration is approved
   */
  function isPrecurationApproved(gene) {
    const precuration = genePrecurations.value[gene.gene_id]
    return precuration?.status === 'approved'
  }

  /**
   * Get precuration status label for display
   */
  function getPrecurationStatusLabel(gene) {
    const precuration = genePrecurations.value[gene.gene_id]
    if (!precuration) return 'No Precuration'

    const statusLabels = {
      draft: 'Draft',
      submitted: 'Submitted',
      in_review: 'In Review',
      approved: 'Approved',
      rejected: 'Rejected'
    }
    return statusLabels[precuration.status] || precuration.status
  }

  /**
   * Start precuration for gene
   */
  function startPrecuration(gene) {
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}/precuration/new`)
  }

  /**
   * Continue existing precuration
   */
  function continuePrecuration(gene) {
    const precuration = genePrecurations.value[gene.gene_id]
    if (precuration?.id) {
      router.push(`/scopes/${props.scopeId}/precurations/${precuration.id}`)
    } else {
      startPrecuration(gene)
    }
  }

  /**
   * Start curation for gene (only if precuration approved)
   */
  function startCuration(gene) {
    if (!isPrecurationApproved(gene)) {
      notificationStore.addToast(
        'Complete and approve precuration before starting curation',
        'warning'
      )
      return
    }
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}/curation/new`)
  }

  /**
   * Reassign gene to another curator
   */
  function reassignGene(gene) {
    // Open assign modal with this gene pre-selected
    openAssignModal([gene.gene_id])
  }

  /**
   * Handle genes added to catalog
   */
  function handleGenesAdded() {
    fetchGenes()
    notificationStore.addToast(
      'Genes added to catalog. You can now assign them to curators.',
      'success'
    )
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

  /* Gene link in table */
  .gene-link {
    cursor: pointer;
  }
</style>
