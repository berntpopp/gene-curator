/**
 * Shared types for the schema-driven form engine (DynamicForm / DynamicField).
 *
 * The JSON schema, tab layout and validation result shapes are produced by the
 * backend schema generator and are not part of the OpenAPI contract in
 * `@/types/api`, so they are described here.
 */

import type { Schema } from '@/types/api'

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
}

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
  score_calculations?: Record<string, number>
}

export interface SectionConfig {
  name: string
  icon?: string
  help_text?: string
  collapsed?: boolean
  /** Dot-notation field paths */
  fields: string[]
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

/** Schema entry offered by SchemaSelector (precuration or curation) */
export interface SchemaOption {
  id: string
  name: string
  description?: string | null
  version: number | string
}

/** Workflow pair linking a precuration and a curation schema */
export interface WorkflowPairOption {
  id?: string
  name: string
  precuration_schema_id: string
  curation_schema_id: string
}

/** Clinical scope offered by ScopeSelector */
export type ScopeOption = Schema<'ScopeListItem'>

/** Vuetify input variants accepted by the field wrappers */
export type FieldVariant =
  | 'outlined'
  | 'plain'
  | 'filled'
  | 'underlined'
  | 'solo'
  | 'solo-inverted'
  | 'solo-filled'

/** Payload of `component-fallback`: a schema-named component was not in the registry. */
export interface ComponentFallbackEvent {
  requestedComponent: string
  fieldName: string
  fallbackType: string
}

/**
 * Scoped logger from `useLogger()`. That composable's JSDoc types its return
 * as a bare `Object`, so components cast it to this interface.
 */
export interface ComponentLogger {
  debug: (message: string, data?: Record<string, unknown>) => void
  info: (message: string, data?: Record<string, unknown>) => void
  warn: (message: string, data?: Record<string, unknown>) => void
  error: (message: string, data?: Record<string, unknown>) => void
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
