import { describe, it, expect } from 'vitest'
import {
  transformSchema,
  transformSchemas,
  prepareSchemaForAPI,
  formatType,
  formatStatus,
  getTypeColor,
  getStatusColor
} from '../schemaTransformer'
import defaultExport from '../schemaTransformer'

const { SCHEMA_DEFAULTS } = defaultExport

describe('schemaTransformer', () => {
  describe('transformSchema', () => {
    it('maps schema_type to type and is_active to status', () => {
      expect(
        transformSchema({ schema_type: 'curation', is_active: true, name: 'S' })
      ).toMatchObject({
        type: 'curation',
        status: 'active',
        name: 'S'
      })
      expect(transformSchema({ schema_type: 'precuration', is_active: false })).toMatchObject({
        type: 'precuration',
        status: 'deprecated'
      })
    })

    it('treats a missing is_active flag as draft', () => {
      expect(transformSchema({ schema_type: 'combined' })).toMatchObject({ status: 'draft' })
    })

    it('fills missing name, version and description with defaults', () => {
      expect(transformSchema({})).toEqual({
        type: SCHEMA_DEFAULTS.type,
        status: 'draft',
        name: SCHEMA_DEFAULTS.name,
        version: SCHEMA_DEFAULTS.version,
        description: SCHEMA_DEFAULTS.description
      })
    })

    it('keeps an existing frontend type when schema_type is absent', () => {
      expect(transformSchema({ type: 'curation' })).toMatchObject({ type: 'curation' })
    })

    it('returns null for null and undefined input', () => {
      expect(transformSchema(null)).toBeNull()
      expect(transformSchema(undefined)).toBeNull()
    })
  })

  describe('transformSchemas', () => {
    it('transforms every item and drops nothing that is valid', () => {
      const result = transformSchemas([{ schema_type: 'curation' }, { is_active: true }])

      expect(result.map(s => s.type)).toEqual(['curation', SCHEMA_DEFAULTS.type])
    })

    it('returns an empty array for non-array input', () => {
      expect(transformSchemas(null)).toEqual([])
      expect(transformSchemas(undefined)).toEqual([])
    })
  })

  describe('prepareSchemaForAPI', () => {
    it('maps type and status back to the backend fields', () => {
      expect(prepareSchemaForAPI({ type: 'curation', status: 'active', name: 'S' })).toEqual({
        name: 'S',
        schema_type: 'curation',
        is_active: true
      })
    })

    it('marks anything not active as inactive and keeps an existing schema_type', () => {
      expect(prepareSchemaForAPI({ schema_type: 'precuration', status: 'draft' })).toEqual({
        schema_type: 'precuration',
        is_active: false
      })
    })

    it('returns an empty object for null input', () => {
      expect(prepareSchemaForAPI(null)).toEqual({})
    })
  })

  describe('display helpers', () => {
    it('formatType capitalises and falls back to Unknown', () => {
      expect(formatType('curation')).toBe('Curation')
      expect(formatType('')).toBe('Unknown')
      expect(formatType(null)).toBe('Unknown')
    })

    it('formatStatus capitalises and falls back to Draft', () => {
      expect(formatStatus('active')).toBe('Active')
      expect(formatStatus(undefined)).toBe('Draft')
    })

    it('getTypeColor maps known types and defaults to grey', () => {
      expect(getTypeColor('precuration')).toBe('blue')
      expect(getTypeColor('curation')).toBe('green')
      expect(getTypeColor('combined')).toBe('purple')
      expect(getTypeColor('other')).toBe('grey')
      expect(getTypeColor(null)).toBe('grey')
    })

    it('getStatusColor maps known statuses and defaults to grey', () => {
      expect(getStatusColor('draft')).toBe('orange')
      expect(getStatusColor('active')).toBe('success')
      expect(getStatusColor('deprecated')).toBe('error')
      expect(getStatusColor('unknown')).toBe('grey')
      expect(getStatusColor(undefined)).toBe('grey')
    })
  })

  it('default export bundles the same helpers', () => {
    expect(defaultExport.transformSchema).toBe(transformSchema)
    expect(defaultExport.getStatusColor).toBe(getStatusColor)
    expect(defaultExport.SCHEMA_DEFAULTS).toBe(SCHEMA_DEFAULTS)
  })
})
