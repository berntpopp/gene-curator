/**
 * Schema Transformer Utility
 *
 * Handles transformation between backend and frontend schema formats.
 * Implements defensive programming with null safety and sensible defaults.
 *
 * Backend uses: schema_type, is_active
 * Frontend uses: type, status
 *
 * @module utils/schemaTransformer
 * @see .planning/milestones/pre-gsd/plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */

/** Backend schema as received from the API, plus the frontend-only fields */
export interface SchemaLike {
  schema_type?: string | null
  type?: string | null
  is_active?: boolean | null
  status?: string | null
  name?: string | null
  version?: string | null
  description?: string | null
  [key: string]: unknown
}

export interface TransformedSchema extends SchemaLike {
  type: string
  status: string
  name: string
  version: string
  description: string
}

/**
 * Default values for missing schema fields
 */
const SCHEMA_DEFAULTS = {
  name: 'Unnamed Schema',
  version: '1.0.0',
  description: '',
  type: 'unknown',
  status: 'inactive'
} as const

/**
 * Transform a single backend schema to frontend format
 *
 * @returns Transformed schema or null if input is null/undefined
 *
 * @example
 * const transformed = transformSchema({ schema_type: 'curation', is_active: true })
 * // Returns: { type: 'curation', status: 'active', ... }
 */
export const transformSchema = (
  schema: SchemaLike | null | undefined
): TransformedSchema | null => {
  if (!schema) return null

  const status = schema.is_active ? 'active' : 'inactive'

  return {
    ...schema,
    // Map schema_type to type (frontend expects 'type')
    type: schema.schema_type || schema.type || SCHEMA_DEFAULTS.type,
    // Derive status from is_active flag
    status,
    // Ensure required fields have defaults
    name: schema.name || SCHEMA_DEFAULTS.name,
    version: schema.version || SCHEMA_DEFAULTS.version,
    description: schema.description || SCHEMA_DEFAULTS.description
  }
}

/**
 * Transform an array of backend schemas to frontend format
 *
 * @returns Array of transformed schemas (empty array if input is invalid)
 *
 * @example
 * const transformed = transformSchemas([{ schema_type: 'curation' }])
 */
export const transformSchemas = (schemas: SchemaLike[] | null | undefined): TransformedSchema[] => {
  if (!Array.isArray(schemas)) return []
  return schemas.map(transformSchema).filter((s): s is TransformedSchema => Boolean(s))
}

/**
 * Transform frontend schema format back to backend format for API calls
 *
 * @returns Backend-compatible schema object
 *
 * @example
 * const apiData = prepareSchemaForAPI({ type: 'curation', status: 'active' })
 * // Returns: { schema_type: 'curation', is_active: true, ... }
 */
export const prepareSchemaForAPI = (schema: SchemaLike | null | undefined): SchemaLike => {
  if (!schema) return {}

  const { type, status, ...rest } = schema

  return {
    ...rest,
    schema_type: type || schema.schema_type,
    is_active: status === 'active'
  }
}

/**
 * Safely format a type string for display
 *
 * @returns Formatted type string (capitalized) or 'Unknown'
 *
 * @example
 * formatType('curation') // Returns: 'Curation'
 * formatType(null) // Returns: 'Unknown'
 */
export const formatType = (type: string | null | undefined): string => {
  if (!type || typeof type !== 'string') return 'Unknown'
  return type.charAt(0).toUpperCase() + type.slice(1)
}

export default {
  transformSchema,
  transformSchemas,
  prepareSchemaForAPI,
  formatType,
  SCHEMA_DEFAULTS
}
