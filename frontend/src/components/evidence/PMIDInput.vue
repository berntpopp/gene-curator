<template>
  <div class="pmid-input">
    <v-combobox
      v-model="internalPMIDs"
      :label="label"
      :hint="hint"
      :error-messages="errorMessages"
      :loading="isValidating"
      :required="required"
      :disabled="disabled"
      multiple
      chips
      closable-chips
      variant="outlined"
      prepend-inner-icon="mdi-file-document"
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
        <v-btn
          :loading="isValidating"
          :disabled="internalPMIDs.length === 0 || isValidating"
          color="primary"
          variant="tonal"
          size="small"
          @click="validatePMIDs"
        >
          <v-icon start size="small">mdi-check-circle</v-icon>
          Validate
        </v-btn>
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

    <!-- Validated Publications Display -->
    <v-expand-transition>
      <div v-if="validatedPublications.length > 0" class="mt-3">
        <div class="text-subtitle-2 mb-2 d-flex align-center">
          <v-icon size="small" color="success" class="mr-1">mdi-check-circle</v-icon>
          Validated Publications ({{ validatedPublications.length }})
          <v-spacer />
          <v-btn v-if="showDetails" variant="text" size="x-small" @click="showDetails = false">
            <v-icon size="small">mdi-chevron-up</v-icon>
            Hide Details
          </v-btn>
          <v-btn v-else variant="text" size="x-small" @click="showDetails = true">
            <v-icon size="small">mdi-chevron-down</v-icon>
            Show Details
          </v-btn>
        </div>
        <v-expand-transition>
          <v-list v-if="showDetails" density="compact" class="rounded border">
            <v-list-item v-for="pub in validatedPublications" :key="pub.pmid" class="py-2">
              <v-list-item-title class="text-body-2 d-flex align-center flex-wrap">
                <v-chip size="x-small" color="primary" variant="tonal" class="mr-2 mb-1">
                  PMID:{{ pub.pmid }}
                </v-chip>
                <span class="font-weight-medium">{{ truncateTitle(pub.title) }}</span>
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                {{ formatAuthors(pub) }}
                <span v-if="pub.journal" class="text-primary ml-1">
                  - {{ pub.journal }} ({{ pub.year || 'N/A' }})
                </span>
              </v-list-item-subtitle>
              <template #append>
                <div class="d-flex ga-1">
                  <v-tooltip v-if="pub.abstract" location="top">
                    <template #activator="{ props: tooltipProps }">
                      <v-btn v-bind="tooltipProps" icon variant="text" size="x-small">
                        <v-icon size="small">mdi-text</v-icon>
                      </v-btn>
                    </template>
                    <div class="text-caption" style="max-width: 400px">
                      <strong>Abstract</strong>
                      <div class="mt-1">{{ truncateAbstract(pub.abstract) }}</div>
                    </div>
                  </v-tooltip>
                  <v-btn
                    v-if="pub.doi"
                    icon
                    variant="text"
                    size="x-small"
                    :href="`https://doi.org/${pub.doi}`"
                    target="_blank"
                    aria-label="Open DOI"
                  >
                    <v-icon size="small">mdi-link-variant</v-icon>
                  </v-btn>
                  <v-btn
                    icon
                    variant="text"
                    size="x-small"
                    :href="`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}/`"
                    target="_blank"
                    aria-label="Open PubMed"
                  >
                    <v-icon size="small">mdi-open-in-new</v-icon>
                  </v-btn>
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-expand-transition>
      </div>
    </v-expand-transition>

    <!-- Validation Errors -->
    <v-expand-transition>
      <v-alert
        v-if="validationErrors.length > 0"
        type="warning"
        variant="tonal"
        density="compact"
        class="mt-3"
        closable
        @click:close="validationErrors = []"
      >
        <template #title>Invalid PMIDs</template>
        <div class="text-body-2">
          The following could not be validated:
          <v-chip
            v-for="err in validationErrors"
            :key="err.pmid"
            size="small"
            color="error"
            variant="outlined"
            class="ml-1"
          >
            {{ err.pmid }}
          </v-chip>
        </div>
      </v-alert>
    </v-expand-transition>
  </div>
</template>

