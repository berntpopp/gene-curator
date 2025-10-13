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
                @update:model-value="updateField(fieldName, $event)"
                @validate="validateField(fieldName, $event)"
              />
            </v-col>
          </v-row>

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
        </div>

        <v-alert v-else-if="error" type="error" variant="tonal">
          <template #prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          Failed to load form schema: {{ error }}
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
  </v-form>
</template>

<script setup>
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
  import { ref, computed, onMounted, watch } from 'vue'
  import { useValidationStore } from '@/stores'
  import DynamicField from './DynamicField.vue'

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
    }
  })

  const emit = defineEmits(['submit', 'save-draft'])

  const validationStore = useValidationStore()
  const formRef = ref(null)
  const formData = ref({ ...props.initialData })
  const saving = ref(false)
  const submitting = ref(false)

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

  const updateField = (fieldName, value) => {
    formData.value[fieldName] = value
    // Trigger validation debounced
    clearTimeout(updateField.timeout)
    updateField.timeout = setTimeout(() => {
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

  // Watch for schema changes and generate JSON schema
  watch(
    () => props.schemaId,
    async newSchemaId => {
      if (newSchemaId) {
        try {
          await validationStore.generateJsonSchema(newSchemaId)
        } catch (error) {
          logger.error('Failed to generate JSON schema:', { error: error.message, stack: error.stack })
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
