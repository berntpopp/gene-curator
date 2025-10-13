<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Workflow Management</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Manage workflow pairs and multi-stage curation pipelines
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" size="large" @click="createWorkflowDialog = true">
        <v-icon start>mdi-plus</v-icon>
        New Workflow Pair
      </v-btn>
    </div>

    <!-- Workflow Pairs Table -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-workflow</v-icon>
        Workflow Pairs ({{ workflowPairs.length }})
      </v-card-title>

      <v-data-table
        :headers="workflowHeaders"
        :items="workflowPairs"
        :loading="loading"
        item-value="id"
      >
        <template #item.name="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.name }}</div>
            <div class="text-caption">{{ item.description }}</div>
          </div>
        </template>

        <template #item.schemas="{ item }">
          <div>
            <v-chip size="small" color="blue" variant="outlined" class="mb-1">
              Pre: {{ item.precuration_schema_name }}
            </v-chip>
            <br />
            <v-chip size="small" color="green" variant="outlined">
              Cur: {{ item.curation_schema_name }}
            </v-chip>
          </div>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" variant="flat">
            {{ formatStatus(item.status) }}
          </v-chip>
        </template>

        <template #item.usage_count="{ item }">
          <div class="text-center">
            <div class="text-h6 font-weight-bold">{{ item.usage_count || 0 }}</div>
            <div class="text-caption">Active</div>
          </div>
        </template>

        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1">
            <v-btn icon="mdi-eye" size="small" variant="text" @click="viewWorkflow(item)" />
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="editWorkflow(item)" />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              :disabled="item.usage_count > 0"
              @click="deleteWorkflow(item)"
            />
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Workflow Stages Configuration -->
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-stairs</v-icon>
        Workflow Stages Configuration
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col v-for="stage in workflowStages" :key="stage.id" cols="12" sm="6" md="4">
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1">
                <v-icon :color="getStageColor(stage.stage_type)" start>
                  {{ getStageIcon(stage.stage_type) }}
                </v-icon>
                {{ stage.name }}
              </v-card-title>
              <v-card-text>
                <div class="text-body-2 mb-2">{{ stage.description }}</div>
                <div class="text-caption text-medium-emphasis">
                  Required Roles: {{ stage.required_roles.join(', ') }}
                </div>
                <div class="text-caption text-medium-emphasis">Order: {{ stage.order }}</div>
              </v-card-text>
              <v-card-actions>
                <v-btn size="small" variant="text" @click="editStage(stage)">
                  <v-icon start>mdi-pencil</v-icon>
                  Edit
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Create Workflow Dialog -->
    <v-dialog v-model="createWorkflowDialog" max-width="600">
      <v-card>
        <v-card-title>Create New Workflow Pair</v-card-title>
        <v-card-text>
          <v-form ref="createForm">
            <v-text-field
              v-model="newWorkflow.name"
              label="Workflow Pair Name"
              variant="outlined"
              :rules="[v => !!v || 'Name is required']"
              required
            />

            <v-textarea
              v-model="newWorkflow.description"
              label="Description"
              variant="outlined"
              rows="3"
            />

            <v-select
              v-model="newWorkflow.precuration_schema_id"
              :items="precurationSchemas"
              item-title="name"
              item-value="id"
              label="Precuration Schema"
              variant="outlined"
              :rules="[v => !!v || 'Precuration schema is required']"
              required
            />

            <v-select
              v-model="newWorkflow.curation_schema_id"
              :items="curationSchemas"
              item-title="name"
              item-value="id"
              label="Curation Schema"
              variant="outlined"
              :rules="[v => !!v || 'Curation schema is required']"
              required
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="createWorkflowDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="creating" @click="createWorkflow">
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted, onErrorCaptured } from 'vue'
  import { useSchemasStore, useWorkflowStore } from '@/stores'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess, showInfo } from '@/composables/useNotifications'

  const schemasStore = useSchemasStore()
  const workflowStore = useWorkflowStore()
  const logger = useLogger()

  const loading = ref(false)
  const creating = ref(false)
  const createWorkflowDialog = ref(false)
  const createForm = ref(null)

  const newWorkflow = ref({
    name: '',
    description: '',
    precuration_schema_id: null,
    curation_schema_id: null
  })

  const workflowHeaders = [
    { title: 'Name', key: 'name', sortable: true },
    { title: 'Schemas', key: 'schemas', sortable: false },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Usage', key: 'usage_count', sortable: true },
    { title: 'Created', key: 'created_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  // Defensive computed properties with defaults
  const workflowPairs = computed(() => workflowStore.workflowPairs || [])
  const workflowStages = computed(() => workflowStore.workflowStages || [])
  const precurationSchemas = computed(() => schemasStore.getPrecurationSchemas || [])
  const curationSchemas = computed(() => schemasStore.getCurationSchemas || [])

  // Error boundary for component-level errors
  onErrorCaptured((err, instance, info) => {
    logger.error('WorkflowManagement error', {
      error: err.message,
      stack: err.stack,
      component: instance?.$options?.name || 'WorkflowManagement',
      errorInfo: info
    })

    showError('An error occurred while rendering the workflow management')

    // Don't propagate error up - handle it here
    return false
  })

  const getStatusColor = status => {
    const colorMap = {
      active: 'success',
      draft: 'warning',
      deprecated: 'error'
    }
    return colorMap[status] || 'grey'
  }

  const getStageColor = stageType => {
    const colorMap = {
      entry: 'blue',
      precuration: 'orange',
      curation: 'green',
      review: 'purple',
      active: 'success'
    }
    return colorMap[stageType] || 'grey'
  }

  const getStageIcon = stageType => {
    const iconMap = {
      entry: 'mdi-file-document-plus',
      precuration: 'mdi-file-document-edit',
      curation: 'mdi-file-document-check',
      review: 'mdi-eye-check',
      active: 'mdi-check-circle'
    }
    return iconMap[stageType] || 'mdi-circle'
  }

  const formatStatus = status => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const formatDate = dateString => {
    return new Date(dateString).toLocaleDateString()
  }

  const viewWorkflow = workflow => {
    logger.info('View workflow requested', { workflowId: workflow.id, workflowName: workflow.name })
    // TODO: Implement workflow detail view when available
    showInfo('Workflow detail view coming soon')
  }

  const editWorkflow = workflow => {
    logger.info('Edit workflow requested', { workflowId: workflow.id, workflowName: workflow.name })
    // TODO: Implement workflow edit when available
    showInfo('Workflow editing coming soon')
  }

  const deleteWorkflow = async workflow => {
    if (confirm(`Are you sure you want to delete "${workflow.name}"?`)) {
      try {
        await workflowStore.deleteWorkflowPair(workflow.id)
        logger.info('Workflow deleted', { workflowId: workflow.id, workflowName: workflow.name })
        showSuccess('Workflow deleted successfully')
      } catch (error) {
        logger.error('Failed to delete workflow', {
          workflowId: workflow.id,
          error: error.message,
          stack: error.stack
        })
        showError('Failed to delete workflow')
      }
    }
  }

  const editStage = stage => {
    logger.info('Edit stage requested', { stageId: stage.id, stageName: stage.name })
    // TODO: Implement stage edit when available
    showInfo('Stage editing coming soon')
  }

  const createWorkflow = async () => {
    const { valid } = await createForm.value.validate()
    if (!valid) return

    creating.value = true
    try {
      await workflowStore.createWorkflowPair(newWorkflow.value)
      logger.info('Workflow created', { workflowName: newWorkflow.value.name })
      showSuccess('Workflow created successfully')

      createWorkflowDialog.value = false
      newWorkflow.value = {
        name: '',
        description: '',
        precuration_schema_id: null,
        curation_schema_id: null
      }
    } catch (error) {
      logger.error('Failed to create workflow', {
        workflowName: newWorkflow.value.name,
        error: error.message,
        stack: error.stack
      })
      showError('Failed to create workflow')
    } finally {
      creating.value = false
    }
  }

  onMounted(async () => {
    loading.value = true
    try {
      // Call existing methods
      await Promise.all([
        workflowStore.fetchWorkflowAnalytics(),
        workflowStore.fetchPeerReviewers(),
        schemasStore.fetchSchemas()
      ])

      logger.info('WorkflowManagement mounted', {
        analyticsLoaded: !!workflowStore.analytics,
        reviewersCount: workflowStore.peerReviewers?.length || 0,
        schemasCount: schemasStore.schemas?.length || 0
      })
    } catch (error) {
      logger.error('Failed to load workflow data', {
        error: error.message,
        stack: error.stack
      })
      showError('Failed to load workflow data. Please refresh.')
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  .v-data-table {
    border-radius: 8px;
  }
</style>
