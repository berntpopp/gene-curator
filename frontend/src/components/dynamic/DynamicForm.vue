<template>
  <v-form ref="formRef" @submit.prevent="handleSubmit">
    <v-card>
      <v-card-title class="d-flex align-center">
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
            </v-tab>
          </v-tabs>

          <v-window v-model="activeTab">
            <v-window-item v-for="tab in validTabs" :key="tab.id" :value="tab.id">
              <KeepAlive>
                <TabContent
                  :tab="tab"
                  :schema="jsonSchema"
                  :form-data="formData"
                  :validation-result="validationResult"
                  :readonly="readonly"
                  @update:field="handleTabFieldUpdate"
                />
              </KeepAlive>
            </v-window-item>
          </v-window>
        </div>

        <!-- Flat Fallback -->
        <div v-else-if="jsonSchema && jsonSchema.properties">
          <v-row>
            <v-col
              v-for="(field, fieldName) in jsonSchema.properties"
              :key="fieldName"
              :cols="getFieldCols(field)"
            >
              <DynamicField
                :field-name="fieldName"
                :field-schema="field"
                :model-value="formData[fieldName]"
                :validation-result="getFieldValidation(fieldName)"
                :disabled="readonly"
                @update:model-value="updateField(fieldName, $event)"
                @validate="validateField(fieldName, $event)"
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
            <li v-for="error in validationResult.errors" :key="error.field">
              <strong>{{ error.field }}:</strong> {{ error.message }}
            </li>
          </ul>
        </v-alert>

        <v-alert
          v-if="validationResult && validationResult.warnings?.length"
          type="warning"
          variant="tonal"
          class="mt-4"
        >
          <template #prepend>
            <v-icon>mdi-alert</v-icon>
          </template>
          <div class="font-weight-medium mb-2">Form Warnings</div>
          <ul class="pl-4">
            <li v-for="warning in validationResult.warnings" :key="warning.field">
              <strong>{{ warning.field }}:</strong> {{ warning.message }}
            </li>
          </ul>
        </v-alert>

        <div v-if="validationResult && validationResult.score_calculations">
          <v-divider class="my-6" />
          <h3 class="text-h6 mb-4 d-flex align-center">
            <v-icon start>mdi-calculator</v-icon>
            Live Scoring
          </h3>
          <v-row>
            <v-col
              v-for="(score, category) in validationResult.score_calculations"
              :key="category"
              cols="12"
              sm="6"
              md="4"
            >
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h4 text-primary font-weight-bold">{{ score }}</div>
                  <div class="text-caption text-uppercase text-medium-emphasis">
                    {{ formatScoreCategory(category) }}
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="secondary"
          variant="outlined"
          :loading="saving"
          :disabled="!hasChanges"
          @click="saveDraft"
        >
          <v-icon start>mdi-content-save</v-icon>
          Save Draft
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
  </v-form>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, onMounted, watch } from 'vue'
  import { useValidationStore } from '@/stores'
  import DynamicField from './DynamicField.vue'
  import TabContent from './TabContent.vue'

  const props = defineProps({
    schemaId: {
      type: String,
      required: true
    },
    title: {
      type: String,
      default: 'Dynamic Form'
    },
    initialData: {
      type: Object,
      default: () => ({})
    },
    readonly: {
      type: Boolean,
      default: false
    }
  })

  const emit = defineEmits(['submit', 'save-draft', 'update:modelValue', 'validation-change'])

  const validationStore = useValidationStore()
  const formRef = ref(null)
  const formData = ref({ ...props.initialData })
  const saving = ref(false)
  const submitting = ref(false)
  const activeTab = ref(null)

  const loading = computed(() => validationStore.loading)
  const error = computed(() => validationStore.error)
  const jsonSchema = computed(() => validationStore.getJsonSchema(props.schemaId))
  const validationResult = computed(() => validationStore.getValidationResult('form'))

  const hasChanges = computed(() => {
    return JSON.stringify(formData.value) !== JSON.stringify(props.initialData)
  })

  const canSubmit = computed(() => {
    return validationResult.value?.is_valid !== false && hasChanges.value
  })

  const hasTabs = computed(() => {
    const layout = jsonSchema.value?.ui_configuration?.layout

    if (!layout) {
      logger.debug('No ui_configuration.layout - using flat rendering')
      return false
    }

    if (layout.type !== 'tabs') {
      logger.debug('Layout type not tabs - using flat rendering', { type: layout.type })
      return false
    }

    if (!Array.isArray(layout.tabs) || layout.tabs.length === 0) {
      logger.warn('Invalid tabs configuration - using flat rendering', { layout })
      return false
    }

    return true
  })

  const validTabs = computed(() => {
    if (!hasTabs.value) return []

    const tabs = jsonSchema.value.ui_configuration.layout.tabs.filter(tab => {
      // Validate tab structure
      if (!tab.id || !tab.name) {
        logger.warn('Tab missing required fields', { tab })
        return false
      }

      if (!Array.isArray(tab.sections) || tab.sections.length === 0) {
        logger.warn('Tab has no sections', { tabId: tab.id })
        return false
      }

      return true
    })

    // If fewer than 2 valid tabs, fallback to flat rendering
    if (tabs.length < 2) {
      logger.warn('Fewer than 2 valid tabs - using flat rendering', { validCount: tabs.length })
      return []
    }

    return tabs
  })

  const updateField = (fieldName, value) => {
    formData.value[fieldName] = value
    // Trigger validation debounced
    clearTimeout(updateField.timeout)
    updateField.timeout = setTimeout(() => {
      validateForm()
    }, 500)
  }

  /**
   * Set nested value using dot notation path
   * @param {Object} obj - Target object
   * @param {string} path - Dot-notation path
   * @param {*} value - Value to set
   */
  const setNestedValue = (obj, path, value) => {
    const keys = path.split('.')
    const lastKey = keys.pop()
    const target = keys.reduce((acc, key) => {
      if (!acc[key]) acc[key] = {}
      return acc[key]
    }, obj)
    target[lastKey] = value
  }

  /**
   * Handle field updates from TabContent (supports nested paths)
   * @param {string} fieldPath - Dot-notation field path
   * @param {*} value - New field value
   */
  const handleTabFieldUpdate = (fieldPath, value) => {
    // Handle nested paths using dot notation
    if (fieldPath.includes('.')) {
      setNestedValue(formData.value, fieldPath, value)
    } else {
      formData.value[fieldPath] = value
    }

    // Emit update
    emit('update:modelValue', { ...formData.value })

    // Trigger validation debounced
    clearTimeout(handleTabFieldUpdate.timeout)
    handleTabFieldUpdate.timeout = setTimeout(() => {
      validateForm()
    }, 500)
  }

  const validateField = async (fieldName, value) => {
    try {
      await validationStore.validateField({
        field_name: fieldName,
        field_value: value,
        schema_id: props.schemaId
      })
    } catch (error) {
      logger.error('Field validation error:', { error: error.message, stack: error.stack })
    }
  }

  const validateForm = async () => {
    try {
      await validationStore.validateEvidence(formData.value, props.schemaId, 'form')
    } catch (error) {
      logger.error('Form validation error:', { error: error.message, stack: error.stack })
    }
  }

  const getFieldValidation = fieldName => {
    return validationResult.value?.field_validations?.[fieldName]
  }

  const getFieldCols = field => {
    // Determine column width based on field type
    switch (field.type) {
      case 'boolean':
        return 12
      case 'array':
      case 'object':
        return 12
      case 'text':
        if (field.multiline) return 12
        return 6
      default:
        return 6
    }
  }

  const formatScoreCategory = category => {
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const handleSubmit = async () => {
    submitting.value = true
    try {
      // Final validation
      await validateForm()

      if (validationResult.value?.is_valid !== false) {
        emit('submit', formData.value)
      }
    } catch (error) {
      logger.error('Submit error:', { error: error.message, stack: error.stack })
    } finally {
      submitting.value = false
    }
  }

  const saveDraft = async () => {
    saving.value = true
    try {
      emit('save-draft', formData.value)
    } catch (error) {
      logger.error('Save draft error:', { error: error.message, stack: error.stack })
    } finally {
      saving.value = false
    }
  }

  // Initialize active tab when validTabs change
  watch(
    validTabs,
    tabs => {
      if (tabs.length > 0 && !activeTab.value) {
        activeTab.value = tabs[0].id
        logger.debug('Initialized active tab', { tabId: activeTab.value })
      }
    },
    { immediate: true }
  )

  // Watch for schema changes and generate JSON schema
  watch(
    () => props.schemaId,
    async newSchemaId => {
      if (newSchemaId) {
        try {
          await validationStore.generateJsonSchema(newSchemaId)
        } catch (error) {
          logger.error('Failed to generate JSON schema:', {
            error: error.message,
            stack: error.stack
          })
        }
      }
    },
    { immediate: true }
  )

  // Initial validation when form data changes
  watch(
    formData,
    () => {
      if (Object.keys(formData.value).length > 0) {
        validateForm()
      }
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

  // Emit validation state changes for parent components
  watch(
    validationResult,
    result => {
      emit('validation-change', result)
    },
    { immediate: true }
  )

  onMounted(async () => {
    if (props.schemaId) {
      try {
        await validationStore.generateJsonSchema(props.schemaId)
        if (Object.keys(formData.value).length > 0) {
          await validateForm()
        }
      } catch (error) {
        logger.error('Failed to initialize form:', { error: error.message, stack: error.stack })
      }
    }
  })
</script>
