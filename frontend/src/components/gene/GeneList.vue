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
      <template #item="{ item: slotItem }">
        <tr v-for="item in [toGene(slotItem)]" :key="item.assignment_id">
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
          <td>
            <v-chip v-if="item.curator_name" size="small" color="primary" variant="tonal">
              <v-icon start size="small">mdi-account</v-icon>
              {{ item.curator_name }}
            </v-chip>
            <v-chip v-else size="small" variant="outlined">Unassigned</v-chip>
          </td>
          <td>
            <v-chip :color="getPriorityColor(item.priority)" size="small" variant="tonal">
              <v-icon start size="small">{{ getPriorityIcon(item.priority) }}</v-icon>
              {{ getPriorityLabel(item.priority) }}
            </v-chip>
          </td>
          <td>
            <v-chip :color="getStatusColor(item.status)" size="small">
              {{ getStatusLabel(item.status) }}
            </v-chip>
          </td>
          <td>
            <!-- Active/Completed curation -->
            <v-chip v-if="isCurationActive(item)" size="small" color="success" variant="elevated">
              <v-icon start size="small">mdi-check-decagram</v-icon>
              Active
            </v-chip>
            <!-- Curation awaiting review -->
            <v-chip
              v-else-if="hasCuration(item) && getCuration(item)?.status === 'submitted'"
              size="small"
              color="info"
              variant="tonal"
            >
              <v-icon start size="small">mdi-eye-check</v-icon>
              Awaiting Review
            </v-chip>
            <!-- Curation in progress -->
            <v-chip
              v-else-if="hasCuration(item) && getCuration(item)?.status === 'draft'"
              size="small"
              color="warning"
              variant="tonal"
            >
              <v-icon start size="small">mdi-pencil</v-icon>
              Curation In Progress
            </v-chip>
            <!-- Ready for curation (precuration approved) -->
            <v-chip
              v-else-if="isPrecurationApproved(item)"
              size="small"
              color="success"
              variant="tonal"
            >
              <v-icon start size="small">mdi-check-circle</v-icon>
              Ready for Curation
            </v-chip>
            <!-- Precuration in progress -->
            <v-chip v-else-if="hasPrecuration(item)" size="small" color="warning" variant="tonal">
              <v-icon start size="small">mdi-clipboard-text</v-icon>
              {{ getPrecurationStatusLabel(item) }}
            </v-chip>
            <!-- No precuration -->
            <v-chip v-else size="small" variant="outlined" color="grey">
              <v-icon start size="small">mdi-clipboard-outline</v-icon>
              No Precuration
            </v-chip>
          </td>
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
            <GeneRowActions
              :gene="item"
              :workflow="workflow"
              :can-assign-genes="canAssignGenes"
              :can-remove-genes="canRemoveGenes"
              @start-precuration="startPrecuration"
              @complete-precuration="completePrecuration"
              @view-curation="viewCuration"
              @start-curation="startCuration"
              @reassign="reassignGene"
              @edit-assignment="editGeneAssignment"
              @remove="confirmRemoveGene"
            />
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
          <GeneCard
            :gene="gene"
            :workflow="workflow"
            @view="viewGene"
            @start-precuration="startPrecuration"
            @complete-precuration="completePrecuration"
            @start-curation="startCuration"
          />
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

    <!-- Reassign Gene Modal -->
    <ReassignGeneModal
      v-model="showReassignModal"
      :scope-id="scopeId"
      :gene="selectedGeneForReassign"
      @reassigned="handleGeneReassigned"
    />

    <!-- Edit Gene Assignment Modal -->
    <EditGeneAssignmentModal
      v-model="showEditModal"
      :scope-id="scopeId"
      :gene="selectedGeneForEdit"
      @updated="handleGeneEdited"
      @revalidated="handleGeneRevalidated"
    />

    <!-- Remove Gene Confirmation Dialog -->
    <RemoveGeneDialog
      v-model="showRemoveConfirm"
      :gene-symbol="selectedGeneForRemoval?.gene_symbol"
      :is-removing="isRemoving"
      @confirm="removeGeneFromScope"
      @cancel="cancelRemoveGene"
    />
  </div>
