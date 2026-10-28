<template>
  <v-form ref="formRef" @submit.prevent="handleSubmit">
    <v-row>
      <!-- Main form content -->
      <v-col cols="12" :lg="showScoring ? 8 : 12">
        <v-card>
          <v-card-title v-if="title" class="d-flex align-center text-wrap">
            <v-icon start>mdi-form-select</v-icon>
            {{ title }}
          </v-card-title>

          <v-card-text>
            <div v-if="loading" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" />
              <div class="mt-4">Loading form schema...</div>
            </div>

            <!-- Tabbed Layout -->
            <div v-else-if="hasTabs">
              <v-tabs v-model="activeTab" show-arrows color="primary" density="comfortable">
                <v-tab v-for="tab in validTabs" :key="tab.id" :value="tab.id">
                  <v-icon v-if="tab.icon" :icon="tab.icon" start />
                  {{ tab.name }}
                  <v-chip
                    v-if="tab.show_score_badge && tabScores[tab.id] !== undefined"
                    :color="getScoreColor(tabScores[tab.id])"
                    size="small"
                    variant="flat"
                    class="ml-2"
                  >
                    {{ tabScores[tab.id] }}
                  </v-chip>
                  <!-- Error badge -->
                  <v-badge
                    v-if="tabValidationErrors[tab.id]"
                    color="error"
                    dot
                    inline
                    class="ml-2"
                  />
                </v-tab>
              </v-tabs>

              <v-window v-model="activeTab" :touch="{ left: nextTab, right: prevTab }">
                <v-window-item v-for="tab in validTabs" :key="tab.id" :value="tab.id">
                  <KeepAlive>
                    <TabContent
                      :tab="tab"
                      :schema="jsonSchema"
                      :form-data="formData"
                      :validation-result="validationResult"
                      :backend-errors="backendErrors"
                      :readonly="readonly"
                      @update:field="handleTabFieldUpdate"
                      @disease-name="fillDiseaseName"
                      @clear-backend-error="clearFieldBackendError"
                    >
                      <template #section="slotProps">
                        <slot name="section" v-bind="slotProps" />
                      </template>
                    </TabContent>
                  </KeepAlive>
                </v-window-item>
              </v-window>
            </div>

            <!-- Flat Fallback -->
            <div v-else-if="jsonSchema && jsonSchema.properties">
              <v-alert
                v-if="Object.keys(jsonSchema.properties).length === 0"
                type="info"
                variant="tonal"
              >
                This schema defines no fields
              </v-alert>
              <v-row>
                <v-col
                  v-for="(field, fieldName) in shownProperties"
                  :key="fieldName"
                  :cols="getFieldCols(field)"
                >
                  <DynamicField
                    :field-name="fieldName"
                    :field-schema="field"
                    :model-value="formData[fieldName]"
                    :validation-result="getFieldValidation(fieldName)"
                    :backend-errors="backendErrors[fieldName] || []"
                    :disabled="readonly"
                    :readonly="readonly"
                    @update:model-value="updateField(fieldName, $event)"
                    @update:disease-name="fillDiseaseName(fieldName, $event)"
                    @validate="validateField(fieldName, $event)"
                    @clear-backend-error="clearFieldBackendError(fieldName)"
                  />
                </v-col>
              </v-row>
            </div>

            <v-alert v-else-if="error" type="error" variant="tonal">
              <template #prepend>
                <v-icon>mdi-alert-circle</v-icon>
              </template>
              Failed to load form schema: {{ error }}
            </v-alert>

            <!-- Validation Errors (shown for both layouts) -->
            <v-alert
              v-if="validationResult && !validationResult.is_valid"
              type="error"
              variant="tonal"
              class="mt-4"
            >
              <template #prepend>
                <v-icon>mdi-alert-circle</v-icon>
              </template>
              <div class="font-weight-medium mb-2">Form Validation Errors</div>
              <ul class="pl-4">
                <li v-for="item in validationResult.errors" :key="`${item.field}:${item.message}`">
                  <strong>{{ labelFor(item.field) }}:</strong> {{ item.message }}
                </li>
              </ul>
            </v-alert>

            <!-- Non-field Backend Errors -->
            <v-alert
              v-if="nonFieldErrors.length > 0"
              type="error"
              variant="tonal"
              class="mt-4"
              closable
              @click:close="nonFieldErrors = []"
            >
              <template #prepend>
                <v-icon>mdi-alert-circle</v-icon>
              </template>
              <div class="font-weight-medium">Form Error</div>
              <div v-for="(msg, idx) in nonFieldErrors" :key="idx">{{ msg }}</div>
            </v-alert>

            <ValidationWarnings :messages="warningLines" />
          </v-card-text>

          <v-card-actions v-if="!readonly && !hideActions">
            <v-spacer />
            <v-btn variant="outlined" :loading="saving" :disabled="!hasChanges" @click="saveDraft">
              <v-icon start>mdi-content-save</v-icon>
              Save draft
            </v-btn>
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="submitting"
              :disabled="!canSubmit"
            >
              <v-icon start>mdi-check</v-icon>
              Submit
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Scoring sidebar -->
      <v-col v-if="showScoring" cols="12" lg="4">
        <div class="sticky-sidebar">
          <ScoreDisplay
            :score-calculations="validationResult?.score_calculations"
            :scoring-configuration="jsonSchema?.scoring_configuration"
            :loading="validationPending"
          />
        </div>
      </v-col>
    </v-row>
  </v-form>
