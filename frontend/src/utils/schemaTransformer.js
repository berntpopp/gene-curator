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
 * @see plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */

/**
 * Default values for missing schema fields
 * @type {Object}
 */
const SCHEMA_DEFAULTS = {
  name: 'Unnamed Schema',
  version: '1.0.0',
  description: '',
  type: 'unknown',
  status: 'draft'
}

/**
 * Transform a single backend schema to frontend format
 *
 * @param {Object|null} schema - Backend schema object
 * @returns {Object|null} Transformed schema or null if input is null/undefined
 *
 * @example
 * const transformed = transformSchema({ schema_type: 'curation', is_active: true })
 * // Returns: { type: 'curation', status: 'active', ... }
 */
export const transformSchema = schema => {
  if (!schema) return null

  // Derive status from is_active flag
  const status =
    schema.is_active === true ? 'active' : schema.is_active === false ? 'deprecated' : 'draft'

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
 * @param {Array|null} schemas - Array of backend schema objects
 * @returns {Array} Array of transformed schemas (empty array if input is invalid)
 *
 * @example
 * const transformed = transformSchemas([{ schema_type: 'curation' }])
 */
export const transformSchemas = schemas => {
  if (!Array.isArray(schemas)) return []
  return schemas.map(transformSchema).filter(Boolean)
}

/**
 * Transform frontend schema format back to backend format for API calls
 *
 * @param {Object} schema - Frontend schema object
 * @returns {Object} Backend-compatible schema object
 *
 * @example
 * const apiData = prepareSchemaForAPI({ type: 'curation', status: 'active' })
 * // Returns: { schema_type: 'curation', is_active: true, ... }
 */
export const prepareSchemaForAPI = schema => {
  if (!schema) return {}

  // eslint-disable-next-line no-unused-vars
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
 * @param {string|null|undefined} type - Type string to format
 * @returns {string} Formatted type string (capitalized) or 'Unknown'
 *
 * @example
 * formatType('curation') // Returns: 'Curation'
 * formatType(null) // Returns: 'Unknown'
 */
export const formatType = type => {
  if (!type || typeof type !== 'string') return 'Unknown'
  return type.charAt(0).toUpperCase() + type.slice(1)
}

/**
 * Safely format a status string for display
 *
 * @param {string|null|undefined} status - Status string to format
 * @returns {string} Formatted status string (capitalized) or 'Draft'
 *
 * @example
 * formatStatus('active') // Returns: 'Active'
 * formatStatus(undefined) // Returns: 'Draft'
 */
export const formatStatus = status => {
  if (!status || typeof status !== 'string') return 'Draft'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

/**
 * Get color for schema type chip
 *
 * @param {string|null|undefined} type - Schema type
 * @returns {string} Vuetify color name
 */
export const getTypeColor = type => {
  const colorMap = {
    precuration: 'blue',
    curation: 'green',
    combined: 'purple'
  }
  return colorMap[type] || 'grey'
}

/**
 * Get color for schema status chip
 *
 * @param {string|null|undefined} status - Schema status
 * @returns {string} Vuetify color name
 */
export const getStatusColor = status => {
  const colorMap = {
    draft: 'orange',
    active: 'success',
    deprecated: 'error'
  }
  return colorMap[status] || 'grey'
}

export default {
  transformSchema,
  transformSchemas,
  prepareSchemaForAPI,
  formatType,
  formatStatus,
  getTypeColor,
  getStatusColor,
  SCHEMA_DEFAULTS
}
