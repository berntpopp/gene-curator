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
      <v-btn color="primary" variant="flat" @click="createWorkflowDialog = true" size="large">
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
              @click="deleteWorkflow(item)"
              :disabled="item.usage_count > 0"
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
          <v-btn color="primary" variant="flat" @click="createWorkflow" :loading="creating">
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useSchemasStore, useWorkflowStore } from '@/stores'

  const schemasStore = useSchemasStore()
  const workflowStore = useWorkflowStore()

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

  const workflowPairs = computed(() => workflowStore.workflowPairs)
  const workflowStages = computed(() => workflowStore.workflowStages)
  const precurationSchemas = computed(() => schemasStore.getPrecurationSchemas)
  const curationSchemas = computed(() => schemasStore.getCurationSchemas)

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
    console.log('View workflow:', workflow)
  }

  const editWorkflow = workflow => {
    console.log('Edit workflow:', workflow)
  }

  const deleteWorkflow = async workflow => {
    if (confirm(`Are you sure you want to delete "${workflow.name}"?`)) {
      try {
        await workflowStore.deleteWorkflowPair(workflow.id)
      } catch (error) {
        console.error('Failed to delete workflow:', error)
      }
    }
  }

  const editStage = stage => {
    console.log('Edit stage:', stage)
  }

  const createWorkflow = async () => {
    const { valid } = await createForm.value.validate()
    if (!valid) return

    creating.value = true
    try {
      await workflowStore.createWorkflowPair(newWorkflow.value)
      createWorkflowDialog.value = false
      newWorkflow.value = {
        name: '',
        description: '',
        precuration_schema_id: null,
        curation_schema_id: null
      }
    } catch (error) {
      console.error('Failed to create workflow:', error)
    } finally {
      creating.value = false
    }
  }

  onMounted(async () => {
    loading.value = true
    try {
      await Promise.all([
        workflowStore.fetchWorkflowPairs(),
        workflowStore.fetchWorkflowStages(),
        schemasStore.fetchSchemas()
      ])
    } catch (error) {
      console.error('Failed to load workflow data:', error)
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