</template>

<script setup lang="ts">
  /**
   * GeneList Component
   *
   * Displays genes assigned to a scope with filtering, sorting, and actions.
   * Supports both table and card views for responsive design.
   *
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
  import { useScopesStore } from '@/stores/scopes'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import TableSkeleton from '@/components/skeletons/TableSkeleton.vue'
  import AddGeneModal from '@/components/gene/AddGeneModal.vue'
  import AssignCuratorModal from '@/components/gene/AssignCuratorModal.vue'
  import GeneDetailModal from '@/components/gene/GeneDetailModal.vue'
  import ReassignGeneModal from '@/components/gene/ReassignGeneModal.vue'
  import EditGeneAssignmentModal from '@/components/gene/EditGeneAssignmentModal.vue'
  import GeneCard from './GeneCard.vue'
  import GeneRowActions from './GeneRowActions.vue'
  import RemoveGeneDialog from './RemoveGeneDialog.vue'
  import { useGeneWorkflowStatus } from './useGeneWorkflowStatus'
  import { useScopeGenes } from './useScopeGenes'
  import {
    getPriorityColor,
    getPriorityIcon,
    getPriorityLabel,
    getProgressColor,
    getStatusColor,
    getStatusLabel
  } from './geneDisplay'
  import type { ApiErrorLike } from '@/components/forms/types'
  import type { GeneRow } from './types'

  const props = defineProps<{
    scopeId: string
  }>()

  const router = useRouter()
  const authStore = useAuthStore()
  const scopeStore = useScopesStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // Precuration/curation status per gene (maps and predicates)
  const workflow = useGeneWorkflowStatus(() => props.scopeId)
  const {
    genePrecurations,
    geneCurations,
    hasPrecuration,
    isPrecurationApproved,
    hasCuration,
    getCuration,
    isCurationActive,
    getPrecurationStatusLabel
  } = workflow

  const {
    loading,
    search,
    filterStatus,
    filterCurator,
    curatorOptions,
    filteredGenes,
    fetchGenes,
    clearFilters
  } = useScopeGenes(() => props.scopeId, workflow)
  const viewMode = ref('table')

  // Modal state
  const showAddModal = ref(false)
  const showAssignModal = ref(false)
  const showGeneDetailModal = ref(false)
  const showReassignModal = ref(false)
  const showRemoveConfirm = ref(false)
  const selectedGeneForDetail = ref<GeneRow | null>(null)
  const selectedGeneForReassign = ref<GeneRow | null>(null)
  const selectedGeneForRemoval = ref<GeneRow | null>(null)
  const selectedGeneForEdit = ref<GeneRow | null>(null)
  const preSelectedGeneIds = ref<string[]>([])
  const isRemoving = ref(false)
  const showEditModal = ref(false)

  /**
   * Open assign curator modal with optional pre-selected genes
   */
  function openAssignModal(geneIds: string[] = []) {
    preSelectedGeneIds.value = geneIds
    showAssignModal.value = true
  }

  // Table headers
  const tableHeaders = [
    { title: 'Gene Symbol', key: 'gene_symbol', sortable: true },
    { title: 'Curator', key: 'curator_name', sortable: true },
    { title: 'Priority', key: 'priority', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Workflow', key: 'workflow', sortable: false },
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

  // Permissions: curate rights come from the scope membership; only the application admin may
  // deactivate assignments (backend rule in gene_assignments.py)
  const { canCurate: canAssignGenes } = useScopePermissions(
    computed(() => scopeStore.currentUserRole)
  )
  const canRemoveGenes = computed(() => authStore.isAdmin)

  /** TableSkeleton passes its rows through an untyped item slot. */
  function toGene(value: unknown): GeneRow {
    return value as GeneRow
  }

  /**
   * View gene details in modal
   */
  function viewGene(gene: GeneRow) {
    selectedGeneForDetail.value = gene
    showGeneDetailModal.value = true
  }

  /**
   * Start precuration for gene
   */
  function startPrecuration(gene: GeneRow) {
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}/precuration/new`)
  }

  /**
   * Complete existing precuration (mark as ready for curation)
   */
  async function completePrecuration(gene: GeneRow) {
    const precuration = genePrecurations.value[gene.gene_id]
    if (!precuration?.id) {
      startPrecuration(gene)
      return
    }

    try {
      await precurationsAPI.completePrecuration(precuration.id)
      notificationStore.addToast('Precuration completed successfully', 'success')

      // Refresh precuration status to update UI
      await workflow.fetchPrecurationStatuses()

      logger.info('Precuration completed', {
        precuration_id: precuration.id,
        gene_id: gene.gene_id
      })
    } catch (error) {
      const message = (error as ApiErrorLike).message
      logger.error('Failed to complete precuration', { error: message })
      notificationStore.addToast(`Failed to complete precuration: ${message}`, 'error')
    }
  }

  /**
   * Start curation for gene (only if precuration approved)
   */
  function startCuration(gene: GeneRow) {
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
   * View existing curation for gene
   */
  function viewCuration(gene: GeneRow) {
    const curation = geneCurations.value[gene.gene_id]
    if (curation?.id) {
      router.push(`/scopes/${props.scopeId}/curations/${curation.id}`)
    }
  }

  /**
   * Reassign gene to another curator
   */
  function reassignGene(gene: GeneRow) {
    selectedGeneForReassign.value = gene
    showReassignModal.value = true
  }

  /**
   * Confirm removal of gene from scope
   */
  function confirmRemoveGene(gene: GeneRow) {
    selectedGeneForRemoval.value = gene
    showRemoveConfirm.value = true
  }

  /**
   * Cancel the remove gene confirmation dialog
   */
  function cancelRemoveGene() {
    showRemoveConfirm.value = false
    selectedGeneForRemoval.value = null
  }

  /**
   * Remove gene from scope
   */
  async function removeGeneFromScope() {
    if (!selectedGeneForRemoval.value?.assignment_id) return

    isRemoving.value = true
    try {
      await assignmentsAPI.removeAssignment(
        selectedGeneForRemoval.value.assignment_id,
        'Removed from scope via gene management'
      )

      logger.info('Gene removed from scope', {
        gene_id: selectedGeneForRemoval.value.gene_id,
        gene_symbol: selectedGeneForRemoval.value.gene_symbol,
        scope_id: props.scopeId
      })

      notificationStore.addToast(
        `${selectedGeneForRemoval.value.gene_symbol} removed from scope`,
        'success'
      )

      showRemoveConfirm.value = false
      selectedGeneForRemoval.value = null
      fetchGenes()
    } catch (error) {
      const apiError = error as ApiErrorLike
      logger.error('Failed to remove gene from scope', { error: apiError.message })
      notificationStore.addToast(
        `Failed to remove: ${(apiError.response as { data?: { detail?: string } } | undefined)?.data?.detail || apiError.message}`,
        'error'
      )
    } finally {
      isRemoving.value = false
    }
  }

  /**
   * Handle genes added to catalog
   */
  function handleGenesAdded() {
    fetchGenes()
    notificationStore.addToast(
      'Genes added to this scope. You can now assign them to curators.',
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

  /**
   * Handle gene reassigned
   */
  function handleGeneReassigned() {
    fetchGenes()
  }

  /**
   * Edit gene assignment (priority, due date, notes)
   */
  function editGeneAssignment(gene: GeneRow) {
    selectedGeneForEdit.value = gene
    showEditModal.value = true
  }

  /**
   * Handle gene assignment edited
   */
  function handleGeneEdited() {
    fetchGenes()
  }

  /**
   * Handle gene revalidated
   */
  function handleGeneRevalidated(result: { external_data?: unknown } | null | undefined) {
    logger.debug('Gene revalidated', { result })
    // Optionally refresh genes if data changed
    if (result?.external_data) {
      fetchGenes()
    }
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
