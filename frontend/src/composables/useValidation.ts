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
import type { Ref } from 'vue'
import { useExternalValidationStore } from '@/stores/externalValidation'
import { logService } from '@/services/logService'

export type ValidatorType = 'hgnc' | 'pubmed' | 'hpo'

/** Result returned by the external validation endpoints (HGNC, PubMed, HPO). */
export interface ValidationOutcome {
  is_valid: boolean
  [key: string]: unknown
}

export interface UseValidationReturn {
  value: Ref<string>
  result: Ref<ValidationOutcome | null>
  isValidating: Ref<boolean>
  error: Ref<string | null>
  validate: (val?: string) => Promise<ValidationOutcome | null>
  reset: () => void
}

// Simple debounce implementation
function debounce<T extends unknown[]>(
  fn: (...args: T) => void,
  delay: number
): (...args: T) => void {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  return function (...args: T) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

function errorMessageOf(e: unknown): string | undefined {
  return e instanceof Error ? e.message : undefined
}

export function useValidation(validator: ValidatorType): UseValidationReturn {
  if (!['hgnc', 'pubmed', 'hpo'].includes(validator)) {
    throw new Error(`Invalid validator: ${validator}. Must be 'hgnc', 'pubmed', or 'hpo'`)
  }

  const validationStore = useExternalValidationStore()

  const value = ref('')
  const result = ref<ValidationOutcome | null>(null)
  const isValidating = ref(false)
  const error = ref<string | null>(null)

  /** Dispatch to the store method matching the validator type */
  const callValidator = (val: string): Promise<ValidationOutcome> => {
    if (validator === 'hgnc') return validationStore.validateHGNC(val)
    if (validator === 'pubmed') return validationStore.validatePubMed(val)
    return validationStore.validateHPO(val)
  }

  /**
   * Validate a value with debouncing
   */
  const validateDebounced = debounce(async (val: string) => {
    if (!val || val.length < 2) {
      result.value = null
      return
    }

    isValidating.value = true
    error.value = null

    try {
      const validationResult = await callValidator(val)

      result.value = validationResult
      logService.debug('Validation complete', {
        validator,
        value: val,
        isValid: validationResult.is_valid
      })
    } catch (e) {
      error.value = errorMessageOf(e) || 'Validation failed'
      logService.error('Validation error', { validator, value: val, error: errorMessageOf(e) })
    } finally {
      isValidating.value = false
    }
  }, 500)

  // Watch value changes for automatic validation
  watch(value, newVal => {
    validateDebounced(newVal)
  })

  /**
   * Manually validate a value without debouncing
   * @param val - Value to validate (optional, uses current value if not provided)
   * @returns Validation result, or null when empty or on error
   */
  async function validate(val?: string): Promise<ValidationOutcome | null> {
    const valueToValidate = val || value.value

    if (!valueToValidate) {
      result.value = null
      return null
    }

    isValidating.value = true
    error.value = null

    try {
      const validationResult = await callValidator(valueToValidate)

      result.value = validationResult
      logService.info('Manual validation complete', {
        validator,
        value: valueToValidate,
        isValid: validationResult.is_valid
      })
      return validationResult
    } catch (e) {
      error.value = errorMessageOf(e) || 'Validation failed'
      logService.error('Manual validation error', {
        validator,
        value: valueToValidate,
        error: errorMessageOf(e)
      })
      return null
    } finally {
      isValidating.value = false
    }
  }

  /**
   * Reset validation state
   */
  function reset(): void {
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
