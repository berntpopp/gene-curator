<template>
  <v-container fluid>
    <div v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="mt-4 text-title-large">Loading schema...</div>
    </div>

    <div v-else-if="schema">
      <!-- Page Header -->
      <div class="d-flex align-center mb-6">
        <v-btn
          aria-label="Go back"
          icon="mdi-arrow-left"
          variant="text"
          class="mr-4"
          @click="router.push({ name: 'SchemaManagement' })"
        />
        <div>
          <h1 class="page-title text-headline-large font-weight-bold">
            {{ isEditing ? 'Edit' : 'View' }} Schema: {{ schema.name }}
          </h1>
          <p class="text-body-large text-medium-emphasis mt-1">
            {{ schema.schema_type }} schema {{ formatVersion(schema.version) }}
          </p>
        </div>
        <v-spacer />
        <div class="d-flex ga-2">
          <v-btn v-if="!isEditing" color="primary" variant="outlined" @click="isEditing = true">
            <v-icon start>mdi-pencil</v-icon>
            Edit
          </v-btn>
          <v-btn
            v-if="isEditing"
            color="success"
            variant="flat"
            :loading="saving"
            :disabled="hasJsonErrors"
            :title="hasJsonErrors ? 'Fix the JSON marked in red before saving' : undefined"
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
        <!-- The scoring tables need the full width; the sidebar moves below them -->
        <v-col cols="12" :lg="tab === 'scoring' ? 12 : 8">
          <!-- Basic Information -->
          <v-card class="mb-6">
            <v-card-title>Basic information</v-card-title>
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

          <v-alert
            v-if="validation"
            :type="validation.is_valid ? 'success' : 'error'"
            variant="tonal"
            class="mb-6"
            closable
            @click:close="validation = null"
          >
            <div v-if="validation.is_valid">Schema is valid</div>
            <ul v-if="validation.errors?.length" class="ps-4">
              <li v-for="e in validation.errors" :key="e">{{ e }}</li>
            </ul>
            <ul v-if="validation.warnings?.length" class="ps-4">
              <li v-for="(w, i) in validation.warnings" :key="i">Warning: {{ w }}</li>
            </ul>
          </v-alert>

          <v-card class="mb-6">
            <v-tabs v-model="tab" color="primary" show-arrows>
              <v-tab value="fields" prepend-icon="mdi-form-select">
                Fields
                <v-badge v-if="fieldProblems" :content="fieldProblems" color="error" inline />
              </v-tab>
              <v-tab value="workflow" prepend-icon="mdi-sitemap">
                Workflow
                <v-badge v-if="workflowProblems" :content="workflowProblems" color="error" inline />
              </v-tab>
              <v-tab value="preview" prepend-icon="mdi-eye">Preview</v-tab>
              <v-tab value="scoring" prepend-icon="mdi-calculator">
                Scoring
                <v-badge v-if="jsonErrors.scoring_code" color="error" dot inline class="ml-2" />
                <v-badge
                  v-else-if="scoringProblems"
                  :content="scoringProblems"
                  color="error"
                  inline
                />
              </v-tab>
              <v-tab value="advanced" prepend-icon="mdi-code-json">
                Advanced JSON
                <v-badge v-if="advancedErrors" color="error" dot inline class="ml-2" />
              </v-tab>
            </v-tabs>
            <v-divider />
            <v-card-text>
              <v-window v-model="tab">
                <v-window-item value="fields">
                  <FieldsEditor
                    :model-value="draft.field_definitions"
                    :ui-configuration="draft.ui_configuration"
                    :references="{
                      scoring_configuration: draft.scoring_configuration,
                      validation_rules: draft.validation_rules
                    }"
                    :published="published"
                    :readonly="!isEditing"
                    :diagnostics="checks.diagnostics.value"
                    @update:model-value="v => (draft.field_definitions = v)"
                    @update:ui-configuration="v => (draft.ui_configuration = v)"
                  />
                </v-window-item>
                <v-window-item value="workflow">
                  <WorkflowStagesEditor
                    :model-value="draft.workflow_states"
                    :diagnostics="checks.diagnostics.value"
                    :has-scoring="!!draft.scoring_configuration"
                    :readonly="!isEditing"
                    @update:model-value="v => setBlock('workflow_states', v)"
                    @open="builder => (tab = builder)"
                  />
                </v-window-item>
                <v-window-item value="preview">
                  <DynamicForm
                    v-if="tab === 'preview'"
                    :schema-id="schemaId"
                    :definition="draft"
                    title=""
                    hide-actions
                    hide-scoring
                  />
                </v-window-item>
                <v-window-item value="scoring" eager>
                  <PointModelBuilder
                    v-if="isEditing"
                    :model-value="scoringConfig"
                    :field-definitions="draft.field_definitions"
                    :definition="draft"
                    :schema-id="schemaId"
                    @update:model-value="v => setBlock('scoring_configuration', v)"
                    @error="message => (jsonErrors.scoring_code = message)"
                  />
                  <JsonBlockEditor
                    v-else
                    :model-value="draft.scoring_configuration"
                    label="Scoring configuration (JSON)"
                    hint="Edit the schema to change scoring"
                    nullable
                    readonly
                  />
                </v-window-item>
                <v-window-item value="advanced" eager>
                  <AdvancedJson
                    :model-value="draft"
                    :errors="jsonErrors"
                    :readonly="!isEditing"
                    @update="setBlock"
                    @error="(key, message) => (jsonErrors[key] = message)"
                  />
                </v-window-item>
              </v-window>
            </v-card-text>
          </v-card>

          <!-- Validator report of the unsaved draft; each builder also shows its own inline -->
          <v-expansion-panels v-if="checks.diagnostics.value.length" class="mb-6">
            <v-expansion-panel data-testid="draft-diagnostics">
              <v-expansion-panel-title>
                Problems in this draft ({{ checks.diagnostics.value.length }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-list density="compact">
                  <v-list-item
                    v-for="(d, i) in checks.diagnostics.value"
                    :key="i"
                    :prepend-icon="d.severity === 'error' ? 'mdi-alert-circle' : 'mdi-alert'"
                    :base-color="d.severity === 'error' ? 'error' : 'warning'"
                    :title="d.message"
                    :subtitle="d.field"
                  />
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>

        <!-- Sidebar -->
        <v-col cols="12" :lg="tab === 'scoring' ? 12 : 4">
          <!-- Schema Statistics -->
          <v-card class="mb-6">
            <v-card-title>Statistics</v-card-title>
            <v-card-text>
              <div class="d-flex justify-space-between mb-2">
                <span>Total Fields:</span>
                <span class="font-weight-medium">{{ getFieldCount() }}</span>
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
              <div class="d-grid ga-2">
                <v-btn
                  color="info"
                  variant="outlined"
                  block
                  :loading="validating"
                  @click="validateSchema"
                >
                  <v-icon start>mdi-check-decagram</v-icon>
                  Validate saved schema
                </v-btn>

                <v-btn
                  color="primary"
                  variant="flat"
                  block
                  :disabled="isEditing"
                  aria-describedby="publish-caption"
                  @click="publishOpen = true"
                >
                  <v-icon start>mdi-send</v-icon>
                  Publish version
                </v-btn>
                <div
                  v-if="isEditing"
                  id="publish-caption"
                  class="text-body-small text-medium-emphasis"
                >
                  Save or cancel your edits to publish.
                </div>

                <v-btn variant="outlined" block @click="exportSchema">
                  <v-icon start>mdi-download</v-icon>
                  Export schema
                </v-btn>

                <v-btn color="warning" variant="outlined" block @click="duplicateSchema">
                  <v-icon start>mdi-content-copy</v-icon>
                  Derive
                </v-btn>

                <v-btn color="error" variant="outlined" block @click="deleteSchema">
                  <v-icon start>mdi-delete</v-icon>
                  Delete schema
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <PublishDialog
      v-if="schema"
      v-model="publishOpen"
      :schema-id="schemaId"
      :schema-name="schema.name"
    />

    <v-alert v-else-if="error" type="error" variant="tonal">
      <template #prepend>
        <v-icon>mdi-alert-circle</v-icon>
      </template>
      Failed to load schema: {{ error }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
  import { formatDate, formatVersion } from '@/utils/format'
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useSchemasStore } from '@/stores'
  import { errorMessage } from '@/stores/apiError'
  import { showError, showWarning } from '@/composables/useNotifications'
  import type { Schema } from '@/types/api'
  import { useConfirm } from '@/composables/useConfirm'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import FieldsEditor from '@/components/schema-editor/FieldsEditor.vue'
  import AdvancedJson from '@/components/schema-editor/AdvancedJson.vue'
  import JsonBlockEditor from '@/components/schema-editor/JsonBlockEditor.vue'
  import PublishDialog from '@/components/schema-editor/PublishDialog.vue'
  import PointModelBuilder from '@/components/schema-editor/scoring/PointModelBuilder.vue'
  import WorkflowStagesEditor from '@/components/schema-editor/WorkflowStagesEditor.vue'
  import { usePointModelChecks } from '@/components/schema-editor/scoring/usePointModelChecks'
  import type { ScoringConfig } from '@/components/schema-editor/scoring/pointModel'
  import { clone, fieldIds, readLayout, type BlockKey } from '@/components/schema-editor/fieldModel'

  interface ApiError {
    message?: string
    stack?: string
    response?: { status?: number }
  }

  type SchemaDetail = Schema<'CurationSchema'>
  type ValidationResult = Schema<'SchemaValidationResult'>
  type Blocks = Record<BlockKey, unknown> & { field_definitions: Record<string, unknown> }

  const BLOCK_KEYS: BlockKey[] = [
    'field_definitions',
    'ui_configuration',
    'validation_rules',
    'scoring_configuration',
    'workflow_states'
  ]

  const route = useRoute()
  const router = useRouter()
  const schemasStore = useSchemasStore()

  const loading = ref(false)
  const saving = ref(false)
  const validating = ref(false)
  const error = ref<string | null>(null)
  const isEditing = ref(false)
  const schema = ref<SchemaDetail | null>(null)
  const editableSchema = ref<Partial<Schema<'CurationSchemaUpdate'>>>({})
  // The five JSON blocks being edited; every tab edits this one draft
  const draft = ref<Blocks>({ field_definitions: {} } as Blocks)
  // Parse error per JSON editor ('' = valid); Save is blocked while any is set
  const jsonErrors = ref<Record<string, string>>({})
  const tab = ref('fields')
  const publishOpen = ref(false)
  const published = ref(false)
  const validation = ref<ValidationResult | null>(null)
  const basicForm = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

  const schemaId = computed(() => String(route.params.id))
  const scoringConfig = computed(() => draft.value.scoring_configuration as ScoringConfig | null)
  const hasJsonErrors = computed(() => Object.values(jsonErrors.value).some(Boolean))
  const advancedErrors = computed(() =>
    Object.entries(jsonErrors.value).some(([key, message]) => key !== 'scoring_code' && message)
  )

  // The validator's report of the unsaved draft, shown inline and as tab badges (#282)
  const checks = usePointModelChecks()
  const fieldProblems = computed(() =>
    checks.count('field_definitions', 'ui_configuration', 'validation_rules')
  )
  const workflowProblems = computed(() => checks.count('workflow_states'))
  const scoringProblems = computed(() => checks.count('scoring_configuration'))
  let checkTimer: ReturnType<typeof setTimeout> | undefined
  watch(
    draft,
    value => {
      clearTimeout(checkTimer)
      checkTimer = setTimeout(() => checks.checkDraft(value), 600)
    },
    { deep: true }
  )
  onBeforeUnmount(() => clearTimeout(checkTimer))

  const statusOptions = [
    { title: 'Active', value: true },
    { title: 'Inactive', value: false }
  ]

  const setBlock = (key: BlockKey, value: unknown) => {
    ;(draft.value as Record<BlockKey, unknown>)[key] = value
  }

  const getFieldCount = () => fieldIds(readLayout(draft.value.field_definitions)).length

  // Seed the edit buffer and the draft blocks from a loaded schema
  const resetEditor = (source: SchemaDetail) => {
    editableSchema.value = {
      name: source.name,
      version: source.version,
      description: source.description,
      is_active: source.is_active
    }
    draft.value = clone(
      Object.fromEntries(BLOCK_KEYS.map(key => [key, source[key] ?? null]))
    ) as Blocks
    draft.value.field_definitions ??= {}
    jsonErrors.value = {}
  }

  const saveSchema = async () => {
    if (!basicForm.value) return
    const { valid } = await basicForm.value.validate()
    if (!valid || hasJsonErrors.value) return

    saving.value = true
    try {
      // lock_version: a copy saved by someone else meanwhile is refused (409), not overwritten
      schema.value = await schemasStore.updateSchema(schemaId.value, {
        ...editableSchema.value,
        ...(draft.value as Partial<Schema<'CurationSchemaUpdate'>>),
        lock_version: schema.value?.lock_version ?? 0
      })
      resetEditor(schema.value)
      isEditing.value = false
      validation.value = null
    } catch (error) {
      const err = error as ApiError
      if (err.response?.status === 409) return await keepDraftAfterConflict()
      logger.error('Failed to save schema:', { error: err.message, stack: err.stack })
      showError(errorMessage(error, 'Failed to save schema'))
    } finally {
      saving.value = false
    }
  }

  /** Their save wins the row, not the draft: load their version (its lock_version) under the
   * draft, so Save replaces it and Cancel shows it */
  const keepDraftAfterConflict = async () => {
    try {
      schema.value = await schemasStore.fetchSchemaById(schemaId.value)
      showWarning(
        'Someone else saved this schema. Your draft is kept: Save again to replace their version, or Cancel to load theirs.'
      )
    } catch (error) {
      showError(errorMessage(error, 'Someone else saved this schema; reloading it failed'))
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
      const result = await schemasStore.validateSchema(schemaId.value)
      validation.value = result
    } catch (error) {
      const err = error as ApiError
      logger.error('Schema validation failed:', { error: err.message, stack: err.stack })
      showError(errorMessage(error, 'Schema validation failed'))
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
      const { derived } = await schemasStore.duplicateSchema(schemaId.value)
      router.push({ name: 'SchemaEditor', params: { id: derived.id } })
    } catch (error) {
      const err = error as ApiError
      logger.error('Failed to derive schema:', { error: err.message, stack: err.stack })
      showError(errorMessage(error, 'Failed to derive schema'))
    }
  }

  const { confirm } = useConfirm()

  const deleteSchema = async () => {
    if (!schema.value) return
    if (
      await confirm({
        title: `Delete "${schema.value.name}"?`,
        confirmText: 'Delete',
        destructive: true
      })
    ) {
      try {
        await schemasStore.deleteSchema(schemaId.value)
        router.push({ name: 'SchemaManagement' })
      } catch (error) {
        const err = error as ApiError
        logger.error('Failed to delete schema:', { error: err.message, stack: err.stack })
        showError(errorMessage(error, 'Failed to delete schema'))
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
      // Renames warn harder once records may hold values under the old id; creation's own
      // version 1 of a never-activated schema holds none (monkey B16)
      // Assume published until the versions answer, so an early Edit still warns on rename
      published.value = true
      schemasStore
        .fetchVersions(schemaId.value)
        .then(versions => (published.value = versions.length > 1 || !!schemaData.is_active))
        .catch(() => (published.value = false))
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
  .d-grid {
    display: grid;
  }
</style>
