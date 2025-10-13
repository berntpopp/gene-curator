<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <div class="d-flex justify-space-between align-center mb-6">
          <div>
            <h1 class="text-h4 mb-2">ClinGen Curations</h1>
            <p class="text-subtitle-1 text-medium-emphasis">
              Gene-disease validity curations with SOP v11 compliance
            </p>
          </div>
          <v-btn color="primary" :to="{ name: 'CreateCuration' }" prepend-icon="mdi-plus">
            Create Curation
          </v-btn>
        </div>

        <!-- Search and Filters -->
        <v-card class="mb-6">
          <v-card-text>
            <v-row>
              <v-col cols="12" md="3">
                <v-text-field
                  v-model="searchQuery"
                  label="Search"
                  placeholder="Search gene symbols, disease names, GCEP..."
                  variant="outlined"
                  density="compact"
                  prepend-inner-icon="mdi-magnify"
                  clearable
                  @input="debouncedSearch"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="verdictFilter"
                  :items="verdictOptions"
                  label="Verdict"
                  variant="outlined"
                  density="compact"
                  clearable
                  @update:model-value="applyFilters"
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
                <v-range-slider
                  v-model="scoreRange"
                  label="Score Range"
                  :min="0"
                  :max="18"
                  :step="0.5"
                  thumb-label
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
              <v-col cols="12" md="1">
                <v-select
                  v-model="sortOrder"
                  :items="[
                    { title: 'Desc', value: 'desc' },
                    { title: 'Asc', value: 'asc' }
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
          <v-col v-for="stat in statisticsCards" :key="stat.title" cols="12" sm="6" md="2">
            <v-card>
              <v-card-text class="text-center">
                <v-icon :color="stat.color" size="32" class="mb-2">{{ stat.icon }}</v-icon>
                <div class="text-h6 font-weight-bold">{{ stat.value }}</div>
                <div class="text-caption text-medium-emphasis">{{ stat.title }}</div>
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
            :items="curationsStore.filteredCurations"
            :items-length="curationsStore.totalCurations"
            :loading="curationsStore.loading"
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

            <!-- Disease Name Column -->
            <template #item.disease_name="{ item }">
              <div class="disease-name">
                <div class="text-body-2 font-weight-medium">{{ item.disease_name }}</div>
                <div class="text-caption text-medium-emphasis">{{ item.mondo_id }}</div>
              </div>
            </template>

            <!-- Verdict Column -->
            <template #item.verdict="{ item }">
              <v-chip :color="getVerdictColor(item.verdict)" size="small" variant="tonal">
                <v-icon start size="small">{{ getVerdictIcon(item.verdict) }}</v-icon>
                {{ item.verdict }}
              </v-chip>
            </template>

            <!-- Score Column -->
            <template #item.total_score="{ item }">
              <div class="score-display">
                <div class="text-body-1 font-weight-bold">{{ item.total_score.toFixed(1) }}/18</div>
                <div class="text-caption text-medium-emphasis">
                  G: {{ item.genetic_evidence_score.toFixed(1) }} | E:
                  {{ item.experimental_evidence_score.toFixed(1) }}
                </div>
                <v-tooltip activator="parent" location="top">
                  Genetic: {{ item.genetic_evidence_score }}/12 | Experimental:
                  {{ item.experimental_evidence_score }}/6
                </v-tooltip>
              </div>
            </template>

            <!-- Contradictory Evidence Column -->
            <template #item.has_contradictory_evidence="{ item }">
              <v-icon v-if="item.has_contradictory_evidence" color="warning" size="small">
                mdi-alert-triangle
              </v-icon>
              <v-tooltip v-if="item.has_contradictory_evidence" activator="parent" location="top">
                Contains contradictory evidence
              </v-tooltip>
            </template>

            <!-- GCEP Column -->
            <template #item.gcep_affiliation="{ item }">
              <v-chip size="small" variant="outlined" color="info">
                {{ item.gcep_affiliation }}
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
                  :to="{ name: 'CurationDetail', params: { id: item.id } }"
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
                  @click="editCuration(item)"
                >
                  <v-icon size="small">mdi-pencil</v-icon>
                  <v-tooltip activator="parent" location="top">Edit</v-tooltip>
                </v-btn>

                <v-btn
                  icon
                  size="small"
                  variant="text"
                  color="info"
                  @click="viewScoreBreakdown(item)"
                >
                  <v-icon size="small">mdi-chart-line</v-icon>
                  <v-tooltip activator="parent" location="top">Score Breakdown</v-tooltip>
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
                    <v-list-item v-if="canPublish(item)" @click="publishItem(item)">
                      <template #prepend>
                        <v-icon size="small">mdi-publish</v-icon>
                      </template>
                      <v-list-item-title>Publish</v-list-item-title>
                    </v-list-item>
                    <v-list-item v-if="canSubmitForReview(item)" @click="submitForReview(item)">
                      <template #prepend>
                        <v-icon size="small">mdi-send</v-icon>
                      </template>
                      <v-list-item-title>Submit for Review</v-list-item-title>
                    </v-list-item>
                    <v-list-item @click="exportCuration(item)">
                      <template #prepend>
                        <v-icon size="small">mdi-download</v-icon>
                      </template>
                      <v-list-item-title>Export</v-list-item-title>
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
                <v-icon size="64" class="text-medium-emphasis mb-4"
                  >mdi-clipboard-check-multiple-outline</v-icon
                >
                <h3 class="text-h6 mb-2">No curations found</h3>
                <p class="text-body-2 text-medium-emphasis mb-4">
                  {{
                    searchQuery
                      ? 'Try adjusting your search criteria'
                      : 'Create your first curation to get started'
                  }}
                </p>
                <v-btn
                  v-if="!searchQuery"
                  :to="{ name: 'CreateCuration' }"
                  color="primary"
                  prepend-icon="mdi-plus"
                >
                  Create Curation
                </v-btn>
              </div>
            </template>
          </v-data-table-server>
        </v-card>
      </v-col>
    </v-row>

    <!-- Score Breakdown Dialog -->
    <v-dialog v-model="scoreDialog" max-width="600px">
      <v-card v-if="selectedCurationScore">
        <v-card-title>
          <span class="text-h5">ClinGen Score Breakdown</span>
        </v-card-title>
        <v-card-text>
          <ClinGenScoreCard :score="selectedCurationScore" :show-actions="false" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="scoreDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Edit Dialog -->
    <v-dialog v-model="editDialog" max-width="1200px" scrollable>
      <v-card>
        <v-card-title>
          <span class="text-h5">Edit Curation</span>
        </v-card-title>
        <v-card-text>
          <CurationForm
            v-if="editingItem"
            :curation="editingItem"
            @submit="updateCuration"
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
  import { useCurationsStore, useAuthStore } from '@/stores'
  import { showError, showSuccess } from '@/composables/useNotifications.js'
  import ClinGenScoreCard from '@/components/clingen/ClinGenScoreCard.vue'
  import CurationForm from '@/components/clingen/CurationForm.vue'

  const curationsStore = useCurationsStore()
  const authStore = useAuthStore()

  // Reactive state
  const searchQuery = ref('')
  const verdictFilter = ref(null)
  const statusFilter = ref(null)
  const scoreRange = ref([0, 18])
  const sortBy = ref('created_at')
  const sortOrder = ref('desc')
  const page = ref(1)
  const itemsPerPage = ref(25)
  const statistics = ref(null)

  // Dialog state
  const editDialog = ref(false)
  const scoreDialog = ref(false)
  const confirmDialog = ref(false)
  const editingItem = ref(null)
  const selectedCurationScore = ref(null)
  const actionLoading = ref(false)
  const confirmTitle = ref('')
  const confirmMessage = ref('')
  const confirmAction = ref({ text: '', color: 'primary', callback: null })

  // Table headers
  const headers = [
    { title: 'Gene', key: 'gene_symbol', sortable: false, width: '120px' },
    { title: 'Disease', key: 'disease_name', sortable: true, width: '200px' },
    { title: 'Verdict', key: 'verdict', sortable: true, width: '140px' },
    { title: 'Score', key: 'total_score', sortable: true, width: '100px' },
    { title: '⚠️', key: 'has_contradictory_evidence', sortable: true, width: '50px' },
    { title: 'GCEP', key: 'gcep_affiliation', sortable: true, width: '120px' },
    { title: 'Status', key: 'status', sortable: true, width: '100px' },
    { title: 'Created', key: 'created_at', sortable: true, width: '100px' },
    { title: 'Actions', key: 'actions', sortable: false, width: '140px' }
  ]

  // Filter options
  const verdictOptions = [
    { title: 'Definitive', value: 'Definitive' },
    { title: 'Strong', value: 'Strong' },
    { title: 'Moderate', value: 'Moderate' },
    { title: 'Limited', value: 'Limited' },
    { title: 'No Known Disease Relationship', value: 'No Known Disease Relationship' },
    { title: 'Disputed', value: 'Disputed' },
    { title: 'Refuted', value: 'Refuted' }
  ]

  const statusOptions = [
    { title: 'Draft', value: 'Draft' },
    { title: 'In Primary Review', value: 'In_Primary_Review' },
    { title: 'In Secondary Review', value: 'In_Secondary_Review' },
    { title: 'Approved', value: 'Approved' },
    { title: 'Published', value: 'Published' },
    { title: 'Rejected', value: 'Rejected' }
  ]

  const sortOptions = [
    { title: 'Created Date', value: 'created_at' },
    { title: 'Updated Date', value: 'updated_at' },
    { title: 'Gene Symbol', value: 'approved_symbol' },
    { title: 'Disease Name', value: 'disease_name' },
    { title: 'Verdict', value: 'verdict' },
    { title: 'Total Score', value: 'total_score' },
    { title: 'Status', value: 'status' }
  ]

  // Statistics cards
  const statisticsCards = computed(() => {
    if (!statistics.value) return []

    return [
      {
        title: 'Total',
        value: statistics.value.total_curations || 0,
        icon: 'mdi-clipboard-check-multiple',
        color: 'primary'
      },
      {
        title: 'High Confidence',
        value: statistics.value.high_confidence_count || 0,
        icon: 'mdi-check-circle',
        color: 'success'
      },
      {
        title: 'Pending',
        value: statistics.value.pending_approval || 0,
        icon: 'mdi-clock-outline',
        color: 'warning'
      },
      {
        title: 'Published',
        value: statistics.value.published_count || 0,
        icon: 'mdi-publish',
        color: 'info'
      },
      {
        title: 'Contradictory',
        value: statistics.value.contradictory_evidence_count || 0,
        icon: 'mdi-alert-triangle',
        color: 'error'
      },
      {
        title: 'Avg Score',
        value: statistics.value.avg_total_score || '0.0',
        icon: 'mdi-chart-line',
        color: 'purple'
      }
    ]
  })

  // Utility functions
  const formatDate = dateString => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const getVerdictColor = verdict => {
    const colors = {
      Definitive: 'success',
      Strong: 'info',
      Moderate: 'warning',
      Limited: 'orange',
      'No Known Disease Relationship': 'grey',
      Disputed: 'error',
      Refuted: 'error'
    }
    return colors[verdict] || 'grey'
  }

  const getVerdictIcon = verdict => {
    const icons = {
      Definitive: 'mdi-check-circle',
      Strong: 'mdi-check-circle-outline',
      Moderate: 'mdi-alert-circle',
      Limited: 'mdi-help-circle',
      'No Known Disease Relationship': 'mdi-minus-circle',
      Disputed: 'mdi-alert-triangle',
      Refuted: 'mdi-close-circle'
    }
    return icons[verdict] || 'mdi-help-circle'
  }

  const getStatusColor = status => {
    const colors = {
      Draft: 'grey',
      In_Primary_Review: 'orange',
      In_Secondary_Review: 'warning',
      Approved: 'success',
      Published: 'info',
      Rejected: 'error'
    }
    return colors[status] || 'grey'
  }

  // Permission checks
  const canEdit = item => {
    return authStore.isCurator && ['Draft', 'In_Primary_Review'].includes(item.status)
  }

  const canApprove = item => {
    return authStore.isAdmin && item.status === 'In_Primary_Review'
  }

  const canPublish = item => {
    return authStore.isCurator && item.status === 'Approved'
  }

  const canSubmitForReview = item => {
    return authStore.isCurator && item.status === 'Draft'
  }

  // Actions
  const editCuration = item => {
    editingItem.value = { ...item }
    editDialog.value = true
  }

  const updateCuration = async updatedData => {
    try {
      actionLoading.value = true
      await curationsStore.updateCuration(editingItem.value.id, updatedData)
      showSuccess('Curation updated successfully')
      editDialog.value = false
      editingItem.value = null
    } catch (error) {
      showError('Failed to update curation')
    } finally {
      actionLoading.value = false
    }
  }

  const viewScoreBreakdown = async item => {
    try {
      const scoreBreakdown = await curationsStore.fetchCurationScoreSummary(item.id)
      selectedCurationScore.value = scoreBreakdown
      scoreDialog.value = true
    } catch (error) {
      showError('Failed to load score breakdown')
    }
  }

  const approveItem = item => {
    confirmTitle.value = 'Approve Curation'
    confirmMessage.value = `Are you sure you want to approve this curation for ${item.gene?.approved_symbol}?`
    confirmAction.value = {
      text: 'Approve',
      color: 'success',
      callback: () => workflowAction(item, 'approve')
    }
    confirmDialog.value = true
  }

  const publishItem = item => {
    confirmTitle.value = 'Publish Curation'
    confirmMessage.value = `Publish this curation for ${item.gene?.approved_symbol}? It will be publicly available.`
    confirmAction.value = {
      text: 'Publish',
      color: 'info',
      callback: () => workflowAction(item, 'publish')
    }
    confirmDialog.value = true
  }

  const submitForReview = item => {
    confirmTitle.value = 'Submit for Review'
    confirmMessage.value = `Submit this curation for ${item.gene?.approved_symbol} for review?`
    confirmAction.value = {
      text: 'Submit',
      color: 'primary',
      callback: () => workflowAction(item, 'submit_for_review')
    }
    confirmDialog.value = true
  }

  const deleteItem = item => {
    confirmTitle.value = 'Delete Curation'
    confirmMessage.value =
      'Are you sure you want to delete this curation? This action cannot be undone.'
    confirmAction.value = {
      text: 'Delete',
      color: 'error',
      callback: () => curationsStore.deleteCuration(item.id)
    }
    confirmDialog.value = true
  }

  const exportCuration = item => {
    // Create a downloadable JSON export of the curation
    const exportData = {
      ...item,
      exported_at: new Date().toISOString(),
      sop_version: 'v11'
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `curation_${item.gene?.approved_symbol}_${item.id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    showSuccess('Curation exported successfully')
  }

  const workflowAction = async (item, action) => {
    try {
      actionLoading.value = true
      await curationsStore.workflowAction(item.id, { action })
      showSuccess(`Curation ${action.replace('_', ' ')} successful`)
    } catch (error) {
      showError(`Failed to ${action.replace('_', ' ')} curation`)
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
      verdict: verdictFilter.value,
      status: statusFilter.value,
      min_total_score: scoreRange.value[0],
      max_total_score: scoreRange.value[1],
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      skip: 0,
      limit: itemsPerPage.value
    }

    page.value = 1
    await curationsStore.searchCurations(searchParams)
  }

  const applySorting = async () => {
    await curationsStore.setSorting(sortBy.value, sortOrder.value)
  }

  const handleTableUpdate = async options => {
    itemsPerPage.value = options.itemsPerPage
    page.value = options.page

    if (curationsStore.searchResults) {
      await applyFilters()
    } else {
      await curationsStore.fetchCurations({
        page: options.page,
        per_page: options.itemsPerPage
      })
    }
  }

  // Lifecycle
  onMounted(async () => {
    try {
      await Promise.all([curationsStore.fetchCurations(), curationsStore.fetchStatistics()])
      statistics.value = curationsStore.statistics
    } catch (error) {
      showError('Failed to load curations')
    }
  })
</script>

<style scoped>
  .gap-1 {
    gap: 4px;
  }

  .disease-name {
    min-width: 180px;
  }

  .score-display {
    text-align: center;
    min-width: 80px;
  }
</style>
