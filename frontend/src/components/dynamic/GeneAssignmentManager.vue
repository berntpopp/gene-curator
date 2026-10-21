<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-account-group</v-icon>
      Gene assignment management
    </v-card-title>

    <v-alert v-if="loadError" type="error" variant="tonal" class="mx-4">
      {{ loadError }}
      <template #append>
        <v-btn class="retry" variant="text" @click="loadAll">Retry</v-btn>
      </template>
    </v-alert>

    <v-card-text v-else>
      <!-- Assignment Filters -->
      <v-row class="mb-4">
        <v-col cols="12" sm="6">
          <v-select
            v-model="selectedScope"
            :items="availableScopes"
            item-title="display_name"
            item-value="id"
            label="Filter by Scope"
            variant="outlined"
            clearable
          >
            <template #prepend-inner>
              <v-icon>mdi-domain</v-icon>
            </template>
          </v-select>
        </v-col>

        <v-col cols="12" sm="6">
          <v-select
            v-model="selectedAssignee"
            :items="availableUsers"
            item-title="name"
            item-value="id"
            label="Filter by Assignee"
            variant="outlined"
            clearable
          >
            <template #prepend-inner>
              <v-icon>mdi-account</v-icon>
            </template>
          </v-select>
        </v-col>
      </v-row>

      <!-- Quick Actions -->
      <div class="d-flex justify-space-between align-center mb-4">
        <div class="d-flex ga-2">
          <v-btn
            color="primary"
            variant="flat"
            :disabled="!selectedAssignments.length"
            @click="openBulkAssignDialog"
          >
            <v-icon start>mdi-account-multiple-plus</v-icon>
            Bulk Assign ({{ selectedAssignments.length }})
          </v-btn>
        </div>

        <div class="d-flex ga-2">
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
              label="Search genes or assignees"
              placeholder="Search genes or assignees..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              hide-details
              class="mx-4"
            />
          </v-toolbar>
        </template>

        <template #item.gene_symbol="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.gene_symbol }}</div>
            <div class="text-body-small">{{ item.gene_hgnc_id }}</div>
          </div>
        </template>

        <template #item.scope_name="{ item }">
          <v-chip size="small" color="info" variant="outlined" :to="`/scopes/${item.scope_id}`">
            {{ item.scope_name }}
          </v-chip>
        </template>

        <template #item.curator_name="{ item }">
          <div v-if="item.assigned_curator_id">
            <div class="d-flex align-center">
              <v-avatar size="24" class="mr-2">
                <v-icon>mdi-account</v-icon>
              </v-avatar>
              <div>
                <div class="text-body-medium">{{ item.curator_name }}</div>
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

        <template #item.actions="{ item }">
          <div class="d-flex ga-1">
            <v-btn
              aria-label="Edit assignment"
              icon="mdi-pencil"
              size="small"
              variant="text"
              @click="editAssignment(item)"
            />
            <v-btn
              aria-label="Reassign gene"
              icon="mdi-account-plus"
              size="small"
              variant="text"
              @click="reassignGene(item)"
            />
            <v-btn
              aria-label="View assignment"
              icon="mdi-eye"
              size="small"
              variant="text"
              @click="viewAssignment(item)"
            />
          </div>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Bulk Assignment Dialog -->
    <BaseDialog v-model="bulkAssignDialog" size="md" title="Bulk assignment">
      <v-select
        v-model="bulkAssignee"
        :items="availableUsers"
        item-title="name"
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

      <v-textarea
        v-model="bulkComment"
        label="Assignment Comment (Optional)"
        variant="outlined"
        rows="3"
      />

      <div class="text-body-medium mt-4">
        <strong>{{ selectedAssignments.length }}</strong> assignments will be updated.
      </div>
      <template #actions>
        <v-btn variant="text" @click="bulkAssignDialog = false">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="bulkAssigning"
          @click="executeBulkAssignment"
        >
          Assign
        </v-btn>
      </template></BaseDialog
    >

    <!-- Edit Assignment Dialog -->
    <BaseDialog v-model="editDialog" size="md">
      <template #title><v-icon start>mdi-pencil</v-icon> Edit assignment</template>
      <v-form ref="editForm">
        <v-select
          v-model="editFormData.priority_level"
          :items="priorityOptions"
          item-title="title"
          item-value="value"
          label="Priority"
          variant="outlined"
        />
      </v-form>
      <template #actions>
        <v-btn variant="text" @click="editDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" @click="saveAssignment">
          Save
        </v-btn>
      </template></BaseDialog
    >

    <!-- View Assignment Dialog -->
    <BaseDialog v-model="viewDialog" size="md">
      <template #title><v-icon start>mdi-eye</v-icon> Assignment details</template
      ><template v-if="selectedAssignment">
        <v-list>
          <v-list-item>
            <v-list-item-title>Gene</v-list-item-title>
            <v-list-item-subtitle>
              {{ selectedAssignment.gene_symbol }} ({{ selectedAssignment.gene_hgnc_id }})
            </v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Scope</v-list-item-title>
            <v-list-item-subtitle>{{ selectedAssignment.scope_name }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Assignee</v-list-item-title>
            <v-list-item-subtitle>{{
              selectedAssignment.curator_name || 'Unassigned'
            }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Priority</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip :color="getPriorityColor(selectedAssignment.priority)" size="small">
                {{ selectedAssignment.priority }}
              </v-chip>
            </v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Assigned</v-list-item-title>
            <v-list-item-subtitle>{{
              formatDateTime(selectedAssignment.assigned_at)
            }}</v-list-item-subtitle>
          </v-list-item>
        </v-list> </template
      ><template #actions>
        <v-btn variant="text" @click="viewDialog = false">Close</v-btn>
      </template></BaseDialog
    >

    <!-- Reassign Dialog -->
    <BaseDialog v-model="reassignDialog" size="md">
      <template #title><v-icon start>mdi-account-plus</v-icon> Reassign gene</template>
      <div class="text-body-medium mb-4">
        Reassigning
        <strong>{{ reassigningAssignment?.gene_symbol }}</strong>
        from
        <strong>{{ reassigningAssignment?.curator_name || 'Unassigned' }}</strong>
      </div>
      <v-form ref="reassignForm">
        <v-select
          v-model="reassignCuratorId"
          :items="availableUsers"
          item-title="name"
          item-value="id"
          label="New Curator"
          variant="outlined"
          :rules="[v => !!v || 'Please select a curator']"
          required
        />
      </v-form>
      <template #actions>
        <v-btn variant="text" @click="reassignDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="reassigning" @click="executeReassign">
          Reassign
        </v-btn>
      </template></BaseDialog
    >
  </v-card>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted, onErrorCaptured } from 'vue'
  import { formatDateTime } from '@/utils/format'
  import { useAssignmentsStore, useScopesStore, useUsersStore, useAuthStore } from '@/stores'
  import { assignmentsAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { errorDetails } from './errorDetails'
  import { formatPriority, getPriorityColor, priorityOptions } from './assignmentDisplay'
  import type { Schema } from '@/types/api'
  import BaseDialog from '@/components/BaseDialog.vue'

  const assignmentsStore = useAssignmentsStore()
  const scopesStore = useScopesStore()
  const usersStore = useUsersStore()
  const authStore = useAuthStore()
  const logger = useLogger()

  /** Subset of Vuetify's VForm instance used here */
  interface FormHandle {
    validate: () => Promise<{ valid: boolean }>
  }

  /** One row of the assignments table */
  type GeneAssignment = Schema<'GeneScopeAssignmentSummary'>

  type AssignedUser = Schema<'UserResponse'>

  interface EditFormData {
    priority_level: string | null
  }

  // Reactive data
  // v-data-table's selection holds item-value keys (assignment ids)
  const selectedAssignments = ref<string[]>([])
  const selectedScope = ref<string | null>(null)
  const selectedAssignee = ref<string | null>(null)
  const searchQuery = ref('')
  const bulkAssignDialog = ref(false)
  const bulkAssignee = ref<AssignedUser | null>(null)
  const bulkPriority = ref<string | null>(null)
  const bulkComment = ref('')
  const bulkAssigning = ref(false)
  const viewDialog = ref(false)
  const selectedAssignment = ref<GeneAssignment | null>(null)
  const editDialog = ref(false)
  const saving = ref(false)
  const editFormData = ref<EditFormData>({
    priority_level: null
  })
  let editingAssignmentId: string | null = null
  const reassignDialog = ref(false)
  const reassignForm = ref<FormHandle | null>(null)
  const reassigning = ref(false)
  const reassigningAssignment = ref<GeneAssignment | null>(null)
  const reassignCuratorId = ref<string | null>(null)

  const loading = computed(() => assignmentsStore.loading)
  const assignments = computed(() => assignmentsStore.assignments)
  const availableScopes = computed(() => scopesStore.scopes)
  const availableUsers = computed(() => usersStore.users.filter(user => user.is_active))

  // Error boundary for component-level errors
  onErrorCaptured((err, instance, info) => {
    logger.error('GeneAssignmentManager error', {
      ...errorDetails(err),
      component: instance?.$options?.name || 'GeneAssignmentManager',
      errorInfo: info
    })

    showError('An error occurred in the assignment manager')

    // Don't propagate error up - handle it here
    return false
  })

  const tableHeaders = [
    { title: 'Gene', key: 'gene_symbol', sortable: true },
    { title: 'Scope', key: 'scope_name', sortable: true },
    { title: 'Assignee', key: 'curator_name', sortable: true },
    { title: 'Priority', key: 'priority', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  const filteredAssignments = computed(() => {
    let filtered = [...assignments.value]

    if (selectedScope.value) {
      filtered = filtered.filter(a => a.scope_id === selectedScope.value)
    }

    if (selectedAssignee.value) {
      filtered = filtered.filter(a => a.assigned_curator_id === selectedAssignee.value)
    }

    return filtered
  })

  // Actions
  const openBulkAssignDialog = () => {
    bulkAssignDialog.value = true
    bulkAssignee.value = null
    bulkPriority.value = null
    bulkComment.value = ''
  }

  const executeBulkAssignment = async () => {
    if (!bulkAssignee.value) return

    bulkAssigning.value = true
    try {
      // The curator goes through the dedicated assign-curator endpoint; the PUT update
      // carries priority, due date and note only when one was chosen.
      const curatorId = bulkAssignee.value.id
      const hasUpdate = bulkPriority.value || bulkComment.value
      for (const id of selectedAssignments.value) {
        await assignmentsAPI.assignCurator(id, curatorId)
        if (hasUpdate) {
          await assignmentsAPI.updateAssignment(id, {
            ...(bulkPriority.value && { priority_level: bulkPriority.value }),
            ...(bulkComment.value && { assignment_notes: bulkComment.value })
          })
        }
      }
      await assignmentsStore.fetchAssignments()

      logger.info('Bulk assignment successful', {
        count: selectedAssignments.value.length,
        assignedTo: bulkAssignee.value.name
      })
      showSuccess(`Successfully assigned ${selectedAssignments.value.length} items`)

      bulkAssignDialog.value = false
      selectedAssignments.value = []
    } catch (err) {
      logger.error('Bulk assignment failed', {
        count: selectedAssignments.value.length,
        ...errorDetails(err)
      })
      showError('Bulk assignment failed')
    } finally {
      bulkAssigning.value = false
    }
  }

  const refreshAssignments = async () => {
    try {
      await assignmentsStore.fetchAssignments()
      logger.info('Assignments refreshed', { count: assignments.value.length })
      showSuccess('Assignments refreshed')
    } catch (err) {
      logger.error('Refresh failed', errorDetails(err))
      showError('Refresh failed')
    }
  }

  const editAssignment = (assignment: GeneAssignment) => {
    logger.info('Edit assignment requested', { assignmentId: assignment.id })
    editingAssignmentId = assignment.id
    editFormData.value = {
      priority_level: assignment.priority
    }
    editDialog.value = true
  }

  const saveAssignment = async () => {
    if (!editingAssignmentId) return
    saving.value = true
    try {
      await assignmentsStore.updateAssignment(editingAssignmentId, {
        priority_level: editFormData.value.priority_level
      })
      showSuccess('Assignment updated successfully')
      editDialog.value = false
    } catch (err) {
      showError('Failed to update assignment')
      logger.error('Save assignment failed', { error: errorDetails(err).error })
    } finally {
      saving.value = false
    }
  }

  const reassignGene = (assignment: GeneAssignment) => {
    logger.info('Reassign gene requested', {
      assignmentId: assignment.id,
      geneSymbol: assignment.gene_symbol
    })
    reassigningAssignment.value = assignment
    reassignCuratorId.value = null
    reassignDialog.value = true
  }

  const executeReassign = async () => {
    const { valid } = await reassignForm.value!.validate()
    const curatorId = reassignCuratorId.value
    if (!valid || !curatorId) return
    reassigning.value = true
    try {
      await assignmentsAPI.assignCurator(reassigningAssignment.value!.id, curatorId)
      showSuccess('Gene reassigned successfully')
      reassignDialog.value = false
      await assignmentsStore.fetchAssignments()
    } catch (err) {
      showError('Failed to reassign gene')
      logger.error('Reassign failed', { error: errorDetails(err).error })
    } finally {
      reassigning.value = false
    }
  }

  const viewAssignment = (assignment: GeneAssignment) => {
    logger.info('View assignment requested', { assignmentId: assignment.id })
    selectedAssignment.value = assignment
    viewDialog.value = true
  }

  const loadError = ref<string | null>(null)

  async function loadAll() {
    loadError.value = null
    try {
      const promises: Promise<unknown>[] = [
        assignmentsStore.fetchAssignments(),
        scopesStore.fetchUserScopes()
      ]
      // GET /users is admin-only; curators would only get a 403
      if (authStore.isAdmin) promises.push(usersStore.fetchUsers())
      await Promise.all(promises)

      logger.info('GeneAssignmentManager mounted', {
        assignmentsCount: assignments.value.length,
        scopesCount: availableScopes.value.length,
        usersCount: availableUsers.value.length
      })
    } catch (err) {
      logger.error('Failed to load assignment data', errorDetails(err))
      loadError.value = assignmentsStore.error ?? 'Failed to load assignment data'
    }
  }

  onMounted(loadAll)
</script>

<style scoped>
  .v-data-table {
    border-radius: 8px;
  }
</style>
