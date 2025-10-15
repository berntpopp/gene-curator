<template>
  <v-combobox
    v-model="internalTerms"
    label="HPO Terms"
    :hint="hint"
    :error-messages="errorMessages"
    :loading="isValidating"
    :required="required"
    multiple
    chips
    closable-chips
    variant="outlined"
    @blur="handleBlur"
    @keydown.enter.prevent="handleEnter"
  >
    <template #chip="{ item, props: chipProps }">
      <v-chip
        v-bind="chipProps"
        :color="getChipColor(item.value)"
        :prepend-icon="getChipIcon(item.value)"
      >
        <template #default>
          {{ item.value }}
          <v-tooltip v-if="getTermName(item.value)" location="top" activator="parent">
            <div class="text-caption">
              <strong>{{ getTermName(item.value) }}</strong>
              <div v-if="getTermDefinition(item.value)" class="text-caption mt-1">
                {{ getTermDefinition(item.value) }}
              </div>
            </div>
          </v-tooltip>
        </template>
      </v-chip>
    </template>

    <template #append-inner>
      <v-menu v-if="hasValidResults" location="top">
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            icon
            variant="text"
            size="small"
            :aria-label="`${validCount} valid, ${invalidCount} invalid HPO terms`"
          >
            <v-badge :content="validCount" :model-value="validCount > 0" color="success" overlap>
              <v-icon>mdi-information</v-icon>
            </v-badge>
          </v-btn>
        </template>
        <v-card max-width="500">
          <v-card-text>
            <div class="text-caption mb-2">HPO Validation Summary</div>
            <v-row dense>
              <v-col cols="6">
                <v-chip color="success" size="small" block>
                  <v-icon start size="small">mdi-check-circle</v-icon>
                  {{ validCount }} Valid
                </v-chip>
              </v-col>
              <v-col cols="6">
                <v-chip color="error" size="small" block>
                  <v-icon start size="small">mdi-alert-circle</v-icon>
                  {{ invalidCount }} Invalid
                </v-chip>
              </v-col>
            </v-row>

            <!-- List valid terms with names -->
            <v-expansion-panels v-if="validCount > 0" class="mt-2" variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>Valid Terms</v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item
                      v-for="term in validTerms"
                      :key="term"
                      class="px-0"
                      density="compact"
                    >
                      <v-list-item-title class="text-caption">
                        {{ term }}
                      </v-list-item-title>
                      <v-list-item-subtitle class="text-caption">
                        {{ getTermName(term) }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>
      </v-menu>
    </template>

    <template #details>
      <div v-if="isValidating" class="text-caption text-medium-emphasis">
        Validating {{ internalTerms.length }} HPO term(s)...
      </div>
      <div v-else-if="hasValidResults" class="text-caption">
        <span v-if="validCount > 0" class="text-success"> {{ validCount }} valid </span>
        <span v-if="invalidCount > 0" class="text-error">
          {{ invalidCount > 0 && validCount > 0 ? ', ' : '' }}{{ invalidCount }} invalid
        </span>
      </div>
    </template>
  </v-combobox>
</template>

<script setup>
  /**
   * HPOInput Component
   *
   * Multi-value input for Human Phenotype Ontology (HPO) terms with batch validation.
   * Validates on blur (NOT real-time) following UX best practices.
   *
   * Design principles:
   * - On-blur validation (prevents excessive API calls)
   * - Batch validation (efficient for multiple terms)
   * - Visual feedback per chip with tooltips
   * - Accessible (ARIA labels, keyboard support)
   * - Caching via externalValidation store
   * - Shows term names and definitions in tooltips
   *
   * @example
   * <hpo-input
   *   v-model="formData.hpoTerms"
   *   label="Associated Phenotypes"
   *   hint="Enter HPO IDs (e.g., HP:0001250)"
   *   required
   * />
   */

  import { ref, computed, watch } from 'vue'
  import { useExternalValidationStore } from '@/stores/externalValidation.js'
  import { useLogger } from '@/composables/useLogger'

  const props = defineProps({
    modelValue: {
      type: Array,
      default: () => []
    },
    label: {
      type: String,
      default: 'HPO Terms'
    },
    hint: {
      type: String,
      default: 'Enter HPO IDs (e.g., HP:0001250). Press Enter to add multiple.'
    },
    required: {
      type: Boolean,
      default: false
    },
    validateOnMount: {
      type: Boolean,
      default: false
    }
  })

  const emit = defineEmits(['update:modelValue'])

  const logger = useLogger()
  const validationStore = useExternalValidationStore()

  const internalTerms = ref([...(props.modelValue || [])])
  const validationResults = ref(new Map())
  const isValidating = ref(false)
  const error = ref(null)

  // Sync with parent
  watch(
    () => props.modelValue,
    newValue => {
      if (JSON.stringify(newValue) !== JSON.stringify(internalTerms.value)) {
        internalTerms.value = [...(newValue || [])]
      }
    }
  )

  watch(
    internalTerms,
    newValue => {
      emit('update:modelValue', newValue)
    },
    { deep: true }
  )

  /**
   * Validate all HPO terms in batch
   * Called on blur or Enter key
   */
  async function validateTerms() {
    if (!internalTerms.value || internalTerms.value.length === 0) {
      validationResults.value.clear()
      error.value = null
      return
    }

    isValidating.value = true
    error.value = null

    try {
      // Batch validate all HPO terms
      const results = await validationStore.validateBatch('hpo', internalTerms.value)

      // Store results in map for quick lookup
      validationResults.value.clear()
      Object.entries(results).forEach(([term, result]) => {
        validationResults.value.set(term, result)
      })

      logger.debug('HPO batch validation complete', {
        total: internalTerms.value.length,
        valid: validCount.value,
        invalid: invalidCount.value
      })
    } catch (e) {
      error.value = e.message || 'HPO validation failed'
      logger.error('HPO validation error', { error: e.message })
    } finally {
      isValidating.value = false
    }
  }

  /**
   * Handle blur event - validate all terms
   */
  function handleBlur() {
    validateTerms()
    logger.debug('HPO input blur', { count: internalTerms.value.length })
  }

  /**
   * Handle Enter key - validate and stay focused
   */
  function handleEnter() {
    validateTerms()
  }

  /**
   * Get validation result for an HPO term
   */
  function getValidationResult(term) {
    // Check component cache first
    if (validationResults.value.has(term)) {
      return validationResults.value.get(term)
    }
    // Fallback to store cache
    return validationStore.getCachedResult('hpo', term)
  }

  /**
   * Get term name from validation result
   */
  function getTermName(term) {
    const result = getValidationResult(term)
    return result?.data?.term_name || ''
  }

  /**
   * Get term definition from validation result
   */
  function getTermDefinition(term) {
    const result = getValidationResult(term)
    return result?.data?.definition || ''
  }

  /**
   * Determine chip color based on validation state
   */
  function getChipColor(term) {
    if (isValidating.value) return 'primary'
    const result = getValidationResult(term)
    if (!result) return 'default'
    return result.is_valid ? 'success' : 'error'
  }

  /**
   * Get icon for chip based on validation state
   */
  function getChipIcon(term) {
    if (isValidating.value) return 'mdi-loading mdi-spin'
    const result = getValidationResult(term)
    if (!result) return ''
    return result.is_valid ? 'mdi-check-circle' : 'mdi-alert-circle'
  }

  // Validation summary
  const hasValidResults = computed(() => validationResults.value.size > 0)
  const validCount = computed(() => {
    return Array.from(validationResults.value.values()).filter(r => r.is_valid).length
  })
  const invalidCount = computed(() => {
    return Array.from(validationResults.value.values()).filter(r => !r.is_valid).length
  })

  // List of valid term IDs
  const validTerms = computed(() => {
    return Array.from(validationResults.value.entries())
      .filter(([, result]) => result.is_valid)
      .map(([term]) => term)
  })

  // Error messages for form validation
  const errorMessages = computed(() => {
    if (error.value) return [error.value]
    if (props.required && internalTerms.value.length === 0) {
      return ['At least one HPO term is required']
    }
    if (invalidCount.value > 0 && hasValidResults.value) {
      return [`${invalidCount.value} invalid HPO term(s)`]
    }
    return []
  })

  // Auto-validate on mount if requested
  if (props.validateOnMount && props.modelValue && props.modelValue.length > 0) {
    validateTerms()
  }
</script>

<style scoped>
  /* Ensure chips are readable */
  :deep(.v-chip) {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.875rem;
  }

  /* Loading animation for validating state */
  :deep(.mdi-spin) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  /* Tooltip styling */
  :deep(.v-tooltip > .v-overlay__content) {
    max-width: 400px;
  }
</style>
