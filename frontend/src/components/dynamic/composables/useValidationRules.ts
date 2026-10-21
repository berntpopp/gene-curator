/**
 * useValidationRules Composable
 *
 * Generates Vuetify validation rules from JSON schema field constraints.
 * Supports: required, minLength, maxLength, minimum, maximum, pattern, enum
 *
 * @module composables/useValidationRules
 */

import { computed, type ComputedRef } from 'vue'
import type { FieldSchema } from '../types'

/** A Vuetify validation rule: returns `true` when valid, otherwise an error message. */
export type ValidationRule = (value: unknown) => true | string

const isEmpty = (value: unknown): boolean => value === null || value === undefined || value === ''

/**
 * Generate Vuetify validation rules from field schema constraints
 *
 * Rules are applied in order and Vuetify shows the first failing rule.
 * Empty values skip non-required validations to avoid confusing error stacking.
 *
 * @param fieldSchemaGetter - Reactive getter for field schema object
 * @returns { validationRules: ComputedRef<ValidationRule[]> }
 *
 * @example
 * const { validationRules } = useValidationRules(() => props.fieldSchema)
 */
export function useValidationRules(fieldSchemaGetter: () => FieldSchema): {
  validationRules: ComputedRef<ValidationRule[]>
} {
  return { validationRules: computed(() => rulesFor(fieldSchemaGetter())) }
}

/** Vuetify rules for one field's constraints (also used for evidence-table cells) */
export function rulesFor(fieldSchema: FieldSchema): ValidationRule[] {
  const rules: ValidationRule[] = []

  // 1. Required rule (VALD-01)
  if (fieldSchema.required === true) {
    rules.push(value => {
      // Check for null, undefined, empty string
      if (isEmpty(value)) {
        return fieldSchema.errorMessage || 'Required'
      }
      // Check for empty arrays
      if (Array.isArray(value) && value.length === 0) {
        return fieldSchema.errorMessage || 'Required'
      }
      return true
    })
  }

  // 2. minLength rule (VALD-01)
  if (fieldSchema.minLength !== undefined) {
    rules.push(value => {
      // Skip validation if value is empty (falsy) - required handles empty
      if (!value) {
        return true
      }
      if ((value as { length: number }).length < fieldSchema.minLength!) {
        return fieldSchema.errorMessage || `Minimum ${fieldSchema.minLength} characters`
      }
      return true
    })
  }

  // 3. maxLength rule (VALD-01)
  if (fieldSchema.maxLength !== undefined) {
    rules.push(value => {
      // Skip validation if value is empty
      if (!value) {
        return true
      }
      if ((value as { length: number }).length > fieldSchema.maxLength!) {
        return fieldSchema.errorMessage || `Maximum ${fieldSchema.maxLength} characters`
      }
      return true
    })
  }

  // 4. minimum rule (VALD-01)
  if (fieldSchema.minimum !== undefined) {
    rules.push(value => {
      // Skip validation if value is null or empty string
      if (isEmpty(value)) {
        return true
      }
      if ((value as number) < fieldSchema.minimum!) {
        return fieldSchema.errorMessage || `Minimum value: ${fieldSchema.minimum}`
      }
      return true
    })
  }

  // 5. maximum rule (VALD-01)
  if (fieldSchema.maximum !== undefined) {
    rules.push(value => {
      // Skip validation if value is null or empty string
      if (isEmpty(value)) {
        return true
      }
      if ((value as number) > fieldSchema.maximum!) {
        return fieldSchema.errorMessage || `Maximum value: ${fieldSchema.maximum}`
      }
      return true
    })
  }

  // 6. pattern rule (VALD-02)
  if (fieldSchema.pattern) {
    rules.push(value => {
      // Skip validation if value is empty
      if (!value) {
        return true
      }
      try {
        const regex = new RegExp(fieldSchema.pattern!)
        if (!regex.test(String(value))) {
          return fieldSchema.errorMessage || 'Invalid format'
        }
        return true
      } catch {
        // Invalid regex pattern - fail validation
        return 'Invalid pattern configuration'
      }
    })
  }

  // 7. enum rule (VALD-03)
  if (fieldSchema.enum && Array.isArray(fieldSchema.enum)) {
    rules.push(value => {
      // Skip validation if value is empty
      if (!value) {
        return true
      }
      if (!fieldSchema.enum!.includes(value as string | number)) {
        return fieldSchema.errorMessage || 'Must be one of the allowed values'
      }
      return true
    })
  }

  return rules
}
