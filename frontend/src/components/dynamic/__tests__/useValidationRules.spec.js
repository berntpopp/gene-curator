/**
 * useValidationRules Composable Tests
 *
 * Test Coverage:
 * - Required rule for various value types
 * - minLength and maxLength rules
 * - minimum and maximum rules for numbers
 * - pattern rule with regex validation
 * - enum rule with allowed values
 * - Combined rules scenarios
 * - Reactivity when schema changes
 * - Custom error messages
 *
 * @see src/components/dynamic/composables/useValidationRules.js
 */

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useValidationRules } from '../composables/useValidationRules'

describe('useValidationRules', () => {
  // Helper to extract rules and test them
  const getRules = schema => {
    const schemaRef = ref(schema)
    const { validationRules } = useValidationRules(() => schemaRef.value)
    return validationRules.value
  }

  describe('required rule', () => {
    it('returns error for null value when required', () => {
      const rules = getRules({ required: true })
      expect(rules.length).toBe(1)
      const result = rules[0](null)
      expect(result).toBe('Required')
    })

    it('returns error for undefined value when required', () => {
      const rules = getRules({ required: true })
      const result = rules[0](undefined)
      expect(result).toBe('Required')
    })

    it('returns error for empty string when required', () => {
      const rules = getRules({ required: true })
      const result = rules[0]('')
      expect(result).toBe('Required')
    })

    it('returns error for empty array when required', () => {
      const rules = getRules({ required: true })
      const result = rules[0]([])
      expect(result).toBe('Required')
    })

    it('passes for non-empty value when required', () => {
      const rules = getRules({ required: true })
      const result = rules[0]('some value')
      expect(result).toBe(true)
    })

    it('passes for non-empty array when required', () => {
      const rules = getRules({ required: true })
      const result = rules[0](['item'])
      expect(result).toBe(true)
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ required: true, errorMessage: 'Custom required message' })
      const result = rules[0](null)
      expect(result).toBe('Custom required message')
    })

    it('skips rule when not required', () => {
      const rules = getRules({ required: false })
      expect(rules.length).toBe(0)
    })

    it('skips rule when required property absent', () => {
      const rules = getRules({})
      expect(rules.length).toBe(0)
    })
  })

  describe('minLength rule', () => {
    it('returns error for string shorter than minLength', () => {
      const rules = getRules({ minLength: 5 })
      expect(rules.length).toBe(1)
      const result = rules[0]('abc')
      expect(result).toBe('Minimum 5 characters')
    })

    it('passes for string equal to minLength', () => {
      const rules = getRules({ minLength: 5 })
      const result = rules[0]('abcde')
      expect(result).toBe(true)
    })

    it('passes for string longer than minLength', () => {
      const rules = getRules({ minLength: 5 })
      const result = rules[0]('abcdefgh')
      expect(result).toBe(true)
    })

    it('skips validation for empty value', () => {
      const rules = getRules({ minLength: 5 })
      const result = rules[0]('')
      expect(result).toBe(true)
    })

    it('skips validation for null value', () => {
      const rules = getRules({ minLength: 5 })
      const result = rules[0](null)
      expect(result).toBe(true)
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ minLength: 5, errorMessage: 'Must be longer' })
      const result = rules[0]('abc')
      expect(result).toBe('Must be longer')
    })
  })

  describe('maxLength rule', () => {
    it('returns error for string longer than maxLength', () => {
      const rules = getRules({ maxLength: 5 })
      expect(rules.length).toBe(1)
      const result = rules[0]('abcdefgh')
      expect(result).toBe('Maximum 5 characters')
    })

    it('passes for string equal to maxLength', () => {
      const rules = getRules({ maxLength: 5 })
      const result = rules[0]('abcde')
      expect(result).toBe(true)
    })

    it('passes for string shorter than maxLength', () => {
      const rules = getRules({ maxLength: 5 })
      const result = rules[0]('abc')
      expect(result).toBe(true)
    })

    it('skips validation for empty value', () => {
      const rules = getRules({ maxLength: 5 })
      const result = rules[0]('')
      expect(result).toBe(true)
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ maxLength: 5, errorMessage: 'Too long' })
      const result = rules[0]('abcdefgh')
      expect(result).toBe('Too long')
    })
  })

  describe('minimum rule', () => {
    it('returns error for number below minimum', () => {
      const rules = getRules({ minimum: 10 })
      expect(rules.length).toBe(1)
      const result = rules[0](5)
      expect(result).toBe('Minimum value: 10')
    })

    it('passes for number equal to minimum', () => {
      const rules = getRules({ minimum: 10 })
      const result = rules[0](10)
      expect(result).toBe(true)
    })

    it('passes for number above minimum', () => {
      const rules = getRules({ minimum: 10 })
      const result = rules[0](15)
      expect(result).toBe(true)
    })

    it('skips validation for null value', () => {
      const rules = getRules({ minimum: 10 })
      const result = rules[0](null)
      expect(result).toBe(true)
    })

    it('skips validation for empty string', () => {
      const rules = getRules({ minimum: 10 })
      const result = rules[0]('')
      expect(result).toBe(true)
    })

    it('handles minimum of 0', () => {
      const rules = getRules({ minimum: 0 })
      const result = rules[0](-1)
      expect(result).toBe('Minimum value: 0')
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ minimum: 10, errorMessage: 'Value too small' })
      const result = rules[0](5)
      expect(result).toBe('Value too small')
    })
  })

  describe('maximum rule', () => {
    it('returns error for number above maximum', () => {
      const rules = getRules({ maximum: 10 })
      expect(rules.length).toBe(1)
      const result = rules[0](15)
      expect(result).toBe('Maximum value: 10')
    })

    it('passes for number equal to maximum', () => {
      const rules = getRules({ maximum: 10 })
      const result = rules[0](10)
      expect(result).toBe(true)
    })

    it('passes for number below maximum', () => {
      const rules = getRules({ maximum: 10 })
      const result = rules[0](5)
      expect(result).toBe(true)
    })

    it('skips validation for null value', () => {
      const rules = getRules({ maximum: 10 })
      const result = rules[0](null)
      expect(result).toBe(true)
    })

    it('handles maximum of 0', () => {
      const rules = getRules({ maximum: 0 })
      const result = rules[0](1)
      expect(result).toBe('Maximum value: 0')
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ maximum: 10, errorMessage: 'Value too large' })
      const result = rules[0](15)
      expect(result).toBe('Value too large')
    })
  })

  describe('pattern rule', () => {
    it('returns error for value not matching pattern', () => {
      const rules = getRules({ pattern: '^[A-Z]+$' })
      expect(rules.length).toBe(1)
      const result = rules[0]('abc123')
      expect(result).toBe('Invalid format')
    })

    it('passes for value matching pattern', () => {
      const rules = getRules({ pattern: '^[A-Z]+$' })
      const result = rules[0]('ABCD')
      expect(result).toBe(true)
    })

    it('skips validation for empty value', () => {
      const rules = getRules({ pattern: '^[A-Z]+$' })
      const result = rules[0]('')
      expect(result).toBe(true)
    })

    it('skips validation for null value', () => {
      const rules = getRules({ pattern: '^[A-Z]+$' })
      const result = rules[0](null)
      expect(result).toBe(true)
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ pattern: '^[A-Z]+$', errorMessage: 'Must be uppercase letters only' })
      const result = rules[0]('abc')
      expect(result).toBe('Must be uppercase letters only')
    })

    it('handles complex patterns', () => {
      // Email-like pattern
      const rules = getRules({ pattern: '^[^@]+@[^@]+\\.[^@]+$' })
      expect(rules[0]('test@example.com')).toBe(true)
      expect(rules[0]('invalid-email')).toBe('Invalid format')
    })

    it('returns error for invalid regex pattern', () => {
      const rules = getRules({ pattern: '[invalid(' })
      const result = rules[0]('test')
      expect(result).toBe('Invalid pattern configuration')
    })
  })

  describe('enum rule', () => {
    it('returns error for value not in enum', () => {
      const rules = getRules({ enum: ['option1', 'option2', 'option3'] })
      expect(rules.length).toBe(1)
      const result = rules[0]('option4')
      expect(result).toBe('Must be one of the allowed values')
    })

    it('passes for value in enum', () => {
      const rules = getRules({ enum: ['option1', 'option2', 'option3'] })
      const result = rules[0]('option2')
      expect(result).toBe(true)
    })

    it('skips validation for empty value', () => {
      const rules = getRules({ enum: ['option1', 'option2'] })
      const result = rules[0]('')
      expect(result).toBe(true)
    })

    it('skips validation for null value', () => {
      const rules = getRules({ enum: ['option1', 'option2'] })
      const result = rules[0](null)
      expect(result).toBe(true)
    })

    it('handles numeric enum values', () => {
      const rules = getRules({ enum: [1, 2, 3] })
      expect(rules[0](2)).toBe(true)
      expect(rules[0](4)).toBe('Must be one of the allowed values')
    })

    it('uses schema errorMessage when provided', () => {
      const rules = getRules({ enum: ['A', 'B'], errorMessage: 'Must select A or B' })
      const result = rules[0]('C')
      expect(result).toBe('Must select A or B')
    })

    it('skips rule when enum is not an array', () => {
      const rules = getRules({ enum: 'not-an-array' })
      expect(rules.length).toBe(0)
    })
  })

  describe('combined rules', () => {
    it('generates multiple rules for schema with multiple constraints', () => {
      const rules = getRules({
        required: true,
        minLength: 3,
        maxLength: 10,
        pattern: '^[a-z]+$'
      })
      expect(rules.length).toBe(4)
    })

    it('validates all rules in order', () => {
      const rules = getRules({
        required: true,
        minLength: 5,
        maxLength: 10
      })

      // Required fails first
      expect(rules[0]('')).toBe('Required')

      // MinLength fails for short string
      expect(rules[1]('abc')).toBe('Minimum 5 characters')

      // MaxLength fails for long string
      expect(rules[2]('abcdefghijk')).toBe('Maximum 10 characters')

      // All pass for valid string
      const validValue = 'abcdef'
      expect(rules[0](validValue)).toBe(true)
      expect(rules[1](validValue)).toBe(true)
      expect(rules[2](validValue)).toBe(true)
    })

    it('returns empty array for schema with no constraints', () => {
      const rules = getRules({ type: 'string' })
      expect(rules.length).toBe(0)
    })

    it('handles number constraints combined', () => {
      const rules = getRules({
        required: true,
        minimum: 0,
        maximum: 100
      })

      expect(rules.length).toBe(3)
      expect(rules[0](null)).toBe('Required')
      expect(rules[1](-1)).toBe('Minimum value: 0')
      expect(rules[2](101)).toBe('Maximum value: 100')
      expect(rules[0](50)).toBe(true)
      expect(rules[1](50)).toBe(true)
      expect(rules[2](50)).toBe(true)
    })

    it('handles all constraint types together', () => {
      const rules = getRules({
        required: true,
        minLength: 2,
        maxLength: 5,
        pattern: '^[A-Z]+$',
        enum: ['AB', 'ABC', 'ABCD']
      })

      expect(rules.length).toBe(5)

      // Valid value passes all rules
      const validValue = 'ABC'
      expect(rules.every(rule => rule(validValue) === true)).toBe(true)

      // Invalid values fail appropriate rules
      expect(rules[0]('')).toBe('Required')
      expect(rules[1]('A')).toBe('Minimum 2 characters')
      expect(rules[2]('ABCDEF')).toBe('Maximum 5 characters')
      expect(rules[3]('abc')).toBe('Invalid format')
      expect(rules[4]('XYZ')).toBe('Must be one of the allowed values')
    })
  })

  describe('reactivity', () => {
    it('recomputes rules when schema changes', () => {
      const schemaRef = ref({ required: true })
      const { validationRules } = useValidationRules(() => schemaRef.value)

      // Initial state - only required rule
      expect(validationRules.value.length).toBe(1)

      // Update schema to add minLength
      schemaRef.value = { required: true, minLength: 5 }

      // Rules should update reactively
      expect(validationRules.value.length).toBe(2)
    })

    it('removes rules when constraints removed from schema', () => {
      const schemaRef = ref({ required: true, minLength: 5, maxLength: 10 })
      const { validationRules } = useValidationRules(() => schemaRef.value)

      // Initial state - 3 rules
      expect(validationRules.value.length).toBe(3)

      // Remove all constraints
      schemaRef.value = {}

      // No rules should remain
      expect(validationRules.value.length).toBe(0)
    })

    it('updates error messages when schema changes', () => {
      const schemaRef = ref({ required: true, errorMessage: 'Initial message' })
      const { validationRules } = useValidationRules(() => schemaRef.value)

      // Initial error message
      expect(validationRules.value[0](null)).toBe('Initial message')

      // Update error message
      schemaRef.value = { required: true, errorMessage: 'Updated message' }

      // Should use new message
      expect(validationRules.value[0](null)).toBe('Updated message')
    })

    it('updates constraint values reactively', () => {
      const schemaRef = ref({ minimum: 10 })
      const { validationRules } = useValidationRules(() => schemaRef.value)

      // Initial constraint
      expect(validationRules.value[0](5)).toBe('Minimum value: 10')

      // Update minimum value
      schemaRef.value = { minimum: 20 }

      // Should validate against new minimum
      expect(validationRules.value[0](15)).toBe('Minimum value: 20')
    })
  })

  describe('edge cases', () => {
    it('handles undefined schema gracefully', () => {
      const schemaRef = ref(undefined)
      const { validationRules } = useValidationRules(() => schemaRef.value || {})
      expect(validationRules.value.length).toBe(0)
    })

    it('handles empty object schema', () => {
      const rules = getRules({})
      expect(rules.length).toBe(0)
    })

    it('handles zero as valid number value', () => {
      const rules = getRules({ required: true, minimum: 0, maximum: 10 })
      expect(rules[0](0)).toBe(true)
      expect(rules[1](0)).toBe(true)
      expect(rules[2](0)).toBe(true)
    })

    it('handles negative numbers correctly', () => {
      const rules = getRules({ minimum: -10, maximum: -5 })
      expect(rules[0](-7)).toBe(true)
      expect(rules[0](-11)).toBe('Minimum value: -10')
      expect(rules[1](-4)).toBe('Maximum value: -5')
    })

    it('handles single character strings', () => {
      const rules = getRules({ minLength: 1, maxLength: 1 })
      expect(rules[0]('a')).toBe(true)
      expect(rules[0]('')).toBe(true) // Empty skips minLength
      expect(rules[1]('ab')).toBe('Maximum 1 characters')
    })

    it('handles whitespace strings for required', () => {
      const rules = getRules({ required: true })
      // Empty string fails
      expect(rules[0]('')).toBe('Required')
      // Whitespace is considered a value
      expect(rules[0](' ')).toBe(true)
    })
  })
})
