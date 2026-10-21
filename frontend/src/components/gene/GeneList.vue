<template>
  <div>
    <v-alert v-if="noMethodology" type="warning" variant="tonal" class="mb-4">
      This scope has no methodology yet, so precuration and curation cannot be started.
      <template v-if="canManageScope">
        <v-btn variant="text" size="small" @click="router.push(`/scopes/${scopeId}/settings`)">
          Choose one in Settings
        </v-btn>
      </template>
      <template v-else>Ask a scope admin to choose one.</template>
    </v-alert>

    <ScopeStageStrip
      class="mb-3"
      :counts="stageCounts"
      :model-value="stageFilter"
      @update:model-value="setStage"
    />

    <GeneBulkBar
      v-if="canReassign"
      class="mb-3"
      :selected="selectedRows"
      @assign="openAssignModal(selectedRows.filter(r => !r.curator_id).map(r => r.gene_id))"
      @clear="selectedIds = []"
      @changed="onBulkChanged"
    />

    <DataTable
      v-model:search="table.search.value"
      v-model:filters="table.filters.value"
      v-model:page="table.page.value"
      v-model:items-per-page="table.itemsPerPage.value"
      v-model:sort-by="table.sortBy.value"
      v-model:density="table.density.value"
      :headers="tableHeaders"
      :items="pageRows"
      :items-length="filteredGenes.length"
      :loading="loading"
      :filter-defs="filterDefs"
    >
      <template #toolbar-actions>
        <v-btn
          v-if="canReassign && filteredGenes.length"
          size="small"
          variant="text"
          data-testid="select-all"
          @click="selectedIds = filteredGenes.map(g => g.gene_id)"
        >
          Select all {{ filteredGenes.length }}
        </v-btn>
        <v-btn
          v-if="canReassign"
          size="small"
          color="primary"
          variant="flat"
          data-testid="add-genes"
          @click="showAddModal = true"
        >
          Add genes
        </v-btn>
      </template>

      <template #item.select="{ item }">
        <v-checkbox-btn
          v-model="selectedIds"
          :value="item.gene_id"
          density="compact"
          :aria-label="`Select ${item.gene_symbol}`"
        />
      </template>
      <template #item.gene_symbol="{ item }">
        <a href="#" class="gene-link" @click.prevent="viewGene(item)">{{ item.gene_symbol }}</a>
        <div class="text-body-small text-medium-emphasis">{{ item.gene_hgnc_id }}</div>
      </template>
      <template #item.curator_name="{ item }">
        <span :class="{ 'text-medium-emphasis': !item.curator_name }">
          {{ item.curator_name || 'Unassigned' }}
        </span>
      </template>
      <template #item.stage="{ item }">
        <v-chip size="small" :color="stageColor(item.stage)" variant="tonal">
          {{ stageTitle(item.stage) }}
        </v-chip>
      </template>
      <template #item.priority="{ item }">{{ getPriorityLabel(item.priority) }}</template>
      <template #item.updated_at="{ item }">{{ formatDate(item.updated_at) }}</template>
      <template #item.actions="{ item }">
        <GeneRowActions
          :gene="item"
          :workflow="workflow"
          :can-assign-genes="canAssignGenes"
          :can-reassign="canReassign"
          :can-remove-genes="canRemoveGenes"
          :start-blocked-reason="startBlockedReason"
          @start-precuration="startPrecuration"
          @complete-precuration="completePrecuration"
          @view-curation="viewCuration"
          @start-curation="startCuration"
          @reassign="reassignGene"
          @edit-assignment="editGeneAssignment"
          @remove="confirmRemoveGene"
        />
      </template>
      <template #no-data>
        <div data-testid="table-empty" class="pa-6 text-center text-medium-emphasis">
          <template v-if="rows.length">
            No genes match the filters.
            <v-btn variant="text" size="small" @click="clearFilters">Clear filters</v-btn>
          </template>
          <template v-else>
            No genes in this scope yet.
            <v-btn
              v-if="canReassign"
              variant="text"
              size="small"
              color="primary"
              @click="showAddModal = true"
            >
              Add genes
            </v-btn>
          </template>
        </div>
      </template>
    </DataTable>

    <AddGeneModal v-model="showAddModal" :scope-id="scopeId" @added="handleGenesAdded" />

    <AssignCuratorModal
      v-model="showAssignModal"
      :scope-id="scopeId"
      :pre-selected-genes="preSelectedGeneIds"
      @assigned="handleGenesAssigned"
    />

    <GeneDetailModal
      v-model="showGeneDetailModal"
      :hgnc-id="selectedGeneForDetail?.gene_hgnc_id"
      :gene-symbol="selectedGeneForDetail?.gene_symbol"
      :gene-id="selectedGeneForDetail?.gene_id"
      :scope-context="detailContext"
    />

    <ReassignGeneModal
      v-model="showReassignModal"
      :scope-id="scopeId"
      :gene="selectedGeneForReassign"
      @reassigned="handleGeneReassigned"
    />

    <EditGeneAssignmentModal
      v-model="showEditModal"
      :scope-id="scopeId"
      :gene="selectedGeneForEdit"
      @updated="handleGeneEdited"
    />

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
   * GeneList: the genes of a scope on the shared DataTable (search, filters, sort and page in
   * the URL), with the stage strip as a filter and a bulk bar for the selected genes.
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { assignmentsAPI, precurationsAPI } from '@/api'
  import { useAuthStore } from '@/stores/auth'
  import { useScopesStore } from '@/stores/scopes'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import DataTable from '@/components/common/DataTable.vue'
  import ScopeStageStrip from '@/components/scope/ScopeStageStrip.vue'
  import GeneBulkBar from './GeneBulkBar.vue'
  import AddGeneModal from '@/components/gene/AddGeneModal.vue'
  import AssignCuratorModal from '@/components/gene/AssignCuratorModal.vue'
  import GeneDetailModal from '@/components/gene/GeneDetailModal.vue'
  import ReassignGeneModal from '@/components/gene/ReassignGeneModal.vue'
  import EditGeneAssignmentModal from '@/components/gene/EditGeneAssignmentModal.vue'
  import GeneRowActions from './GeneRowActions.vue'
  import RemoveGeneDialog from './RemoveGeneDialog.vue'
  import { useGeneWorkflowStatus } from './useGeneWorkflowStatus'
  import { useScopeGenes } from './useScopeGenes'
  import { getPriorityLabel } from './geneDisplay'
  import { GENE_STAGES, stageTitle, type GeneStage } from './geneStage'
  import { useTableUrlState } from '@/composables/useTableUrlState'
  import { formatDate } from '@/utils/format'
  import { priorityOptions } from '@/components/dynamic/assignmentDisplay'
  import type { ApiErrorLike } from '@/components/forms/types'
  import type { GeneRow } from './types'

  const props = defineProps<{
    scopeId: string
  }>()

  // Tell the dashboard that genes were added, assigned or removed so it can refresh its counts
  const emit = defineEmits<{ changed: [] }>()

  const router = useRouter()
  const authStore = useAuthStore()
  const scopeStore = useScopesStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // Precuration/curation status per gene (maps and predicates)
  const workflow = useGeneWorkflowStatus(() => props.scopeId)
  const { genePrecurations, geneCurations, isPrecurationApproved } = workflow

  const table = useTableUrlState({ filterKeys: ['stage', 'curator', 'priority'] })
  const { loading, rows, stageCounts, curatorOptions, filteredGenes, pageRows, fetchGenes } =
    useScopeGenes(() => props.scopeId, workflow, table)

  const filterDefs = computed(() => [
    {
      key: 'stage',
      label: 'Stage',
      options: GENE_STAGES.map(s => ({ value: s.value, title: s.title }))
    },
    { key: 'curator', label: 'Curator', options: curatorOptions.value },
    { key: 'priority', label: 'Priority', options: priorityOptions }
  ])
  const stageFilter = computed(() => table.filters.value.stage as string | undefined)
  const stageColor = (stage: GeneStage) => GENE_STAGES.find(s => s.value === stage)?.color
  const setStage = (stage?: GeneStage) =>
    (table.filters.value = {
      ...table.filters.value,
      ...(stage ? { stage } : { stage: undefined as never })
    })
  const clearFilters = () => {
    table.search.value = ''
    table.filters.value = {}
  }

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

  const tableHeaders = computed(() => [
    ...(canReassign.value ? [{ title: 'Select', key: 'select', sortable: false }] : []),
    { title: 'Gene', key: 'gene_symbol' },
    { title: 'Curator', key: 'curator_name' },
    { title: 'Stage', key: 'stage' },
    { title: 'Priority', key: 'priority' },
    { title: 'Updated', key: 'updated_at' },
    { title: 'Actions', key: 'actions', sortable: false }
  ])

  // Permissions: curate rights come from the scope membership; only the application admin may
  // deactivate assignments (backend rule in gene_assignments.py)
  const { canCurate: canAssignGenes } = useScopePermissions(
    computed(() => scopeStore.currentUserRole)
  )
  const canRemoveGenes = computed(() => authStore.isAdmin)
  const { canManageScope } = useScopePermissions(computed(() => scopeStore.currentUserRole))
  const canReassign = computed(() => canManageScope.value || authStore.isAdmin)

  // A scope without a workflow pair has no schemas, so precuration would be a dead end (#197)
  const noMethodology = computed(
    () => !!scopeStore.currentScope && !scopeStore.currentScope.default_workflow_pair_id
  )
  const startBlockedReason = computed(() =>
    noMethodology.value ? 'This scope has no methodology yet' : null
  )

  const selectedIds = ref<string[]>([])
  const selectedRows = computed(() => rows.value.filter(r => selectedIds.value.includes(r.gene_id)))
  const detailContext = computed(() => {
    const g = selectedGeneForDetail.value
    const row = g && rows.value.find(r => r.gene_id === g.gene_id)
    return row
      ? {
          curator: row.curator_name,
          stage: stageTitle(row.stage),
          curationLink: row.curation_id
            ? `/scopes/${props.scopeId}/curations/${row.curation_id}`
            : ''
        }
      : undefined
  })

  /** After a bulk run only the genes that failed stay selected. */
  function onBulkChanged(failedGeneIds: string[]) {
    refresh()
    selectedIds.value = failedGeneIds
  }

  /** Reload after a change and let the parent refresh its statistics. */
  function refresh() {
    selectedIds.value = []
    fetchGenes()
    emit('changed')
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
    if (startBlockedReason.value) return
    router.push(`/scopes/${props.scopeId}/genes/${gene.gene_id}/precuration/new`)
  }

  /**
   * Complete existing precuration (mark as ready for curation)
   */
  async function completePrecuration(gene: GeneRow) {
    if (startBlockedReason.value) return
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
    if (startBlockedReason.value) return
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
      refresh()
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
    refresh()
    notificationStore.addToast(
      'Genes added to this scope. You can now assign them to curators.',
      'success'
    )
  }

  /**
   * Handle genes assigned
   */
  function handleGenesAssigned() {
    refresh()
    notificationStore.addToast('Genes assigned successfully', 'success')
  }

  /**
   * Handle gene reassigned
   */
  function handleGeneReassigned() {
    refresh()
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
    refresh()
  }

  // Lifecycle
  onMounted(() => {
    fetchGenes()
  })
</script>

<style scoped>
  .gene-link {
    color: rgb(var(--v-theme-secondary));
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    text-decoration: none;
  }

  .gene-link:hover {
    text-decoration: underline;
  }
</style>
