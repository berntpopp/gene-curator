<template>
  <v-form ref="formRef" @submit.prevent="handleSubmit">
    <v-row>
      <!-- Main form content -->
      <v-col cols="12" :lg="showScoring ? 8 : 12">
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
                      @clear-backend-error="clearFieldBackendError"
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
                    :backend-errors="backendErrors[fieldName] || []"
                    :disabled="readonly"
                    @update:model-value="updateField(fieldName, $event)"
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
                <li v-for="error in validationResult.errors" :key="error.field">
                  <strong>{{ error.field }}:</strong> {{ error.message }}
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
      </v-col>

      <!-- Scoring sidebar -->
      <v-col v-if="showScoring" cols="12" lg="4">
        <div class="sticky-sidebar">
          <ScoreDisplay
            :score-calculations="validationResult?.score_calculations"
            :scoring-configuration="jsonSchema?.scoring_configuration"
            :loading="validating"
          />
        </div>
      </v-col>
    </v-row>
  </v-form>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, onMounted, watch, nextTick } from 'vue'
  import { useValidationStore } from '@/stores'
  import DynamicField from './DynamicField.vue'
  import TabContent from './TabContent.vue'
  import ScoreDisplay from './ScoreDisplay.vue'

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
  const validating = ref(false)
  const activeTab = ref(null)
  const backendErrors = ref({}) // { fieldPath: [error messages] }
  const nonFieldErrors = ref([]) // Errors not mapped to specific fields

  const loading = computed(() => validationStore.loading)
  const error = computed(() => validationStore.error)
  const jsonSchema = computed(() => validationStore.getJsonSchema(props.schemaId))
  const validationResult = computed(() => validationStore.getValidationResult('form'))

  const showScoring = computed(() => {
    return jsonSchema.value?.scoring_configuration?.engine != null
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

  /**
   * Calculate score for each tab with show_score_badge enabled
   * Maps tab IDs to their corresponding score from validationResult
   */
  const tabScores = computed(() => {
    if (!validationResult.value?.score_calculations) return {}

    const scores = {}
    validTabs.value.forEach(tab => {
      if (tab.show_score_badge) {
        scores[tab.id] = calculateTabScore(tab)
      }
    })

    return scores
  })

  /**
   * Map tab ID to score calculation field
   * Convention: tab.id maps to score_calculations[tab.id + '_score']
   * Special cases: genetic -> genetic_evidence_score, experimental -> experimental_evidence_score
   */
  function calculateTabScore(tab) {
    const scoreCalcs = validationResult.value?.score_calculations
    if (!scoreCalcs) return null

    // Check for direct mapping with _score suffix
    const scoreKey = `${tab.id}_score`
    if (scoreCalcs[scoreKey] !== undefined) {
      return scoreCalcs[scoreKey]
    }

    // Check for special cases
    const specialMappings = {
      genetic: 'genetic_evidence_score',
      experimental: 'experimental_evidence_score',
      clinical: 'clinical_evidence_score'
    }

    const specialKey = specialMappings[tab.id]
    if (specialKey && scoreCalcs[specialKey] !== undefined) {
      return scoreCalcs[specialKey]
    }

    return null
  }

  /**
   * Track which tabs have validation errors
   */
  const tabValidationErrors = computed(() => {
    const errors = {}

    validTabs.value.forEach(tab => {
      // Get all field paths in this tab
      const fieldsInTab = getTabFieldPaths(tab)
      const hasErrors = fieldsInTab.some(fieldPath => backendErrors.value[fieldPath]?.length > 0)
      errors[tab.id] = hasErrors
    })

    return errors
  })

  /**
   * Extract all field paths from a tab's sections
   */
  const getTabFieldPaths = tab => {
    const paths = []
    tab.sections?.forEach(section => {
      section.fields?.forEach(fieldPath => {
        paths.push(fieldPath)
      })
    })
    return paths
  }

  /**
   * Determine color for score badge based on value
   * @param {number|null} score - Score value
   * @returns {string} Vuetify color name
   */
  function getScoreColor(score) {
    if (score === null || score === undefined) return 'grey'
    if (score >= 7) return 'success'
    if (score >= 2) return 'warning'
    return 'info'
  }

  const updateField = (fieldName, value) => {
    clearFieldBackendError(fieldName)
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
    clearFieldBackendError(fieldPath)

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

  /**
   * Process backend validation result and map errors to fields
   * @param {Object} result - Validation result from backend
   */
  const handleBackendValidation = result => {
    backendErrors.value = {}
    nonFieldErrors.value = []

    if (!result || result.is_valid) return

    // Map field-specific errors
    if (result.field_validations) {
      Object.entries(result.field_validations).forEach(([field, validation]) => {
        if (validation.errors && validation.errors.length > 0) {
          // Take first error only per CONTEXT.md decision
          backendErrors.value[field] = [validation.errors[0].message]
        }
      })
    }

    // Collect non-field errors (errors without field mapping)
    if (result.errors) {
      result.errors.forEach(error => {
        if (!error.field || !result.field_validations?.[error.field]) {
          nonFieldErrors.value.push(error.message)
        }
      })
    }
  }

  /**
   * Clear backend error for a specific field
   * @param {string} fieldPath - Field path (supports dot notation)
   */
  const clearFieldBackendError = fieldPath => {
    if (backendErrors.value[fieldPath]) {
      delete backendErrors.value[fieldPath]
    }
  }

  const validateForm = async () => {
    validating.value = true
    try {
      const result = await validationStore.validateEvidence(formData.value, props.schemaId, 'form')
      handleBackendValidation(result)
    } catch (error) {
      logger.error('Form validation error:', { error: error.message, stack: error.stack })
    } finally {
      validating.value = false
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

  /**
   * Navigate to next tab (for mobile swipe gesture)
   */
  function nextTab() {
    const currentIndex = validTabs.value.findIndex(t => t.id === activeTab.value)
    if (currentIndex < validTabs.value.length - 1) {
      activeTab.value = validTabs.value[currentIndex + 1].id
    }
  }

  /**
   * Navigate to previous tab (for mobile swipe gesture)
   */
  function prevTab() {
    const currentIndex = validTabs.value.findIndex(t => t.id === activeTab.value)
    if (currentIndex > 0) {
      activeTab.value = validTabs.value[currentIndex - 1].id
    }
  }

  /**
   * Find first tab containing validation errors
   */
  const findFirstInvalidTab = () => {
    for (const tab of validTabs.value) {
      if (tabValidationErrors.value[tab.id]) {
        return tab.id
      }
    }
    return null
  }

  /**
   * Focus first field with validation error in current tab
   */
  const focusFirstInvalidField = () => {
    // Query for Vuetify input with error state
    const errorInput = document.querySelector('.v-input--error input, .v-input--error textarea')
    if (errorInput) {
      errorInput.focus()
      logger.debug('Focused first invalid field')
    }
  }

  const handleSubmit = async () => {
    submitting.value = true
    try {
      // Validate using v-form ref (VALD-06)
      const { valid } = await formRef.value.validate()

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

      // Also check backend validation
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

<style scoped>
  .sticky-sidebar {
    position: sticky;
    top: 80px;
    max-height: calc(100vh - 100px);
    overflow-y: auto;
    transition: all 0.3s ease;
  }

  @media (max-width: 1280px) {
    .sticky-sidebar {
      position: static;
      max-height: none;
    }
  }
</style>
