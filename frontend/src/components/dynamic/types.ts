/**
 * Shared types for the schema-driven form engine (DynamicForm / DynamicField).
 *
 * The JSON schema, tab layout and validation result shapes are produced by the
 * backend schema generator and are not part of the OpenAPI contract in
 * `@/types/api`, so they are described here.
 */

/** A single field definition inside a generated JSON schema. */
export interface FieldSchema {
  type?: string
  title?: string
  label?: string
  description?: string
  hint?: string
  tooltip?: string
  icon?: string
  helpUrl?: string
  placeholder?: string
  multiline?: boolean
  rows?: number
  format?: string
  required?: boolean
  minimum?: number
  maximum?: number
  minLength?: number
  maxLength?: number
  pattern?: string
  step?: number
  default?: unknown
  /** Starting numeric suggestion selected by another column; never replaces manual input. */
  default_by?: { field: string; values: Record<string, number> }
  errorMessage?: string
  enum?: Array<string | number>
  enumOptions?: Array<string | { label?: string; value?: string }>
  /** Name of a component in `componentRegistry` */
  component?: string
  /** Child fields of an `object` type */
  properties?: Record<string, FieldSchema>
  /** Item definition of an `array` type; only `properties` is used */
  items?: { properties?: Record<string, FieldSchema> }
  itemTitle?: string
  /** Shown but not editable (e.g. inherited from the previous stage) */
  readOnly?: boolean
  /** `evidence_table` columns; each column is a field */
  columns?: Record<string, FieldSchema>
  /** Show only when the condition holds */
  visible_when?: Condition
  /** Required when the condition holds (in addition to `required`) */
  required_when?: Condition
}

/** `{ path: value }` (equals) or `{ path: [values] }` (in); every entry must hold */
export type Condition = Record<string, unknown>

export interface FieldValidationMessage {
  message: string
  field?: string
}

/** Validation outcome for a single field (keyed by field path). */
export interface FieldValidation {
  is_valid?: boolean
  errors?: FieldValidationMessage[]
  warnings?: FieldValidationMessage[]
}

/** Whole-form validation outcome returned by the validation endpoint. */
export interface FormValidationResult {
  is_valid?: boolean
  errors?: FieldValidationMessage[]
  warnings?: FieldValidationMessage[]
  field_validations?: Record<string, FieldValidation>
  /** Numeric scores plus the live verdict and trace (scorePreview.ts) */
  score_calculations?: Record<string, unknown>
}

export interface SectionConfig {
  name: string
  icon?: string
  help_text?: string
  collapsed?: boolean
  /** Dot-notation field paths */
  fields: string[]
  /** Component-only section, rendered through the form's `section` slot */
  component?: string
}

export interface TabConfig {
  id: string
  name: string
  icon?: string
  show_score_badge?: boolean
  sections: SectionConfig[]
}

export interface ScoringConfiguration {
  engine?: string | null
  classification_thresholds?: Record<string, number>
  max_scores?: Record<string, number>
}

/** Vuetify input variants accepted by the field wrappers */
export type FieldVariant =
  'outlined' | 'plain' | 'filled' | 'underlined' | 'solo' | 'solo-inverted' | 'solo-filled'

/** Payload of `component-fallback`: a schema-named component was not in the registry. */
export interface ComponentFallbackEvent {
  requestedComponent: string
  fieldName: string
  fallbackType: string
}

/** The JSON schema document consumed by DynamicForm. */
export interface JsonSchemaDocument {
  properties?: Record<string, FieldSchema>
  scoring_configuration?: ScoringConfiguration
  ui_configuration?: {
    layout?: {
      type?: string
      tabs?: TabConfig[]
    }
  }
}
