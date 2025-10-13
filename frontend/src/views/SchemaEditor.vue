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
            {{ schema.type }} schema v{{ schema.version }}
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
                    <v-select
                      v-model="editableSchema.type"
                      :items="schemaTypes"
                      label="Schema Type"
                      variant="outlined"
                      :readonly="!isEditing"
                      :rules="isEditing ? [v => !!v || 'Type is required'] : []"
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
                      v-model="editableSchema.status"
                      :items="statusOptions"
                      label="Status"
                      variant="outlined"
                      :readonly="!isEditing"
                      :rules="isEditing ? [v => !!v || 'Status is required'] : []"
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
              JSON Schema Definition
            </v-card-title>
            <v-card-text>
              <div v-if="!isEditing" class="mb-4">
                <pre class="json-display">{{ formatJson(editableSchema.json_schema) }}</pre>
              </div>
              <v-textarea
                v-else
                v-model="jsonSchemaText"
                label="JSON Schema"
                variant="outlined"
                rows="20"
                font-family="monospace"
                :error="!isValidJson"
                :error-messages="jsonError ? [jsonError] : []"
                @input="validateJson"
              />
              <div v-if="isEditing" class="text-caption text-medium-emphasis mt-2">
                Define the field structure and validation rules using JSON Schema format
              </div>
            </v-card-text>
          </v-card>

          <!-- Scoring Configuration -->
          <v-card v-if="editableSchema.scoring_config">
            <v-card-title class="d-flex align-center">
              <v-icon start>mdi-calculator</v-icon>
              Scoring Configuration
            </v-card-title>
            <v-card-text>
              <div v-if="!isEditing">
                <pre class="json-display">{{ formatJson(editableSchema.scoring_config) }}</pre>
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
              <div class="d-flex justify-space-between mb-2">
                <span>Active Curations:</span>
                <span class="font-weight-medium">{{ schema.usage_count || 0 }}</span>
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

                <v-btn
                  color="error"
                  variant="outlined"
                  block
                  :disabled="schema.usage_count > 0"
                  @click="deleteSchema"
                >
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

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useSchemasStore } from '@/stores'

  const route = useRoute()
  const router = useRouter()
  const schemasStore = useSchemasStore()

  const loading = ref(false)
  const saving = ref(false)
  const validating = ref(false)
  const error = ref(null)
  const isEditing = ref(false)
  const schema = ref(null)
  const editableSchema = ref({})
  const jsonSchemaText = ref('')
  const scoringConfigText = ref('')
  const isValidJson = ref(true)
  const jsonError = ref('')
  const basicForm = ref(null)

  const schemaId = computed(() => route.params.id)

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

  const formatJson = obj => {
    return JSON.stringify(obj, null, 2)
  }

  const formatDate = dateString => {
    return new Date(dateString).toLocaleDateString()
  }

  const getFieldCount = () => {
    if (!editableSchema.value.json_schema?.properties) return 0
    return Object.keys(editableSchema.value.json_schema.properties).length
  }

  const getRequiredFieldCount = () => {
    if (!editableSchema.value.json_schema?.required) return 0
    return editableSchema.value.json_schema.required.length
  }

  const validateJson = () => {
    try {
      JSON.parse(jsonSchemaText.value)
      isValidJson.value = true
      jsonError.value = ''
    } catch (e) {
      isValidJson.value = false
      jsonError.value = e.message
    }
  }

  const validateScoringConfig = () => {
    try {
      JSON.parse(scoringConfigText.value)
    } catch (e) {
      logger.error('Invalid scoring config JSON:', { error: e.message, stack: e.stack })
    }
  }

  const saveSchema = async () => {
    const { valid } = await basicForm.value.validate()
    if (!valid || !isValidJson.value) return

    saving.value = true
    try {
      // Parse JSON fields
      editableSchema.value.json_schema = JSON.parse(jsonSchemaText.value)
      if (scoringConfigText.value) {
        editableSchema.value.scoring_config = JSON.parse(scoringConfigText.value)
      }

      await schemasStore.updateSchema(schemaId.value, editableSchema.value)
      schema.value = { ...editableSchema.value }
      isEditing.value = false
    } catch (error) {
      logger.error('Failed to save schema:', { error: error.message, stack: error.stack })
    } finally {
      saving.value = false
    }
  }

  const cancelEdit = () => {
    editableSchema.value = { ...schema.value }
    jsonSchemaText.value = formatJson(schema.value.json_schema)
    scoringConfigText.value = schema.value.scoring_config
      ? formatJson(schema.value.scoring_config)
      : ''
    isEditing.value = false
  }

  const validateSchema = async () => {
    validating.value = true
    try {
      const result = await schemasStore.validateSchema(schemaId.value)
      logger.info('Schema validation result:', result)
      // Show validation results to user
    } catch (error) {
      logger.error('Schema validation failed:', { error: error.message, stack: error.stack })
    } finally {
      validating.value = false
    }
  }

  const exportSchema = () => {
    const blob = new Blob([JSON.stringify(schema.value, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${schema.value.name}-v${schema.value.version}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const duplicateSchema = async () => {
    try {
      const duplicated = await schemasStore.duplicateSchema(schemaId.value)
      router.push({ name: 'SchemaEditor', params: { id: duplicated.id } })
    } catch (error) {
      logger.error('Failed to duplicate schema:', { error: error.message, stack: error.stack })
    }
  }

  const deleteSchema = async () => {
    if (confirm(`Are you sure you want to delete "${schema.value.name}"?`)) {
      try {
        await schemasStore.deleteSchema(schemaId.value)
        router.push({ name: 'SchemaManagement' })
      } catch (error) {
        logger.error('Failed to delete schema:', { error: error.message, stack: error.stack })
      }
    }
  }

  const loadSchema = async () => {
    loading.value = true
    error.value = null

    try {
      const schemaData = await schemasStore.fetchSchemaById(schemaId.value)
      schema.value = schemaData
      editableSchema.value = { ...schemaData }
      jsonSchemaText.value = formatJson(schemaData.json_schema)
      scoringConfigText.value = schemaData.scoring_config
        ? formatJson(schemaData.scoring_config)
        : ''
    } catch (err) {
      error.value = err.message || 'Failed to load schema'
      logger.error('Failed to load schema:', { error: err.message, stack: err.stack })
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
