<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-account-group</v-icon>
      Gene Assignment Management
    </v-card-title>

    <v-card-text>
      <!-- Assignment Filters -->
      <v-row class="mb-4">
        <v-col cols="12" sm="4">
          <v-select
            v-model="selectedScope"
            :items="availableScopes"
            item-title="display_name"
            item-value="id"
            label="Filter by Scope"
            variant="outlined"
            clearable
            @update:model-value="applyFilters"
          >
            <template #prepend-inner>
              <v-icon>mdi-domain</v-icon>
            </template>
          </v-select>
        </v-col>

        <v-col cols="12" sm="4">
          <v-select
            v-model="selectedStatus"
            :items="statusOptions"
            label="Filter by Status"
            variant="outlined"
            clearable
            @update:model-value="applyFilters"
          >
            <template #prepend-inner>
              <v-icon>mdi-tag</v-icon>
            </template>
          </v-select>
        </v-col>

        <v-col cols="12" sm="4">
          <v-select
            v-model="selectedAssignee"
            :items="availableUsers"
            item-title="full_name"
            item-value="id"
            label="Filter by Assignee"
            variant="outlined"
            clearable
            @update:model-value="applyFilters"
          >
            <template #prepend-inner>
              <v-icon>mdi-account</v-icon>
            </template>
          </v-select>
        </v-col>
      </v-row>

      <!-- Quick Actions -->
      <div class="d-flex justify-space-between align-center mb-4">
        <div class="d-flex gap-2">
          <v-btn
            color="primary"
            variant="flat"
            :disabled="!selectedAssignments.length"
            @click="openBulkAssignDialog"
          >
            <v-icon start>mdi-account-multiple-plus</v-icon>
            Bulk Assign ({{ selectedAssignments.length }})
          </v-btn>

          <v-btn
            color="secondary"
            variant="outlined"
            :loading="rebalancing"
            @click="rebalanceWorkload"
          >
            <v-icon start>mdi-scale-balance</v-icon>
            Rebalance Workload
          </v-btn>
        </div>

        <div class="d-flex gap-2">
          <v-btn variant="outlined" :loading="exporting" @click="exportAssignments">
            <v-icon start>mdi-download</v-icon>
            Export
          </v-btn>

          <v-btn variant="outlined" :loading="loading" @click="refreshAssignments">
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </div>

      <!-- Assignments Table -->
      <v-data-table
        v-model="selectedAssignments"
        :headers="tableHeaders"
        :items="filteredAssignments"
        :loading="loading"
        item-value="id"
        show-select
        :items-per-page="25"
        :search="searchQuery"
      >
        <template #top>
          <v-toolbar flat>
            <v-text-field
              v-model="searchQuery"
              placeholder="Search genes, diseases, or assignees..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              hide-details
              class="mx-4"
            />
          </v-toolbar>
        </template>

        <template #item.gene="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.gene_symbol }}</div>
            <div class="text-caption">{{ item.gene_name }}</div>
          </div>
        </template>

        <template #item.disease="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.disease_name }}</div>
            <div class="text-caption">OMIM: {{ item.omim_id }}</div>
          </div>
        </template>

        <template #item.scope="{ item }">
          <v-chip size="small" color="info" variant="outlined">
            {{ getScopeName(item.scope_id) }}
          </v-chip>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" variant="flat">
            {{ formatStatus(item.status) }}
          </v-chip>
        </template>

        <template #item.assignee="{ item }">
          <div v-if="item.assigned_to">
            <div class="d-flex align-center">
              <v-avatar size="24" class="mr-2">
                <v-icon>mdi-account</v-icon>
              </v-avatar>
              <div>
                <div class="text-body-2">{{ getUserName(item.assigned_to) }}</div>
                <div class="text-caption">{{ getUserRole(item.assigned_to) }}</div>
              </div>
            </div>
          </div>
          <div v-else class="text-medium-emphasis">Unassigned</div>
        </template>

        <template #item.priority="{ item }">
          <v-chip :color="getPriorityColor(item.priority)" size="small" variant="outlined">
            {{ formatPriority(item.priority) }}
          </v-chip>
        </template>

        <template #item.due_date="{ item }">
          <div v-if="item.due_date">
            <div class="text-body-2">{{ formatDate(item.due_date) }}</div>
            <div class="text-caption" :class="getDueDateClass(item.due_date)">
              {{ getDueDateStatus(item.due_date) }}
            </div>
          </div>
          <div v-else class="text-medium-emphasis">No due date</div>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1">
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="editAssignment(item)" />
            <v-btn
              icon="mdi-account-plus"
              size="small"
              variant="text"
              @click="reassignGene(item)"
            />
            <v-btn icon="mdi-eye" size="small" variant="text" @click="viewAssignment(item)" />
          </div>
        </template>
      </v-data-table>

      <!-- Workload Summary -->
      <v-card variant="outlined" class="mt-6">
        <v-card-title class="text-h6">
          <v-icon start>mdi-chart-bar</v-icon>
          Workload Summary
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col v-for="user in workloadSummary" :key="user.id" cols="12" sm="6" md="4">
              <v-card variant="tonal">
                <v-card-text class="text-center">
                  <v-avatar class="mb-2">
                    <v-icon>mdi-account</v-icon>
                  </v-avatar>
                  <div class="font-weight-medium">{{ user.full_name }}</div>
                  <div class="text-caption text-medium-emphasis mb-2">{{ user.role }}</div>
                  <div class="text-h4 text-primary">{{ user.assignment_count }}</div>
                  <div class="text-caption">Active Assignments</div>
                  <v-progress-linear
                    :model-value="getWorkloadPercentage(user.assignment_count)"
                    :color="getWorkloadColor(user.assignment_count)"
                    class="mt-2"
                  />
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-card-text>

    <!-- Bulk Assignment Dialog -->
    <v-dialog v-model="bulkAssignDialog" max-width="600">
      <v-card>
        <v-card-title>Bulk Assignment</v-card-title>
        <v-card-text>
          <v-select
            v-model="bulkAssignee"
            :items="availableUsers"
            item-title="full_name"
            item-value="id"
            label="Assign to User"
            variant="outlined"
            return-object
          />

          <v-select
            v-model="bulkPriority"
            :items="priorityOptions"
            label="Set Priority"
            variant="outlined"
          />

          <v-text-field
            v-model="bulkDueDate"
            type="date"
            label="Due Date (Optional)"
            variant="outlined"
          />

          <v-textarea
            v-model="bulkComment"
            label="Assignment Comment (Optional)"
            variant="outlined"
            rows="3"
          />

          <div class="text-body-2 mt-4">
            <strong>{{ selectedAssignments.length }}</strong> assignments will be updated.
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="bulkAssignDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :loading="bulkAssigning"
            @click="executeBulkAssignment"
          >
            Assign
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
  import { ref, computed, onMounted, onErrorCaptured } from 'vue'
  import { useAssignmentsStore, useScopesStore, useUsersStore, useAuthStore } from '@/stores'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess } from '@/composables/useNotifications'

  const assignmentsStore = useAssignmentsStore()
  const scopesStore = useScopesStore()
  const usersStore = useUsersStore()
  const authStore = useAuthStore()
  const logger = useLogger()

  // Reactive data
  const selectedAssignments = ref([])
  const selectedScope = ref(null)
  const selectedStatus = ref(null)
  const selectedAssignee = ref(null)
  const searchQuery = ref('')
  const bulkAssignDialog = ref(false)
  const bulkAssignee = ref(null)
  const bulkPriority = ref(null)
  const bulkDueDate = ref('')
  const bulkComment = ref('')
  const rebalancing = ref(false)
  const exporting = ref(false)
  const bulkAssigning = ref(false)

  // Computed properties with defensive defaults
  const loading = computed(() => assignmentsStore.loading)
  const assignments = computed(() => assignmentsStore.assignments || [])
  const availableScopes = computed(() => scopesStore.scopes || [])
  const availableUsers = computed(() => (usersStore.users || []).filter(user => user.role !== 'viewer'))
  const workloadSummary = computed(() => assignmentsStore.workloadSummary || [])

  // Error boundary for component-level errors
  onErrorCaptured((err, instance, info) => {
    logger.error('GeneAssignmentManager error', {
      error: err.message,
      stack: err.stack,
      component: instance?.$options?.name || 'GeneAssignmentManager',
      errorInfo: info
    })

    showError('An error occurred in the assignment manager')

    // Don't propagate error up - handle it here
    return false
  })

  const statusOptions = [
    { title: 'Unassigned', value: 'unassigned' },
    { title: 'Assigned', value: 'assigned' },
    { title: 'In Progress', value: 'in_progress' },
    { title: 'Under Review', value: 'under_review' },
    { title: 'Completed', value: 'completed' },
    { title: 'On Hold', value: 'on_hold' }
  ]

  const priorityOptions = [
    { title: 'Low', value: 'low' },
    { title: 'Medium', value: 'medium' },
    { title: 'High', value: 'high' },
    { title: 'Urgent', value: 'urgent' }
  ]

  const tableHeaders = [
    { title: 'Gene', key: 'gene', sortable: true },
    { title: 'Disease', key: 'disease', sortable: true },
    { title: 'Scope', key: 'scope', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Assignee', key: 'assignee', sortable: true },
    { title: 'Priority', key: 'priority', sortable: true },
    { title: 'Due Date', key: 'due_date', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  const filteredAssignments = computed(() => {
    let filtered = [...assignments.value]

    if (selectedScope.value) {
      filtered = filtered.filter(a => a.scope_id === selectedScope.value)
    }

    if (selectedStatus.value) {
      filtered = filtered.filter(a => a.status === selectedStatus.value)
    }

    if (selectedAssignee.value) {
      filtered = filtered.filter(a => a.assigned_to === selectedAssignee.value)
    }

    return filtered
  })

  // Helper methods
  const getScopeName = scopeId => {
    const scope = availableScopes.value.find(s => s.id === scopeId)
    return scope?.display_name || 'Unknown'
  }

  const getUserName = userId => {
    const user = availableUsers.value.find(u => u.id === userId)
    return user?.full_name || 'Unknown'
  }

  const getUserRole = userId => {
    const user = availableUsers.value.find(u => u.id === userId)
    return user?.role || 'Unknown'
  }

  const getStatusColor = status => {
    const colorMap = {
      unassigned: 'grey',
      assigned: 'info',
      in_progress: 'primary',
      under_review: 'warning',
      completed: 'success',
      on_hold: 'orange'
    }
    return colorMap[status] || 'grey'
  }

  const getPriorityColor = priority => {
    const colorMap = {
      low: 'green',
      medium: 'orange',
      high: 'red',
      urgent: 'deep-purple'
    }
    return colorMap[priority] || 'grey'
  }

  const getWorkloadColor = count => {
    if (count > 20) return 'red'
    if (count > 15) return 'orange'
    if (count > 10) return 'yellow'
    return 'green'
  }

  const getWorkloadPercentage = count => {
    const maxWorkload = Math.max(...workloadSummary.value.map(u => u.assignment_count), 25)
    return (count / maxWorkload) * 100
  }

  const formatStatus = status => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatPriority = priority => {
    return priority.charAt(0).toUpperCase() + priority.slice(1)
  }

  const formatDate = dateString => {
    return new Date(dateString).toLocaleDateString()
  }

  const getDueDateClass = dateString => {
    const dueDate = new Date(dateString)
    const today = new Date()
    const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24))

    if (diffDays < 0) return 'text-error'
    if (diffDays < 7) return 'text-warning'
    return 'text-success'
  }

  const getDueDateStatus = dateString => {
    const dueDate = new Date(dateString)
    const today = new Date()
    const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24))

    if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`
    if (diffDays === 0) return 'Due today'
    if (diffDays === 1) return 'Due tomorrow'
    return `${diffDays} days remaining`
  }

  // Actions
  const applyFilters = () => {
    // Filters are applied reactively through computed property
  }

  const openBulkAssignDialog = () => {
    bulkAssignDialog.value = true
    bulkAssignee.value = null
    bulkPriority.value = null
    bulkDueDate.value = ''
    bulkComment.value = ''
  }

  const executeBulkAssignment = async () => {
    if (!bulkAssignee.value) return

    bulkAssigning.value = true
    try {
      await assignmentsStore.bulkUpdateAssignments({
        assignment_ids: selectedAssignments.value,
        assigned_to: bulkAssignee.value.id,
        priority: bulkPriority.value,
        due_date: bulkDueDate.value || null,
        comment: bulkComment.value || null
      })

      logger.info('Bulk assignment successful', {
        count: selectedAssignments.value.length,
        assignedTo: bulkAssignee.value.full_name
      })
      showSuccess(`Successfully assigned ${selectedAssignments.value.length} items`)

      bulkAssignDialog.value = false
      selectedAssignments.value = []
    } catch (error) {
      logger.error('Bulk assignment failed', {
        count: selectedAssignments.value.length,
        error: error.message,
        stack: error.stack
      })
      showError('Bulk assignment failed')
    } finally {
      bulkAssigning.value = false
    }
  }

  const rebalanceWorkload = async () => {
    rebalancing.value = true
    try {
      await assignmentsStore.rebalanceWorkload({
        scope_id: selectedScope.value
      })
      logger.info('Workload rebalanced', { scopeId: selectedScope.value })
      showSuccess('Workload rebalanced successfully')
    } catch (error) {
      logger.error('Workload rebalancing failed', {
        scopeId: selectedScope.value,
        error: error.message,
        stack: error.stack
      })
      showError('Workload rebalancing failed')
    } finally {
      rebalancing.value = false
    }
  }

  const exportAssignments = async () => {
    exporting.value = true
    try {
      await assignmentsStore.exportAssignments({
        scope_id: selectedScope.value,
        status: selectedStatus.value,
        assigned_to: selectedAssignee.value
      })
      logger.info('Assignments exported', {
        scopeId: selectedScope.value,
        status: selectedStatus.value
      })
      showSuccess('Assignments exported successfully')
    } catch (error) {
      logger.error('Export failed', {
        error: error.message,
        stack: error.stack
      })
      showError('Export failed')
    } finally {
      exporting.value = false
    }
  }

  const refreshAssignments = async () => {
    try {
      await assignmentsStore.fetchAssignments()
      logger.info('Assignments refreshed', { count: assignments.value.length })
      showSuccess('Assignments refreshed')
    } catch (error) {
      logger.error('Refresh failed', {
        error: error.message,
        stack: error.stack
      })
      showError('Refresh failed')
    }
  }

  const editAssignment = assignment => {
    logger.info('Edit assignment requested', { assignmentId: assignment.id })
    // TODO: Implement assignment edit when available
  }

  const reassignGene = assignment => {
    logger.info('Reassign gene requested', {
      assignmentId: assignment.id,
      geneSymbol: assignment.gene_symbol
    })
    // TODO: Implement gene reassignment when available
  }

  const viewAssignment = assignment => {
    logger.info('View assignment requested', { assignmentId: assignment.id })
    // TODO: Implement assignment detail view when available
  }

  onMounted(async () => {
    try {
      const curatorId = authStore.user?.id

      // Call existing methods with proper parameters
      const promises = [
        assignmentsStore.fetchAssignments(),
        scopesStore.fetchScopes(),
        usersStore.fetchUsers()
      ]

      // Only fetch curator workload if user is logged in
      if (curatorId) {
        promises.push(assignmentsStore.fetchCuratorWorkload(curatorId))
      } else {
        logger.warn('No curator ID available for workload fetch')
      }

      await Promise.all(promises)

      logger.info('GeneAssignmentManager mounted', {
        assignmentsCount: assignments.value.length,
        scopesCount: availableScopes.value.length,
        usersCount: availableUsers.value.length
      })
    } catch (error) {
      logger.error('Failed to load assignment data', {
        error: error.message,
        stack: error.stack
      })
      showError('Failed to load assignment data. Please refresh.')
    }
  })
</script>

<style scoped>
  .v-data-table {
    border-radius: 8px;
  }
</style>
