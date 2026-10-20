<template>
  <v-container fluid>
    <div v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="mt-4 text-h6">Loading schema...</div>
    </div>

    <div v-else-if="schema">
      <!-- Page Header -->
      <div class="d-flex align-center mb-6">
        <v-btn icon="mdi-arrow-left" variant="text" class="mr-4" @click="$router.back()" />
        <div>
          <h1 class="text-h4 font-weight-bold">
            {{ isEditing ? 'Edit' : 'View' }} Schema: {{ schema.name }}
          </h1>
          <p class="text-body-1 text-medium-emphasis mt-1">
            {{ schema.schema_type }} schema v{{ schema.version }}
          </p>
        </div>
        <v-spacer />
        <div class="d-flex gap-2">
          <v-btn v-if="!isEditing" color="primary" variant="outlined" @click="isEditing = true">
            <v-icon start>mdi-pencil</v-icon>
            Edit
          </v-btn>
          <v-btn
            v-if="isEditing"
            color="success"
            variant="flat"
            :loading="saving"
            @click="saveSchema"
          >
            <v-icon start>mdi-content-save</v-icon>
            Save
          </v-btn>
          <v-btn v-if="isEditing" variant="outlined" @click="cancelEdit"> Cancel </v-btn>
        </div>
      </div>

      <!-- Schema Details -->
      <v-row>
        <v-col cols="12" lg="8">
          <!-- Basic Information -->
          <v-card class="mb-6">
            <v-card-title>Basic Information</v-card-title>
            <v-card-text>
              <v-form ref="basicForm">
                <v-row>
                  <v-col cols="12" sm="6">
                    <v-text-field
                      v-model="editableSchema.name"
                      label="Schema Name"
                      variant="outlined"
                      :readonly="!isEditing"
                      :rules="isEditing ? [v => !!v || 'Name is required'] : []"
                    />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field
                      :model-value="schema.schema_type"
                      label="Schema Type"
                      variant="outlined"
                      readonly
                    />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field
                      v-model="editableSchema.version"
                      label="Version"
                      variant="outlined"
                      :readonly="!isEditing"
                      :rules="isEditing ? [v => !!v || 'Version is required'] : []"
                    />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-select
                      v-model="editableSchema.is_active"
                      :items="statusOptions"
                      label="Status"
                      variant="outlined"
                      :readonly="!isEditing"
                    />
                  </v-col>
                  <v-col cols="12">
                    <v-textarea
                      v-model="editableSchema.description"
                      label="Description"
                      variant="outlined"
                      :readonly="!isEditing"
                      rows="3"
                    />
                  </v-col>
                </v-row>
              </v-form>
            </v-card-text>
          </v-card>

          <!-- JSON Schema Definition -->
          <v-card class="mb-6">
            <v-card-title class="d-flex align-center">
              <v-icon start>mdi-code-json</v-icon>
              Field Definitions
            </v-card-title>
            <v-card-text>
              <div v-if="!isEditing" class="mb-4">
                <pre class="json-display">{{ formatJson(schema.field_definitions) }}</pre>
              </div>
              <v-textarea
                v-else
                v-model="jsonSchemaText"
                label="Field Definitions (JSON)"
                variant="outlined"
                rows="20"
                font-family="monospace"
                :error="!isValidJson"
                :error-messages="jsonError ? [jsonError] : []"
                @input="validateJson"
              />
              <div v-if="isEditing" class="text-caption text-medium-emphasis mt-2">
                Define the fields of this schema as a JSON object keyed by field name
              </div>
            </v-card-text>
          </v-card>

          <!-- Scoring Configuration -->
          <v-card v-if="schema.scoring_configuration">
            <v-card-title class="d-flex align-center">
              <v-icon start>mdi-calculator</v-icon>
              Scoring Configuration
            </v-card-title>
            <v-card-text>
              <div v-if="!isEditing">
                <pre class="json-display">{{ formatJson(schema.scoring_configuration) }}</pre>
              </div>
              <v-textarea
                v-else
                v-model="scoringConfigText"
                label="Scoring Configuration"
                variant="outlined"
                rows="10"
                font-family="monospace"
                @input="validateScoringConfig"
              />
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Sidebar -->
        <v-col cols="12" lg="4">
          <!-- Schema Statistics -->
          <v-card class="mb-6">
            <v-card-title>Statistics</v-card-title>
            <v-card-text>
              <div class="d-flex justify-space-between mb-2">
                <span>Total Fields:</span>
                <span class="font-weight-medium">{{ getFieldCount() }}</span>
              </div>
              <div class="d-flex justify-space-between mb-2">
                <span>Required Fields:</span>
                <span class="font-weight-medium">{{ getRequiredFieldCount() }}</span>
              </div>
              <div class="d-flex justify-space-between">
                <span>Last Modified:</span>
                <span class="font-weight-medium">{{ formatDate(schema.updated_at) }}</span>
              </div>
            </v-card-text>
          </v-card>

          <!-- Schema Actions -->
          <v-card>
            <v-card-title>Actions</v-card-title>
            <v-card-text>
              <div class="d-grid gap-2">
                <v-btn
                  color="info"
                  variant="outlined"
                  block
                  :loading="validating"
                  @click="validateSchema"
                >
                  <v-icon start>mdi-check-decagram</v-icon>
                  Validate Schema
                </v-btn>

                <v-btn color="secondary" variant="outlined" block @click="exportSchema">
                  <v-icon start>mdi-download</v-icon>
                  Export Schema
                </v-btn>

                <v-btn color="warning" variant="outlined" block @click="duplicateSchema">
                  <v-icon start>mdi-content-copy</v-icon>
                  Duplicate Schema
                </v-btn>

                <v-btn color="error" variant="outlined" block @click="deleteSchema">
                  <v-icon start>mdi-delete</v-icon>
                  Delete Schema
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <v-alert v-else-if="error" type="error" variant="tonal">
      <template #prepend>
        <v-icon>mdi-alert-circle</v-icon>
      </template>
      Failed to load schema: {{ error }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
  import { useLogger } from '@/composables/useLogger'

  // useLogger's JSDoc types its return as a bare Object; narrow it to the methods used here
  interface Logger {
    debug: (message: string, data?: object) => void
    info: (message: string, data?: object) => void
    warn: (message: string, data?: object) => void
    error: (message: string, data?: object) => void
  }

  const logger = useLogger() as Logger
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useSchemasStore, useValidationStore } from '@/stores'
  import type { Schema } from '@/types/api'
  import { toDuplicatePayload } from './schemaDuplicate'

  // Minimal shape of errors thrown by the API client (axios) or the stores
  interface ApiError {
    message?: string
    stack?: string
  }

  type SchemaDetail = Schema<'CurationSchema'>

  const route = useRoute()
  const router = useRouter()
  const schemasStore = useSchemasStore()
  const validationStore = useValidationStore()

  const loading = ref(false)
  const saving = ref(false)
  const validating = ref(false)
  const error = ref<string | null>(null)
  const isEditing = ref(false)
  const schema = ref<SchemaDetail | null>(null)
  const editableSchema = ref<Schema<'CurationSchemaUpdate'>>({})
  const jsonSchemaText = ref('')
  const scoringConfigText = ref('')
  const isValidJson = ref(true)
  const jsonError = ref('')
  const basicForm = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

  const schemaId = computed(() => String(route.params.id))

  const statusOptions = [
    { title: 'Active', value: true },
    { title: 'Inactive', value: false }
  ]

  const formatJson = (obj: unknown) => {
    return JSON.stringify(obj, null, 2)
  }

  const formatDate = (dateString: string | null | undefined) => {
    return new Date(dateString as string).toLocaleDateString()
  }

  const fieldDefinitions = () => Object.values(schema.value?.field_definitions ?? {})
  const getFieldCount = () => fieldDefinitions().length
  const getRequiredFieldCount = () =>
    fieldDefinitions().filter(f => (f as { required?: boolean } | null)?.required === true).length

  // Seed the edit buffer and JSON editors from a loaded schema
  const resetEditor = (source: SchemaDetail) => {
    editableSchema.value = {
      name: source.name,
      version: source.version,
      description: source.description,
      is_active: source.is_active
    }
    jsonSchemaText.value = formatJson(source.field_definitions)
    scoringConfigText.value = source.scoring_configuration
      ? formatJson(source.scoring_configuration)
      : ''
  }

  const validateJson = () => {
    try {
      JSON.parse(jsonSchemaText.value)
      isValidJson.value = true
      jsonError.value = ''
    } catch (e) {
      isValidJson.value = false
      jsonError.value = (e as Error).message
    }
  }

  const validateScoringConfig = () => {
    try {
      JSON.parse(scoringConfigText.value)
    } catch (e) {
      const err = e as Error
      logger.error('Invalid scoring config JSON:', { error: err.message, stack: err.stack })
    }
  }

  const saveSchema = async () => {
    if (!basicForm.value) return
    const { valid } = await basicForm.value.validate()
    if (!valid || !isValidJson.value) return

    saving.value = true
    try {
      schema.value = await schemasStore.updateSchema(schemaId.value, {
        ...editableSchema.value,
        field_definitions: JSON.parse(jsonSchemaText.value),
        scoring_configuration: scoringConfigText.value ? JSON.parse(scoringConfigText.value) : null
      })
      isEditing.value = false
    } catch (error) {
      const err = error as ApiError
      logger.error('Failed to save schema:', { error: err.message, stack: err.stack })
    } finally {
      saving.value = false
    }
  }

  const cancelEdit = () => {
    if (schema.value) resetEditor(schema.value)
    isEditing.value = false
  }

  const validateSchema = async () => {
    if (!schema.value) return
    validating.value = true
    try {
      const result = await validationStore.validateSchema(schema.value)
      logger.info('Schema validation result:', result)
    } catch (error) {
      const err = error as ApiError
      logger.error('Schema validation failed:', { error: err.message, stack: err.stack })
    } finally {
      validating.value = false
    }
  }

  const exportSchema = () => {
    if (!schema.value) return
    const blob = new Blob([JSON.stringify(schema.value, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${schema.value.name}-v${schema.value.version}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const duplicateSchema = async () => {
    if (!schema.value) return
    try {
      const duplicated = await schemasStore.createSchema(toDuplicatePayload(schema.value))
      router.push({ name: 'SchemaEditor', params: { id: duplicated.id } })
    } catch (error) {
      const err = error as ApiError
      logger.error('Failed to duplicate schema:', { error: err.message, stack: err.stack })
    }
  }

  const deleteSchema = async () => {
    if (!schema.value) return
    if (confirm(`Are you sure you want to delete "${schema.value.name}"?`)) {
      try {
        await schemasStore.deleteSchema(schemaId.value)
        router.push({ name: 'SchemaManagement' })
      } catch (error) {
        const err = error as ApiError
        logger.error('Failed to delete schema:', { error: err.message, stack: err.stack })
      }
    }
  }

  const loadSchema = async () => {
    loading.value = true
    error.value = null

    try {
      const schemaData = await schemasStore.fetchSchemaById(schemaId.value)
      schema.value = schemaData
      resetEditor(schemaData)
    } catch (err) {
      const apiErr = err as ApiError
      error.value = apiErr.message || 'Failed to load schema'
      logger.error('Failed to load schema:', { error: apiErr.message, stack: apiErr.stack })
    } finally {
      loading.value = false
    }
  }

  watch(
    () => route.params.id,
    newId => {
      if (newId) {
        loadSchema()
      }
    }
  )

  onMounted(() => {
    loadSchema()
  })
</script>

<style scoped>
  .json-display {
    background-color: rgba(var(--v-theme-surface-variant), 0.1);
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: 4px;
    padding: 16px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 14px;
  }

  .d-grid {
    display: grid;
  }

  .gap-2 {
    gap: 8px;
  }
</style>
