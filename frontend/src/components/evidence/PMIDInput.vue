<template>
  <v-combobox
    v-model="internalPMIDs"
    label="PubMed IDs (PMIDs)"
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
        {{ item.value }}
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
            :aria-label="`${validCount} valid, ${invalidCount} invalid`"
          >
            <v-badge :content="validCount" :model-value="validCount > 0" color="success" overlap>
              <v-icon>mdi-information</v-icon>
            </v-badge>
          </v-btn>
        </template>
        <v-card max-width="400">
          <v-card-text>
            <div class="text-caption mb-2">Validation Summary</div>
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
          </v-card-text>
        </v-card>
      </v-menu>
    </template>

    <template #details>
      <div v-if="isValidating" class="text-caption text-medium-emphasis">
        Validating {{ internalPMIDs.length }} PMID(s)...
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
   * PMIDInput Component
   *
   * Multi-value input for PubMed IDs with batch validation.
   * Validates on blur (NOT real-time) following UX best practices.
   *
   * Design principles:
   * - On-blur validation (prevents excessive API calls)
   * - Batch validation (efficient for multiple PMIDs)
   * - Visual feedback per chip (color-coded)
   * - Accessible (ARIA labels, keyboard support)
   * - Caching via externalValidation store
   *
   * @example
   * <pmid-input
   *   v-model="formData.pmids"
   *   label="Supporting Evidence"
   *   hint="Enter one or more PubMed IDs"
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
      default: 'PubMed IDs'
    },
    hint: {
      type: String,
      default: 'Press Enter to add multiple PMIDs'
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

  const internalPMIDs = ref([...(props.modelValue || [])])
  const validationResults = ref(new Map())
  const isValidating = ref(false)
  const error = ref(null)

  // Sync with parent
  watch(
    () => props.modelValue,
    newValue => {
      if (JSON.stringify(newValue) !== JSON.stringify(internalPMIDs.value)) {
        internalPMIDs.value = [...(newValue || [])]
      }
    }
  )

  watch(
    internalPMIDs,
    newValue => {
      emit('update:modelValue', newValue)
    },
    { deep: true }
  )

  /**
   * Validate all PMIDs in batch
   * Called on blur or Enter key
   */
  async function validatePMIDs() {
    if (!internalPMIDs.value || internalPMIDs.value.length === 0) {
      validationResults.value.clear()
      error.value = null
      return
    }

    isValidating.value = true
    error.value = null

    try {
      // Batch validate all PMIDs
      const results = await validationStore.validateBatch('pubmed', internalPMIDs.value)

      // Store results in map for quick lookup
      validationResults.value.clear()
      Object.entries(results).forEach(([pmid, result]) => {
        validationResults.value.set(pmid, result)
      })

      logger.debug('PMID batch validation complete', {
        total: internalPMIDs.value.length,
        valid: validCount.value,
        invalid: invalidCount.value
      })
    } catch (e) {
      error.value = e.message || 'Validation failed'
      logger.error('PMID validation error', { error: e.message })
    } finally {
      isValidating.value = false
    }
  }

  /**
   * Handle blur event - validate all PMIDs
   */
  function handleBlur() {
    validatePMIDs()
    logger.debug('PMID input blur', { count: internalPMIDs.value.length })
  }

  /**
   * Handle Enter key - validate and stay focused
   */
  function handleEnter() {
    validatePMIDs()
  }

  /**
   * Get validation result for a PMID
   */
  function getValidationResult(pmid) {
    // Check component cache first
    if (validationResults.value.has(pmid)) {
      return validationResults.value.get(pmid)
    }
    // Fallback to store cache
    return validationStore.getCachedResult('pubmed', pmid)
  }

  /**
   * Determine chip color based on validation state
   */
  function getChipColor(pmid) {
    if (isValidating.value) return 'primary'
    const result = getValidationResult(pmid)
    if (!result) return 'default'
    return result.is_valid ? 'success' : 'error'
  }

  /**
   * Get icon for chip based on validation state
   */
  function getChipIcon(pmid) {
    if (isValidating.value) return 'mdi-loading mdi-spin'
    const result = getValidationResult(pmid)
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

  // Error messages for form validation
  const errorMessages = computed(() => {
    if (error.value) return [error.value]
    if (props.required && internalPMIDs.value.length === 0) {
      return ['At least one PMID is required']
    }
    if (invalidCount.value > 0 && hasValidResults.value) {
      return [`${invalidCount.value} invalid PMID(s)`]
    }
    return []
  })

  // Auto-validate on mount if requested
  if (props.validateOnMount && props.modelValue && props.modelValue.length > 0) {
    validatePMIDs()
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
</style>