<script setup>
  /**
   * PMIDInput Component
   *
   * Multi-value input for PubMed IDs with batch validation and publication details.
   * Validates PMIDs against Europe PMC API and caches publications in database.
   *
   * Design principles:
   * - On-demand validation (prevents excessive API calls)
   * - Batch validation (efficient for multiple PMIDs)
   * - Visual feedback per chip (color-coded)
   * - Publication details display (title, authors, journal)
   * - Database caching via publications API
   *
   * @example
   * <PMIDInput
   *   v-model="formData.pmids"
   *   v-model:publications="formData.publications"
   *   label="Supporting Evidence"
   *   hint="Enter one or more PubMed IDs"
   *   required
   * />
   */

  import { ref, computed, watch } from 'vue'
  import { publicationsAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'

  const props = defineProps({
    modelValue: {
      type: Array,
      default: () => []
    },
    publications: {
      type: Array,
      default: () => []
    },
    label: {
      type: String,
      default: 'PubMed IDs'
    },
    hint: {
      type: String,
      default: 'Enter PMIDs and click Validate'
    },
    required: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    },
    validateOnMount: {
      type: Boolean,
      default: false
    }
  })

  const emit = defineEmits(['update:modelValue', 'update:publications', 'validated'])

  const logger = useLogger()

  // State
  const internalPMIDs = ref([...(props.modelValue || [])])
  const validatedPublications = ref([...props.publications])
  const validationErrors = ref([])
  const validationResults = ref(new Map())
  const isValidating = ref(false)
  const error = ref(null)
  const showDetails = ref(true)

  // Sync with parent modelValue
  watch(
    () => props.modelValue,
    newValue => {
      if (JSON.stringify(newValue) !== JSON.stringify(internalPMIDs.value)) {
        internalPMIDs.value = [...(newValue || [])]
      }
    }
  )

  // Sync with parent publications
  watch(
    () => props.publications,
    newValue => {
      if (JSON.stringify(newValue) !== JSON.stringify(validatedPublications.value)) {
        validatedPublications.value = [...(newValue || [])]
      }
    },
    { deep: true }
  )

  // Emit changes
  watch(
    internalPMIDs,
    newValue => {
      emit('update:modelValue', newValue)
    },
    { deep: true }
  )

  /**
   * Normalize PMID string
   */
  function normalizePmid(pmid) {
    if (!pmid) return ''
    let clean = String(pmid).trim().toUpperCase()
    if (clean.startsWith('PMID:')) clean = clean.slice(5)
    if (clean.startsWith('PMID')) clean = clean.slice(4)
    return clean.trim()
  }

  /**
   * Validate all PMIDs in batch
   */
  async function validatePMIDs() {
    if (!internalPMIDs.value || internalPMIDs.value.length === 0) {
      validationResults.value.clear()
      validatedPublications.value = []
      validationErrors.value = []
      error.value = null
      return
    }

    isValidating.value = true
    error.value = null
    validationErrors.value = []

    try {
      // Normalize and dedupe PMIDs
      const pmids = [...new Set(internalPMIDs.value.map(normalizePmid).filter(p => p))]

      if (pmids.length === 0) {
        logger.debug('No valid PMIDs to validate')
        return
      }

      // Call API to validate
      const response = await publicationsAPI.validatePMIDs(pmids)

      // Update validation results map
      validationResults.value.clear()
      response.results.forEach(r => {
        validationResults.value.set(r.pmid, r)
      })

      // Extract valid publications
      validatedPublications.value = response.results
        .filter(r => r.is_valid && r.publication)
        .map(r => r.publication)

      // Extract errors
      validationErrors.value = response.results
        .filter(r => !r.is_valid)
        .map(r => ({ pmid: r.pmid, error: r.error }))

      // Update internal PMIDs to only valid ones
      const validPmids = validatedPublications.value.map(p => p.pmid)
      internalPMIDs.value = validPmids

      // Emit events
      emit('update:modelValue', validPmids)
      emit('update:publications', validatedPublications.value)
      emit('validated', {
        valid: validatedPublications.value,
        invalid: validationErrors.value
      })

      logger.info('PMID validation complete', {
        total: pmids.length,
        valid: validatedPublications.value.length,
        invalid: validationErrors.value.length
      })
    } catch (e) {
      error.value = e.message || 'Validation failed'
      logger.error('PMID validation error', { error: e.message })
    } finally {
      isValidating.value = false
    }
  }

  /**
   * Handle blur event
   */
  function handleBlur() {
    // Auto-validate if there are new PMIDs
    const currentPmids = new Set(internalPMIDs.value.map(normalizePmid))
    const validatedPmids = new Set(validatedPublications.value.map(p => p.pmid))
    const hasNew = [...currentPmids].some(p => !validatedPmids.has(p))

    if (hasNew && currentPmids.size > 0) {
      validatePMIDs()
    }
  }

  /**
   * Handle Enter key
   */
  function handleEnter() {
    validatePMIDs()
  }

  /**
   * Get validation result for a PMID
   */
  function getValidationResult(pmid) {
    const normalized = normalizePmid(pmid)
    return validationResults.value.get(normalized)
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

  /**
   * Truncate title for display
   */
  function truncateTitle(title, maxLength = 80) {
    if (!title) return 'Untitled'
    if (title.length <= maxLength) return title
    return `${title.slice(0, maxLength)}...`
  }

  /**
   * Truncate abstract for tooltip
   */
  function truncateAbstract(abstract, maxLength = 300) {
    if (!abstract) return ''
    if (abstract.length <= maxLength) return abstract
    return `${abstract.slice(0, maxLength)}...`
  }

  /**
   * Format authors for display
   */
  function formatAuthors(pub) {
    if (pub.author_string) return pub.author_string
    if (pub.authors && pub.authors.length > 0) {
      if (pub.authors.length <= 3) return pub.authors.join(', ')
      return `${pub.authors.slice(0, 3).join(', ')} et al.`
    }
    return 'Unknown authors'
  }

  // Validation summary
  const hasValidResults = computed(() => validationResults.value.size > 0)
  const validCount = computed(() => validatedPublications.value.length)
  const invalidCount = computed(() => validationErrors.value.length)

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

  .pmid-input :deep(.v-field__append-inner) {
    align-items: flex-start;
    padding-top: 8px;
  }
</style>
