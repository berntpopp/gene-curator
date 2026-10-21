<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="page-title text-headline-large font-weight-bold">{{ TERMINOLOGY.TEMPLATES }}</h1>
        <p class="text-body-large text-medium-emphasis mt-1">
          Manage curation methodologies and schema definitions
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" size="large" @click="createSchemaDialog = true">
        <v-icon start>mdi-plus</v-icon>
        New {{ TERMINOLOGY.TEMPLATE }}
      </v-btn>
    </div>

    <!-- Schemas Table -->
    <v-card>
      <v-card-title>
        <v-icon start>mdi-file-document-outline</v-icon>
        {{ TERMINOLOGY.TEMPLATES }} ({{ filteredSchemas.length }})
      </v-card-title>

      <v-card-text class="pb-0">
        <v-row>
          <v-col cols="12" sm="6" md="4">
            <v-text-field
              v-model="searchQuery"
              placeholder="Search templates..."
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

      <v-data-table
        style="min-height: 400px"
        :headers="tableHeaders"
        :items="filteredSchemas"
        :loading="loading"
        :search="searchQuery"
        item-value="id"
      >
        <template #item.name="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.name }}</div>
            <div class="text-body-small">{{ item.description }}</div>
          </div>
        </template>

        <template #item.type="{ item }">
          <v-chip size="small" variant="outlined">
            {{ formatType(item.type) }}
          </v-chip>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="curationStatusColor(item.status)" size="small" variant="flat">
            {{ item.status === 'active' ? 'Active' : 'Inactive' }}
          </v-chip>
        </template>

        <template #item.version="{ item }"> v{{ item.version }} </template>

        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex ga-1">
            <v-btn
              aria-label="Edit schema"
              icon="mdi-pencil"
              size="small"
              variant="text"
              @click="editSchema(item)"
            />
            <v-btn
              aria-label="Derive schema from latest version"
              icon="mdi-content-copy"
              size="small"
              variant="text"
              @click="duplicateSchema(item)"
            />
            <v-btn
              aria-label="Delete schema"
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
    <BaseDialog v-model="createSchemaDialog" size="md">
      <template #title>Create new {{ TERMINOLOGY.TEMPLATE }}</template>
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
      <template #actions>
        <v-btn variant="text" @click="createSchemaDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="creating" @click="createSchema">
          Create
        </v-btn>
      </template></BaseDialog
    >
  </v-container>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
  import { formatDate } from '@/utils/format'
  import { ref, computed, onMounted, onErrorCaptured } from 'vue'
  import { useRouter } from 'vue-router'
  import { useSchemasStore } from '@/stores'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { errorMessage } from '@/stores/apiError'
  import { transformSchemas, type TransformedSchema, formatType } from '@/utils/schemaTransformer'
  import { curationStatusColor } from '@/config/status'
  import { useConfirm } from '@/composables/useConfirm'
  import BaseDialog from '@/components/BaseDialog.vue'

  // Minimal shape of errors thrown by the API client (axios) or the stores
  interface ApiError {
    message?: string
    stack?: string
    response?: { status?: number }
  }

  type SchemaRow = TransformedSchema & { id: string; created_at?: string | null }

  const router = useRouter()
  const schemasStore = useSchemasStore()
  const logger = useLogger()

  const loading = ref(false)
  const creating = ref(false)
  const searchQuery = ref('')
  const selectedType = ref<string | null>(null)
  const selectedStatus = ref<string | null>(null)
  const createSchemaDialog = ref(false)
  const createForm = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

  // Error boundary for component-level errors
  onErrorCaptured((err, instance, info) => {
    const apiErr = err as ApiError
    logger.error('SchemaManagement error', {
      error: apiErr.message,
      stack: apiErr.stack,
      component: instance?.$options?.name || 'SchemaManagement',
      errorInfo: info
    })

    showError('An error occurred in schema management')

    // Don't propagate error up - handle it here
    return false
  })

  const newSchema = ref<{
    name: string
    description: string
    type: string | null
    version: string
  }>({
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
    { title: 'Active', value: 'active' },
    { title: 'Inactive', value: 'inactive' }
  ]

  const tableHeaders = [
    { title: 'Name', key: 'name', sortable: true },
    { title: 'Type', key: 'type', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Version', key: 'version', sortable: true },
    { title: 'Created', key: 'created_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  // Transform raw schemas from store using schemaTransformer utility (DRY principle)
  // This handles backend field mapping (schema_type -> type, is_active -> status)
  const schemas = computed(() => transformSchemas(schemasStore.schemas) as SchemaRow[])

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

  const editSchema = (schema: SchemaRow) => {
    try {
      router.push({ name: 'SchemaEditor', params: { id: schema.id } })
      logger.info('Navigate to schema editor', { schemaId: schema.id, schemaName: schema.name })
    } catch (error) {
      logger.error('Failed to navigate to schema editor', {
        schemaId: schema.id,
        error: (error as ApiError).message
      })
      showError('Failed to open schema editor')
    }
  }

  const duplicateSchema = async (schema: SchemaRow) => {
    try {
      const duplicated = await schemasStore.duplicateSchema(schema.id)
      logger.info('Schema derived', {
        originalId: schema.id,
        duplicatedId: duplicated.id,
        schemaName: schema.name
      })
      showSuccess(`Derived a new draft from "${schema.name}"`)
    } catch (error) {
      const err = error as ApiError
      logger.error('Failed to derive schema', {
        schemaId: schema.id,
        schemaName: schema.name,
        error: err.message,
        stack: err.stack
      })
      showError(errorMessage(error, 'Failed to derive schema'))
    }
  }

  const { confirm } = useConfirm()

  const deleteSchema = async (schema: SchemaRow) => {
    if (
      await confirm({
        title: `Delete "${schema.name}"?`,
        confirmText: 'Delete',
        destructive: true
      })
    ) {
      try {
        await schemasStore.deleteSchema(schema.id)
        logger.info('Schema deleted', { schemaId: schema.id, schemaName: schema.name })
        showSuccess(`Schema "${schema.name}" deleted successfully`)
      } catch (error) {
        const err = error as ApiError
        logger.error('Failed to delete schema', {
          schemaId: schema.id,
          schemaName: schema.name,
          error: err.message,
          stack: err.stack
        })
        showError(errorMessage(error, 'Failed to delete schema'))
      }
    }
  }

  const createSchema = async () => {
    if (!createForm.value) return
    const { valid } = await createForm.value.validate()
    if (!valid) return

    creating.value = true
    try {
      const { type, ...basics } = newSchema.value
      // Created as an inactive skeleton that passes backend validation; edit it in the schema editor
      await schemasStore.createSchema({
        ...basics,
        schema_type: type as string,
        field_definitions: { example_field: { type: 'string', title: 'Example field' } },
        workflow_states: {
          states: [{ name: 'draft' }, { name: 'submitted' }],
          transitions: { draft: ['submitted'], submitted: [] },
          initial_state: 'draft'
        },
        ui_configuration: { sections: [] },
        is_active: false,
        use_dynamic_form: true
      })
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
      const err = error as ApiError
      logger.error('Failed to create schema', {
        schemaName: newSchema.value.name,
        error: err.message,
        stack: err.stack
      })
      showError(errorMessage(error, 'Failed to create schema'))
    } finally {
      creating.value = false
    }
  }

  onMounted(async () => {
    loading.value = true
    try {
      await schemasStore.fetchSchemas({ active_only: false })
      logger.info('SchemaManagement mounted', { schemasCount: schemas.value.length })
    } catch (error) {
      const err = error as ApiError
      logger.error('Failed to load schemas', {
        error: err.message,
        status: err.response?.status,
        endpoint: '/api/v1/schemas',
        stack: err.stack
      })

      showError('Failed to load schemas')
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
