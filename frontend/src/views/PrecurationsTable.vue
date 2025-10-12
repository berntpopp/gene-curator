<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <div class="d-flex justify-space-between align-center mb-6">
          <div>
            <h1 class="text-h4 mb-2">Pre-curations</h1>
            <p class="text-subtitle-1 text-medium-emphasis">
              Manage gene-disease entity pre-curation workflow
            </p>
          </div>
          <v-btn color="primary" :to="{ name: 'CreatePrecuration' }" prepend-icon="mdi-plus">
            Create Pre-curation
          </v-btn>
        </div>

        <!-- Search and Filters -->
        <v-card class="mb-6">
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="searchQuery"
                  label="Search"
                  placeholder="Search gene symbols, MONDO IDs, or rationale..."
                  variant="outlined"
                  density="compact"
                  prepend-inner-icon="mdi-magnify"
                  clearable
                  @input="debouncedSearch"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="statusFilter"
                  :items="statusOptions"
                  label="Status"
                  variant="outlined"
                  density="compact"
                  clearable
                  @update:model-value="applyFilters"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="decisionFilter"
                  :items="decisionOptions"
                  label="Decision"
                  variant="outlined"
                  density="compact"
                  clearable
                  @update:model-value="applyFilters"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="sortBy"
                  :items="sortOptions"
                  label="Sort by"
                  variant="outlined"
                  density="compact"
                  @update:model-value="applySorting"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="sortOrder"
                  :items="[
                    { title: 'Newest first', value: 'desc' },
                    { title: 'Oldest first', value: 'asc' }
                  ]"
                  label="Order"
                  variant="outlined"
                  density="compact"
                  @update:model-value="applySorting"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Statistics Cards -->
        <v-row v-if="statistics" class="mb-6">
          <v-col v-for="stat in statisticsCards" :key="stat.title" cols="12" sm="6" md="3">
            <v-card>
              <v-card-text class="text-center">
                <v-icon :color="stat.color" size="40" class="mb-2">{{ stat.icon }}</v-icon>
                <div class="text-h5 font-weight-bold">{{ stat.value }}</div>
                <div class="text-body-2 text-medium-emphasis">{{ stat.title }}</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Data Table -->
        <v-card>
          <v-data-table-server
            v-model:items-per-page="itemsPerPage"
            v-model:page="page"
            :headers="headers"
            :items="precurationsStore.filteredPrecurations"
            :items-length="precurationsStore.totalPrecurations"
            :loading="precurationsStore.loading"
            :search="searchQuery"
            class="elevation-1"
            @update:options="handleTableUpdate"
          >
            <!-- Gene Symbol Column -->
            <template #item.gene_symbol="{ item }">
              <div class="d-flex align-center">
                <v-chip
                  :to="{ name: 'GeneDetail', params: { id: item.gene_id } }"
                  color="primary"
                  variant="outlined"
                  size="small"
                  clickable
                >
                  {{ item.gene?.approved_symbol || 'Unknown' }}
                </v-chip>
                <v-tooltip activator="parent" location="top">
                  {{ item.gene?.hgnc_id || 'No HGNC ID' }}
                </v-tooltip>
              </div>
            </template>

            <!-- MONDO ID Column -->
            <template #item.mondo_id="{ item }">
              <v-chip
                :href="`https://monarchinitiative.org/disease/${item.mondo_id}`"
                target="_blank"
                color="info"
                variant="outlined"
                size="small"
                clickable
              >
                {{ item.mondo_id }}
                <v-icon end size="small">mdi-open-in-new</v-icon>
              </v-chip>
            </template>

            <!-- Inheritance Column -->
            <template #item.mode_of_inheritance="{ item }">
              <v-chip
                :color="getInheritanceColor(item.mode_of_inheritance)"
                size="small"
                variant="tonal"
              >
                {{ item.mode_of_inheritance }}
              </v-chip>
            </template>

            <!-- Decision Column -->
            <template #item.lumping_splitting_decision="{ item }">
              <v-chip
                :color="getDecisionColor(item.lumping_splitting_decision)"
                size="small"
                :variant="item.lumping_splitting_decision === 'Undecided' ? 'outlined' : 'tonal'"
              >
                {{ item.lumping_splitting_decision }}
              </v-chip>
            </template>

            <!-- Status Column -->
            <template #item.status="{ item }">
              <v-chip :color="getStatusColor(item.status)" size="small" variant="tonal">
                {{ item.status.replace('_', ' ') }}
              </v-chip>
            </template>

            <!-- Created At Column -->
            <template #item.created_at="{ item }">
              {{ formatDate(item.created_at) }}
            </template>

            <!-- Actions Column -->
            <template #item.actions="{ item }">
              <div class="d-flex gap-1">
                <v-btn
                  :to="{ name: 'PrecurationDetail', params: { id: item.id } }"
                  icon
                  size="small"
                  variant="text"
                  color="primary"
                >
                  <v-icon size="small">mdi-eye</v-icon>
                  <v-tooltip activator="parent" location="top">View Details</v-tooltip>
                </v-btn>

                <v-btn
                  v-if="canEdit(item)"
                  icon
                  size="small"
                  variant="text"
                  color="primary"
                  @click="editPrecuration(item)"
                >
                  <v-icon size="small">mdi-pencil</v-icon>
                  <v-tooltip activator="parent" location="top">Edit</v-tooltip>
                </v-btn>

                <v-btn
                  v-if="canCreateCuration(item)"
                  icon
                  size="small"
                  variant="text"
                  color="success"
                  @click="createCurationFromPrecuration(item)"
                >
                  <v-icon size="small">mdi-arrow-right-circle</v-icon>
                  <v-tooltip activator="parent" location="top">Create Curation</v-tooltip>
                </v-btn>

                <v-menu>
                  <template #activator="{ props }">
                    <v-btn v-bind="props" icon size="small" variant="text">
                      <v-icon size="small">mdi-dots-vertical</v-icon>
                    </v-btn>
                  </template>
                  <v-list density="compact">
                    <v-list-item v-if="canApprove(item)" @click="approveItem(item)">
                      <template #prepend>
                        <v-icon size="small">mdi-check</v-icon>
                      </template>
                      <v-list-item-title>Approve</v-list-item-title>
                    </v-list-item>
                    <v-list-item v-if="canSubmitForReview(item)" @click="submitForReview(item)">
                      <template #prepend>
                        <v-icon size="small">mdi-send</v-icon>
                      </template>
                      <v-list-item-title>Submit for Review</v-list-item-title>
                    </v-list-item>
                    <v-list-item
                      v-if="authStore.isAdmin"
                      class="text-error"
                      @click="deleteItem(item)"
                    >
                      <template #prepend>
                        <v-icon size="small">mdi-delete</v-icon>
                      </template>
                      <v-list-item-title>Delete</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </div>
            </template>

            <!-- No data -->
            <template #no-data>
              <div class="text-center py-8">
                <v-icon size="64" class="text-medium-emphasis mb-4">mdi-clipboard-text-off</v-icon>
                <h3 class="text-h6 mb-2">No pre-curations found</h3>
                <p class="text-body-2 text-medium-emphasis mb-4">
                  {{
                    searchQuery
                      ? 'Try adjusting your search criteria'
                      : 'Create your first pre-curation to get started'
                  }}
                </p>
                <v-btn
                  v-if="!searchQuery"
                  :to="{ name: 'CreatePrecuration' }"
                  color="primary"
                  prepend-icon="mdi-plus"
                >
                  Create Pre-curation
                </v-btn>
              </div>
            </template>
          </v-data-table-server>
        </v-card>
      </v-col>
    </v-row>

    <!-- Edit Dialog -->
    <v-dialog v-model="editDialog" max-width="800px" scrollable>
      <v-card>
        <v-card-title>
          <span class="text-h5">Edit Pre-curation</span>
        </v-card-title>
        <v-card-text>
          <PrecurationForm
            v-if="editingItem"
            :precuration="editingItem"
            @submit="updatePrecuration"
            @cancel="editDialog = false"
          />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="confirmDialog" max-width="400px">
      <v-card>
        <v-card-title>{{ confirmTitle }}</v-card-title>
        <v-card-text>{{ confirmMessage }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="confirmDialog = false">Cancel</v-btn>
          <v-btn
            :color="confirmAction.color"
            :loading="actionLoading"
            @click="executeConfirmedAction"
          >
            {{ confirmAction.text }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { usePrecurationsStore, useAuthStore } from '@/stores'
  import { showError, showSuccess } from '@/composables/useNotifications.js'
  import PrecurationForm from '@/components/clingen/PrecurationForm.vue'

  const router = useRouter()
  const precurationsStore = usePrecurationsStore()
  const authStore = useAuthStore()

  // Reactive state
  const searchQuery = ref('')
  const statusFilter = ref(null)
  const decisionFilter = ref(null)
  const sortBy = ref('created_at')
  const sortOrder = ref('desc')
  const page = ref(1)
  const itemsPerPage = ref(25)
  const statistics = ref(null)

  // Dialog state
  const editDialog = ref(false)
  const confirmDialog = ref(false)
  const editingItem = ref(null)
  const actionLoading = ref(false)
  const confirmTitle = ref('')
  const confirmMessage = ref('')
  const confirmAction = ref({ text: '', color: 'primary', callback: null })

  // Table headers
  const headers = [
    { title: 'Gene', key: 'gene_symbol', sortable: false },
    { title: 'MONDO ID', key: 'mondo_id', sortable: true },
    { title: 'Inheritance', key: 'mode_of_inheritance', sortable: true },
    { title: 'Decision', key: 'lumping_splitting_decision', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Created', key: 'created_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false, width: '120px' }
  ]

  // Filter options
  const statusOptions = [
    { title: 'Draft', value: 'Draft' },
    { title: 'In Primary Review', value: 'In_Primary_Review' },
    { title: 'In Secondary Review', value: 'In_Secondary_Review' },
    { title: 'Approved', value: 'Approved' },
    { title: 'Rejected', value: 'Rejected' }
  ]

  const decisionOptions = [
    { title: 'Lump', value: 'Lump' },
    { title: 'Split', value: 'Split' },
    { title: 'Undecided', value: 'Undecided' }
  ]

  const sortOptions = [
    { title: 'Created Date', value: 'created_at' },
    { title: 'Updated Date', value: 'updated_at' },
    { title: 'Gene Symbol', value: 'approved_symbol' },
    { title: 'MONDO ID', value: 'mondo_id' },
    { title: 'Status', value: 'status' }
  ]

  // Statistics cards
  const statisticsCards = computed(() => {
    if (!statistics.value) return []

    return [
      {
        title: 'Total Pre-curations',
        value: statistics.value.total_precurations || 0,
        icon: 'mdi-clipboard-text',
        color: 'primary'
      },
      {
        title: 'Pending Review',
        value: statistics.value.pending_review || 0,
        icon: 'mdi-clock-outline',
        color: 'warning'
      },
      {
        title: 'Recent Additions',
        value: statistics.value.recent_additions || 0,
        icon: 'mdi-plus-circle',
        color: 'success'
      },
      {
        title: 'Updated This Week',
        value: statistics.value.updated_last_week || 0,
        icon: 'mdi-update',
        color: 'info'
      }
    ]
  })

  // Utility functions
  const formatDate = dateString => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const getStatusColor = status => {
    const colors = {
      Draft: 'grey',
      In_Primary_Review: 'orange',
      In_Secondary_Review: 'warning',
      Approved: 'success',
      Rejected: 'error'
    }
    return colors[status] || 'grey'
  }

  const getDecisionColor = decision => {
    const colors = {
      Lump: 'info',
      Split: 'warning',
      Undecided: 'grey'
    }
    return colors[decision] || 'grey'
  }

  const getInheritanceColor = inheritance => {
    const colors = {
      'Autosomal Dominant': 'blue',
      'Autosomal Recessive': 'green',
      'X-linked': 'purple',
      Mitochondrial: 'orange'
    }
    return colors[inheritance] || 'grey'
  }

  // Permission checks
  const canEdit = item => {
    return authStore.isCurator && ['Draft', 'In_Primary_Review'].includes(item.status)
  }

  const canApprove = item => {
    return authStore.isAdmin && item.status === 'In_Primary_Review'
  }

  const canSubmitForReview = item => {
    return authStore.isCurator && item.status === 'Draft'
  }

  const canCreateCuration = item => {
    return authStore.isCurator && item.status === 'Approved'
  }

  // Actions
  const editPrecuration = item => {
    editingItem.value = { ...item }
    editDialog.value = true
  }

  const updatePrecuration = async updatedData => {
    try {
      actionLoading.value = true
      await precurationsStore.updatePrecuration(editingItem.value.id, updatedData)
      showSuccess('Pre-curation updated successfully')
      editDialog.value = false
      editingItem.value = null
    } catch (error) {
      showError('Failed to update pre-curation')
    } finally {
      actionLoading.value = false
    }
  }

  const approveItem = item => {
    confirmTitle.value = 'Approve Pre-curation'
    confirmMessage.value = `Are you sure you want to approve this pre-curation for ${item.gene?.approved_symbol}?`
    confirmAction.value = {
      text: 'Approve',
      color: 'success',
      callback: () => workflowAction(item, 'approve')
    }
    confirmDialog.value = true
  }

  const submitForReview = item => {
    confirmTitle.value = 'Submit for Review'
    confirmMessage.value = `Submit this pre-curation for ${item.gene?.approved_symbol} for review?`
    confirmAction.value = {
      text: 'Submit',
      color: 'primary',
      callback: () => workflowAction(item, 'submit_for_review')
    }
    confirmDialog.value = true
  }

  const deleteItem = item => {
    confirmTitle.value = 'Delete Pre-curation'
    confirmMessage.value =
      'Are you sure you want to delete this pre-curation? This action cannot be undone.'
    confirmAction.value = {
      text: 'Delete',
      color: 'error',
      callback: () => precurationsStore.deletePrecuration(item.id)
    }
    confirmDialog.value = true
  }

  const createCurationFromPrecuration = item => {
    router.push({
      name: 'CreateCuration',
      query: {
        precuration_id: item.id,
        gene_id: item.gene_id
      }
    })
  }

  const workflowAction = async (item, action) => {
    try {
      actionLoading.value = true
      await precurationsStore.workflowAction(item.id, { action })
      showSuccess(`Pre-curation ${action.replace('_', ' ')} successful`)
    } catch (error) {
      showError(`Failed to ${action.replace('_', ' ')} pre-curation`)
    } finally {
      actionLoading.value = false
    }
  }

  const executeConfirmedAction = async () => {
    try {
      actionLoading.value = true
      await confirmAction.value.callback()
      confirmDialog.value = false
    } catch (error) {
      showError('Action failed')
    } finally {
      actionLoading.value = false
    }
  }

  // Search and filtering
  let searchTimeout = null
  const debouncedSearch = () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
      applyFilters()
    }, 500)
  }

  const applyFilters = async () => {
    const searchParams = {
      query: searchQuery.value,
      status: statusFilter.value,
      lumping_splitting_decision: decisionFilter.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      skip: 0,
      limit: itemsPerPage.value
    }

    page.value = 1
    await precurationsStore.searchPrecurations(searchParams)
  }

  const applySorting = async () => {
    await precurationsStore.setSorting(sortBy.value, sortOrder.value)
  }

  const handleTableUpdate = async options => {
    itemsPerPage.value = options.itemsPerPage
    page.value = options.page

    if (precurationsStore.searchResults) {
      await applyFilters()
    } else {
      await precurationsStore.fetchPrecurations({
        page: options.page,
        per_page: options.itemsPerPage
      })
    }
  }

  // Lifecycle
  onMounted(async () => {
    try {
      await Promise.all([
        precurationsStore.fetchPrecurations(),
        precurationsStore.fetchStatistics()
      ])
      statistics.value = precurationsStore.statistics
    } catch (error) {
      showError('Failed to load pre-curations')
    }
  })
</script>

<style scoped>
  .gap-1 {
    gap: 4px;
  }
</style>
