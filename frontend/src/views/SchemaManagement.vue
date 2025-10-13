<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Schema Management</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Manage curation methodologies and schema definitions
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" size="large" @click="createSchemaDialog = true">
        <v-icon start>mdi-plus</v-icon>
        New Schema
      </v-btn>
    </div>

    <!-- Filters and Search -->
    <v-card class="mb-6">
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6" md="4">
            <v-text-field
              v-model="searchQuery"
              placeholder="Search schemas..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" sm="6" md="4">
            <v-select
              v-model="selectedType"
              :items="schemaTypes"
              label="Schema Type"
              variant="outlined"
              density="compact"
              hide-details
              clearable
            />
          </v-col>
          <v-col cols="12" sm="6" md="4">
            <v-select
              v-model="selectedStatus"
              :items="statusOptions"
              label="Status"
              variant="outlined"
              density="compact"
              hide-details
              clearable
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Schemas Table -->
    <v-card>
      <v-card-title>
        <v-icon start>mdi-file-document-outline</v-icon>
        Schemas ({{ filteredSchemas.length }})
      </v-card-title>

      <v-data-table
        :headers="tableHeaders"
        :items="filteredSchemas"
        :loading="loading"
        :search="searchQuery"
        item-value="id"
      >
        <template #item.name="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.name }}</div>
            <div class="text-caption">{{ item.description }}</div>
          </div>
        </template>

        <template #item.type="{ item }">
          <v-chip :color="getTypeColor(item.type)" size="small" variant="outlined">
            {{ formatType(item.type) }}
          </v-chip>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" variant="flat">
            {{ formatStatus(item.status) }}
          </v-chip>
        </template>

        <template #item.version="{ item }">
          <v-chip size="small" color="info" variant="outlined"> v{{ item.version }} </v-chip>
        </template>

        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1">
            <v-btn icon="mdi-eye" size="small" variant="text" @click="viewSchema(item)" />
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="editSchema(item)" />
            <v-btn
              icon="mdi-content-copy"
              size="small"
              variant="text"
              @click="duplicateSchema(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="deleteSchema(item)"
            />
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create Schema Dialog -->
    <v-dialog v-model="createSchemaDialog" max-width="600">
      <v-card>
        <v-card-title>Create New Schema</v-card-title>
        <v-card-text>
          <v-form ref="createForm">
            <v-text-field
              v-model="newSchema.name"
              label="Schema Name"
              variant="outlined"
              :rules="[v => !!v || 'Name is required']"
              required
            />

            <v-textarea
              v-model="newSchema.description"
              label="Description"
              variant="outlined"
              rows="3"
            />

            <v-select
              v-model="newSchema.type"
              :items="schemaTypes"
              label="Schema Type"
              variant="outlined"
              :rules="[v => !!v || 'Type is required']"
              required
            />

            <v-text-field
              v-model="newSchema.version"
              label="Version"
              variant="outlined"
              placeholder="1.0.0"
              :rules="[v => !!v || 'Version is required']"
              required
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="createSchemaDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="creating" @click="createSchema">
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted, onErrorCaptured } from 'vue'
  import { useRouter } from 'vue-router'
  import { useSchemasStore } from '@/stores'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess } from '@/composables/useNotifications'

  const router = useRouter()
  const schemasStore = useSchemasStore()
  const logger = useLogger()

  const loading = ref(false)
  const creating = ref(false)
  const searchQuery = ref('')
  const selectedType = ref(null)
  const selectedStatus = ref(null)
  const createSchemaDialog = ref(false)
  const createForm = ref(null)

  // Error boundary for component-level errors
  onErrorCaptured((err, instance, info) => {
    logger.error('SchemaManagement error', {
      error: err.message,
      stack: err.stack,
      component: instance?.$options?.name || 'SchemaManagement',
      errorInfo: info
    })

    showError('An error occurred in schema management')

    // Don't propagate error up - handle it here
    return false
  })

  const newSchema = ref({
    name: '',
    description: '',
    type: null,
    version: '1.0.0'
  })

  const schemaTypes = [
    { title: 'Precuration', value: 'precuration' },
    { title: 'Curation', value: 'curation' },
    { title: 'Combined', value: 'combined' }
  ]

  const statusOptions = [
    { title: 'Draft', value: 'draft' },
    { title: 'Active', value: 'active' },
    { title: 'Deprecated', value: 'deprecated' }
  ]

  const tableHeaders = [
    { title: 'Name', key: 'name', sortable: true },
    { title: 'Type', key: 'type', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Version', key: 'version', sortable: true },
    { title: 'Created', key: 'created_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  // Defensive computed properties with defaults
  const schemas = computed(() => schemasStore.schemas || [])

  const filteredSchemas = computed(() => {
    // Defensive: ensure schemas is always an array
    let filtered = Array.isArray(schemas.value) ? [...schemas.value] : []

    if (selectedType.value) {
      filtered = filtered.filter(s => s.type === selectedType.value)
    }

    if (selectedStatus.value) {
      filtered = filtered.filter(s => s.status === selectedStatus.value)
    }

    return filtered
  })

  const getTypeColor = type => {
    const colorMap = {
      precuration: 'blue',
      curation: 'green',
      combined: 'purple'
    }
    return colorMap[type] || 'grey'
  }

  const getStatusColor = status => {
    const colorMap = {
      draft: 'orange',
      active: 'success',
      deprecated: 'error'
    }
    return colorMap[status] || 'grey'
  }

  const formatType = type => {
    return type.charAt(0).toUpperCase() + type.slice(1)
  }

  const formatStatus = status => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const formatDate = dateString => {
    return new Date(dateString).toLocaleDateString()
  }

  const viewSchema = schema => {
    logger.info('View schema requested', { schemaId: schema.id, schemaName: schema.name })
    // TODO: Implement schema detail view when available
  }

  const editSchema = schema => {
    try {
      router.push({ name: 'SchemaEditor', params: { id: schema.id } })
      logger.info('Navigate to schema editor', { schemaId: schema.id, schemaName: schema.name })
    } catch (error) {
      logger.error('Failed to navigate to schema editor', {
        schemaId: schema.id,
        error: error.message
      })
      showError('Failed to open schema editor')
    }
  }

  const duplicateSchema = async schema => {
    try {
      const duplicated = await schemasStore.duplicateSchema(schema.id)
      logger.info('Schema duplicated', {
        originalId: schema.id,
        duplicatedId: duplicated.id,
        schemaName: schema.name
      })
      showSuccess(`Schema "${schema.name}" duplicated successfully`)
    } catch (error) {
      logger.error('Failed to duplicate schema', {
        schemaId: schema.id,
        schemaName: schema.name,
        error: error.message,
        stack: error.stack
      })
      showError('Failed to duplicate schema')
    }
  }

  const deleteSchema = async schema => {
    if (confirm(`Are you sure you want to delete "${schema.name}"?`)) {
      try {
        await schemasStore.deleteSchema(schema.id)
        logger.info('Schema deleted', { schemaId: schema.id, schemaName: schema.name })
        showSuccess(`Schema "${schema.name}" deleted successfully`)
      } catch (error) {
        logger.error('Failed to delete schema', {
          schemaId: schema.id,
          schemaName: schema.name,
          error: error.message,
          stack: error.stack
        })
        showError('Failed to delete schema')
      }
    }
  }

  const createSchema = async () => {
    const { valid } = await createForm.value.validate()
    if (!valid) return

    creating.value = true
    try {
      await schemasStore.createSchema(newSchema.value)
      logger.info('Schema created', { schemaName: newSchema.value.name })
      showSuccess(`Schema "${newSchema.value.name}" created successfully`)

      createSchemaDialog.value = false
      newSchema.value = {
        name: '',
        description: '',
        type: null,
        version: '1.0.0'
      }
    } catch (error) {
      logger.error('Failed to create schema', {
        schemaName: newSchema.value.name,
        error: error.message,
        stack: error.stack
      })
      showError('Failed to create schema')
    } finally {
      creating.value = false
    }
  }

  onMounted(async () => {
    loading.value = true
    try {
      await schemasStore.fetchSchemas()
      logger.info('SchemaManagement mounted', { schemasCount: schemas.value.length })
    } catch (error) {
      logger.error('Failed to load schemas', {
        error: error.message,
        status: error.response?.status,
        endpoint: '/api/v1/schemas',
        stack: error.stack
      })

      // Check if 404 (endpoint doesn't exist yet)
      if (error.response?.status === 404) {
        showError('Schema management is not yet available. This feature is under development.')
      } else {
        showError('Failed to load schemas. Please refresh.')
      }
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
