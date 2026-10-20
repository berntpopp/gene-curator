import type { Schema } from '@/types/api'
import type { FieldValidation, FieldValidationMessage, FormValidationResult } from './types'

type Raw = Record<string, unknown>

function toMessages(items: unknown): FieldValidationMessage[] {
  if (!Array.isArray(items)) return []
  return (items as Raw[]).map(item => ({
    message: String(item.message ?? ''),
    ...(typeof item.field === 'string' && { field: item.field })
  }))
}

/**
 * Narrow the backend validation response (untyped error dicts) to what the form renders.
 * Keys the response did not carry stay absent.
 */
export function toFormValidation(raw: Partial<Schema<'ValidationResponse'>>): FormValidationResult {
  const result: FormValidationResult = {}
  if (raw.is_valid !== undefined) result.is_valid = raw.is_valid
  if (raw.errors) result.errors = toMessages(raw.errors)
  if (raw.warnings) result.warnings = toMessages(raw.warnings)
  if (raw.score_calculations) result.score_calculations = raw.score_calculations
  if (raw.field_validations) {
    result.field_validations = {}
    for (const [field, validation] of Object.entries(raw.field_validations)) {
      const entry: FieldValidation = {}
      if (typeof validation.is_valid === 'boolean') entry.is_valid = validation.is_valid
      if (validation.errors) entry.errors = toMessages(validation.errors)
      if (validation.warnings) entry.warnings = toMessages(validation.warnings)
      result.field_validations[field] = entry
    }
  }
  return result
}
