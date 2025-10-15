/**
 * Composable for field validation with external validators (HGNC, PubMed, HPO)
 *
 * Provides reactive validation with debouncing and caching
 *
 * @example
 * import { useValidation } from '@/composables/useValidation'
 *
 * const { value, result, isValidating, error, validate, reset } = useValidation('hgnc')
 * value.value = 'BRCA1' // Auto-validates after 500ms
 */

import { ref, watch } from 'vue'
import { useExternalValidationStore } from '@/stores/externalValidation.js'
import { logService } from '@/services/logService'

// Simple debounce implementation
function debounce(fn, delay) {
  let timeoutId
  return function (...args) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

export function useValidation(validator) {
  if (!['hgnc', 'pubmed', 'hpo'].includes(validator)) {
    throw new Error(`Invalid validator: ${validator}. Must be 'hgnc', 'pubmed', or 'hpo'`)
  }

  const validationStore = useExternalValidationStore()

  const value = ref('')
  const result = ref(null)
  const isValidating = ref(false)
  const error = ref(null)

  /**
   * Validate a value with debouncing
   */
  const validateDebounced = debounce(async (val) => {
    if (!val || val.length < 2) {
      result.value = null
      return
    }

    isValidating.value = true
    error.value = null

    try {
      let validationResult

      if (validator === 'hgnc') {
        validationResult = await validationStore.validateHGNC(val)
      } else if (validator === 'pubmed') {
        validationResult = await validationStore.validatePubMed(val)
      } else {
        validationResult = await validationStore.validateHPO(val)
      }

      result.value = validationResult
      logService.debug('Validation complete', { validator, value: val, isValid: validationResult.is_valid })
    } catch (e) {
      error.value = e.message || 'Validation failed'
      logService.error('Validation error', { validator, value: val, error: e.message })
    } finally {
      isValidating.value = false
    }
  }, 500)

  // Watch value changes for automatic validation
  watch(value, (newVal) => {
    validateDebounced(newVal)
  })

  /**
   * Manually validate a value without debouncing
   * @param {string} val - Value to validate (optional, uses current value if not provided)
   * @returns {Promise<Object|null>} Validation result
   */
  async function validate(val) {
    const valueToValidate = val || value.value

    if (!valueToValidate) {
      result.value = null
      return null
    }

    isValidating.value = true
    error.value = null

    try {
      let validationResult

      if (validator === 'hgnc') {
        validationResult = await validationStore.validateHGNC(valueToValidate)
      } else if (validator === 'pubmed') {
        validationResult = await validationStore.validatePubMed(valueToValidate)
      } else {
        validationResult = await validationStore.validateHPO(valueToValidate)
      }

      result.value = validationResult
      logService.info('Manual validation complete', { validator, value: valueToValidate, isValid: validationResult.is_valid })
      return validationResult
    } catch (e) {
      error.value = e.message || 'Validation failed'
      logService.error('Manual validation error', { validator, value: valueToValidate, error: e.message })
      return null
    } finally {
      isValidating.value = false
    }
  }

  /**
   * Reset validation state
   */
  function reset() {
    value.value = ''
    result.value = null
    error.value = null
    isValidating.value = false
  }

  return {
    value,
    result,
    isValidating,
    error,
    validate,
    reset
  }
}