</template>

<script setup lang="ts">
  import { ref, computed, onBeforeUnmount, onMounted, provide, watch, nextTick } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import { useValidationStore } from '@/stores'
  import DynamicField from './DynamicField.vue'
  import TabContent from './TabContent.vue'
  import ScoreDisplay from './ScoreDisplay.vue'
  import { useFormTabs } from './composables/useFormTabs'
  import { errorDetails } from './errorDetails'
  import { labelForPath } from './fieldLabels'
  import { normalizeDefinition } from './normalizeDefinition'
  import { withDeclaredDefaults } from './formDefaults'
  import { FORM_DATA, resolveField } from './conditions'
  import { toFormValidation } from './validationResult'
  import ValidationWarnings from './ValidationWarnings.vue'
  import type {
    FieldSchema,
    FieldValidation,
    FormValidationResult,
    JsonSchemaDocument
  } from './types'

  const logger = useLogger()

  /** Subset of Vuetify's VForm instance used here */
  interface FormHandle {
    validate: () => Promise<{ valid: boolean }>
  }

  type FormData = Record<string, unknown>

  const props = withDefaults(
    defineProps<{
      schemaId: string
      /** Raw methodology config (version snapshot); rendered instead of the generated JSON schema */
      definition?: Record<string, unknown>
      /** Pinned methodology version: validate against it, not the schema's latest */
      methodologyVersionId?: string
      /** The parent shows the score (e.g. the workspace's backend preview) */
      hideScoring?: boolean
      title?: string
      initialData?: FormData
      readonly?: boolean
      /** The parent renders its own Save/Submit row */
      hideActions?: boolean
    }>(),
    {
      title: 'Dynamic Form',
      initialData: () => ({}),
      readonly: false,
      hideActions: false,
      definition: undefined,
      methodologyVersionId: undefined,
      hideScoring: false
    }
  )

  const emit = defineEmits<{
    submit: [data: FormData]
    'save-draft': [data: FormData]
    'update:modelValue': [data: FormData]
    'validation-change': [result: FormValidationResult | undefined]
    'validation-pending': [pending: boolean]
  }>()

  const validationStore = useValidationStore()
  const formRef = ref<FormHandle | null>(null)
  const formData = ref<FormData>({ ...props.initialData })
  provide(FORM_DATA, formData) // nested fields resolve their conditions against the whole form
  const saving = ref(false)
  const submitting = ref(false)
  const validationPending = ref(false)
  const activeTab = ref<string | null>(null)
  const backendErrors = ref<Record<string, string[]>>({}) // { fieldPath: [error messages] }
  const nonFieldErrors = ref<string[]>([]) // Errors not mapped to specific fields

  // One debounce for every change: a validation (and its live score) per pause in typing
  let validateTimer: ReturnType<typeof setTimeout> | undefined
  let validationRevision = 0
  const scheduleValidate = () => {
    clearTimeout(validateTimer)
    validationRevision++
    validationPending.value = true
    // Invalidate in-flight replies at the edit, not 500 ms later when the next request starts.
    validationStore.clearValidationResult('form')
    validateTimer = setTimeout(validateForm, 500)
  }

  // Spinner only for the initial schema load: validation toggles store.loading on every
  // keystroke and must never unmount the form.
  const loading = computed(
    () =>
      !props.definition && validationStore.loading && !validationStore.getJsonSchema(props.schemaId)
  )
  const error = computed(() => validationStore.error)
  // The store is untyped JS; an unloaded schema is treated as an empty document
  const jsonSchema = computed<JsonSchemaDocument>(() =>
    props.definition
      ? normalizeDefinition(props.definition)
      : (validationStore.getJsonSchema(props.schemaId) ?? {})
  )
  // Flat layout: visible fields with `required_when` resolved against the form data
  const shownProperties = computed(() =>
    Object.fromEntries(
      Object.entries(jsonSchema.value.properties ?? {}).flatMap(([name, field]) => {
        const shown = resolveField(field, formData.value)
        return shown ? [[name, shown]] : []
      })
    )
  )
  const labelFor = (path?: string) => (path ? labelForPath(jsonSchema.value, path) : '')
  const warningLines = computed(() => [
    ...new Set(
      (validationResult.value?.warnings ?? []).map(w =>
        w.field ? `${labelFor(w.field)}: ${w.message}` : w.message
      )
    )
  ])
  const validationResult = computed(() => {
    const raw = validationStore.getValidationResult('form')
    return raw ? toFormValidation(raw) : undefined
  })

  const {
    hasTabs,
    validTabs,
    tabScores,
    tabValidationErrors,
    getScoreColor,
    nextTab,
    prevTab,
    findFirstInvalidTab
  } = useFormTabs({ jsonSchema, validationResult, backendErrors, activeTab })

  const showScoring = computed(() => {
    return !props.hideScoring && jsonSchema.value?.scoring_configuration?.engine != null
  })

  // Defaults are not user edits: a late server load may still replace them.
  let userEdited = false
  watch([() => JSON.stringify(props.initialData), () => props.readonly], ([next, readonly]) => {
    if (readonly || !userEdited) {
      const loaded = JSON.parse(next)
      formData.value = readonly ? loaded : withDeclaredDefaults(loaded, jsonSchema.value.properties)
    }
    if (readonly) userEdited = false
  })

  const hasChanges = computed(() => {
    return JSON.stringify(formData.value) !== JSON.stringify(props.initialData)
  })

  const canSubmit = computed(() => {
    // Block if backend validation failed
    if (validationResult.value?.is_valid === false) return false
    // Block if any backend errors present
    if (Object.keys(backendErrors.value).length > 0) return false
    // Block if no changes
    if (!hasChanges.value) return false
    return true
  })

  const clearFieldBackendError = (fieldPath: string) => {
    if (backendErrors.value[fieldPath]) {
      delete backendErrors.value[fieldPath]
    }
  }

  const validateForm = async () => {
    const revision = ++validationRevision
    validationPending.value = true
    try {
      const result = await validationStore.validateEvidence(
        formData.value,
        props.schemaId,
        'form',
        props.methodologyVersionId
      )
      if (result === null) return null // a newer validation was started: its reply wins
      handleBackendValidation(result ? toFormValidation(result) : undefined)
      return result
    } catch (err) {
      logger.error('Form validation error:', errorDetails(err))
      return null
    } finally {
      if (revision === validationRevision) validationPending.value = false
    }
  }

  const updateField = (fieldName: string, value: unknown) => {
    clearFieldBackendError(fieldName)
    userEdited = true
    formData.value[fieldName] = value
  }

  /** A picked Mondo term names the disease: fill the sibling `disease_name` when the schema has one */
  const fillDiseaseName = (fieldPath: string, name: string) => {
    const sibling = fieldPath.replace(/[^.]*$/, 'disease_name')
    let fields = jsonSchema.value.properties
    for (const key of sibling.split('.').slice(0, -1)) fields = fields?.[key]?.properties
    // A cleared term keeps the name, which the curator may have edited
    if (name && fields?.disease_name) handleTabFieldUpdate(sibling, name)
  }

  /**
   * Set nested value using dot notation path
   */
  const setNestedValue = (obj: FormData, path: string, value: unknown) => {
    const keys = path.split('.')
    const lastKey = keys.pop()!
    const target = keys.reduce<FormData>((acc, key) => {
      if (!acc[key]) acc[key] = {}
      return acc[key] as FormData
    }, obj)
    target[lastKey] = value
  }

  /**
   * Handle field updates from TabContent (supports nested paths)
   * @param fieldPath - Dot-notation field path
   * @param value - New field value
   */
  const handleTabFieldUpdate = (fieldPath: string, value: unknown) => {
    clearFieldBackendError(fieldPath)
    userEdited = true

    // Handle nested paths using dot notation
    if (fieldPath.includes('.')) {
      setNestedValue(formData.value, fieldPath, value)
    } else {
      formData.value[fieldPath] = value
    }

    // Emit update
    emit('update:modelValue', { ...formData.value })
  }

  const validateField = async (fieldName: string, value: unknown) => {
    try {
      await validationStore.validateField({
        field_name: fieldName,
        field_value: value,
        field_config: { ...jsonSchema.value.properties?.[fieldName] }
      })
    } catch (err) {
      logger.error('Field validation error:', errorDetails(err))
    }
  }

  /**
   * Process backend validation result and map errors to fields
   */
  const handleBackendValidation = (result: FormValidationResult | undefined) => {
    backendErrors.value = {}
    nonFieldErrors.value = []

    if (!result || result.is_valid) return

    // Map field-specific errors
    if (result.field_validations) {
      Object.entries(result.field_validations).forEach(([field, validation]) => {
        if (validation.errors && validation.errors.length > 0) {
          // Take first error only per CONTEXT.md decision
          backendErrors.value[field] = [validation.errors[0]!.message]
        }
      })
    }

    // Collect non-field errors (errors without field mapping)
    if (result.errors) {
      result.errors.forEach(err => {
        if (!err.field || !result.field_validations?.[err.field]) {
          nonFieldErrors.value.push(err.message)
        }
      })
    }
  }

  const getFieldValidation = (fieldName: string): FieldValidation | undefined => {
    return validationResult.value?.field_validations?.[fieldName]
  }

  const getFieldCols = (field: FieldSchema): number => {
    // Determine column width based on field type
    switch (field.type) {
      case 'boolean':
        return 12
      case 'array':
      case 'object':
      case 'evidence_table':
        return 12
      case 'text':
        if (field.multiline) return 12
        return 6
      default:
        return 6
    }
  }

  /**
   * Focus first field with validation error in current tab
   */
  const focusFirstInvalidField = () => {
    // Query for Vuetify input with error state
    const errorInput = document.querySelector<HTMLElement>(
      '.v-input--error input, .v-input--error textarea'
    )
    if (errorInput) {
      errorInput.focus()
      logger.debug('Focused first invalid field')
    }
  }

  const handleSubmit = async () => {
    submitting.value = true
    try {
      // Validate using v-form ref (VALD-06)
      const { valid } = await formRef.value!.validate()

      if (!valid) {
        // Find first tab with error and navigate to it
        const firstErrorTab = findFirstInvalidTab()
        if (firstErrorTab) {
          activeTab.value = firstErrorTab
          // Focus first invalid field after tab switch
          await nextTick()
          focusFirstInvalidField()
        }
        return
      }

      // Also check backend validation; no reply (failed or superseded) is not valid yet
      // Submit's own validation must be the newest: a pending debounced one would drop its reply
      clearTimeout(validateTimer)
      const result = await validateForm()
      if (!result) {
        nonFieldErrors.value = ['Could not validate the form. Please try again.']
        return
      }

      if (result.is_valid !== false) {
        emit('submit', formData.value)
      }
    } catch (err) {
      logger.error('Submit error:', errorDetails(err))
    } finally {
      submitting.value = false
    }
  }

  const saveDraft = async () => {
    saving.value = true
    try {
      emit('save-draft', formData.value)
    } catch (err) {
      logger.error('Save draft error:', errorDetails(err))
    } finally {
      saving.value = false
    }
  }

  // Initialize active tab when validTabs change
  watch(
    validTabs,
    tabs => {
      if (tabs.length > 0 && !activeTab.value) {
        activeTab.value = tabs[0]!.id
        logger.debug('Initialized active tab', { tabId: activeTab.value })
      }
    },
    { immediate: true }
  )

  // Watch for schema changes and generate JSON schema
  watch(
    () => props.schemaId,
    async newSchemaId => {
      if (newSchemaId && !props.definition) {
        try {
          await validationStore.generateJsonSchema(newSchemaId)
        } catch (err) {
          logger.error('Failed to generate JSON schema:', errorDetails(err))
        }
      }
    },
    { immediate: true }
  )

  // Validate (debounced) whenever the form data changes
  watch(
    formData,
    () => {
      scheduleValidate()
    },
    { deep: true }
  )

  // Emit modelValue changes for v-model support
  watch(
    formData,
    newVal => {
      emit('update:modelValue', { ...newVal })
    },
    { deep: true }
  )

  watch(validationPending, pending => emit('validation-pending', pending), { immediate: true })

  // Emit validation state changes for parent components
  watch(
    validationResult,
    result => {
      emit('validation-change', result)
    },
    { immediate: true }
  )

  // Results are kept per key: never show another record's score or validity
  validationStore.clearValidationResult('form')
  onBeforeUnmount(() => {
    validationRevision++
    clearTimeout(validateTimer)
    validationStore.clearValidationResult('form')
  })

  // Initialize before validation, including lazy tabs and asynchronously loaded schemas.
  watch(
    [jsonSchema, () => props.readonly],
    ([schema, readonly]) => {
      if (!readonly) formData.value = withDeclaredDefaults(formData.value, schema.properties)
    },
    { immediate: true }
  )

  onMounted(async () => {
    if (props.schemaId) {
      try {
        if (Object.keys(formData.value).length > 0) {
          await validateForm()
        }
      } catch (err) {
        logger.error('Failed to initialize form:', errorDetails(err))
      }
    }
  })
</script>

<style scoped>
  .sticky-sidebar {
    position: sticky;
    top: 80px;
    max-height: calc(100vh - 100px);
    overflow-y: auto;
  }

  @media (max-width: 1280px) {
    .sticky-sidebar {
      position: static;
      max-height: none;
    }
  }
</style>
