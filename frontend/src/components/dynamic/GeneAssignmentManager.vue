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
            @click="openBulkAssignDialog"
            :disabled="!selectedAssignments.length"
          >
            <v-icon start>mdi-account-multiple-plus</v-icon>
            Bulk Assign ({{ selectedAssignments.length }})
          </v-btn>

          <v-btn
            color="secondary"
            variant="outlined"
            @click="rebalanceWorkload"
            :loading="rebalancing"
          >
            <v-icon start>mdi-scale-balance</v-icon>
            Rebalance Workload
          </v-btn>
        </div>

        <div class="d-flex gap-2">
          <v-btn variant="outlined" @click="exportAssignments" :loading="exporting">
            <v-icon start>mdi-download</v-icon>
            Export
          </v-btn>

          <v-btn variant="outlined" @click="refreshAssignments" :loading="loading">
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
            @click="executeBulkAssignment"
            :loading="bulkAssigning"
          >
            Assign
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { useAssignmentsStore, useScopesStore, useUsersStore } from '@/stores'

  const assignmentsStore = useAssignmentsStore()
  const scopesStore = useScopesStore()
  const usersStore = useUsersStore()

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

  // Computed properties
  const loading = computed(() => assignmentsStore.loading)
  const assignments = computed(() => assignmentsStore.assignments)
  const availableScopes = computed(() => scopesStore.scopes)
  const availableUsers = computed(() => usersStore.users.filter(user => user.role !== 'viewer'))
  const workloadSummary = computed(() => assignmentsStore.workloadSummary)

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

      bulkAssignDialog.value = false
      selectedAssignments.value = []
    } catch (error) {
      console.error('Bulk assignment failed:', error)
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
    } catch (error) {
      console.error('Workload rebalancing failed:', error)
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
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      exporting.value = false
    }
  }

  const refreshAssignments = async () => {
    try {
      await assignmentsStore.fetchAssignments()
    } catch (error) {
      console.error('Refresh failed:', error)
    }
  }

  const editAssignment = assignment => {
    // Emit event or navigate to edit page
    console.log('Edit assignment:', assignment)
  }

  const reassignGene = assignment => {
    // Open reassignment dialog or navigate
    console.log('Reassign gene:', assignment)
  }

  const viewAssignment = assignment => {
    // Navigate to assignment details
    console.log('View assignment:', assignment)
  }

  onMounted(async () => {
    try {
      await Promise.all([
        assignmentsStore.fetchAssignments(),
        assignmentsStore.fetchWorkloadSummary(),
        scopesStore.fetchScopes(),
        usersStore.fetchUsers()
      ])
    } catch (error) {
      console.error('Failed to load assignment data:', error)
    }
  })
</script>

<style scoped>
  .v-data-table {
    border-radius: 8px;
  }
</style>
