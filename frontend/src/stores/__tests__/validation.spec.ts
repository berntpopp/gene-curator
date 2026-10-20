import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useValidationStore } from '@/stores/validation'
import { validationAPI } from '@/api'

vi.mock('@/api', () => ({
  validationAPI: {
    validateEvidence: vi.fn(),
    validateSchema: vi.fn(),
    generateJsonSchema: vi.fn(),
    getSupportedFieldTypes: vi.fn(),
    getBusinessRules: vi.fn(),
    validateField: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(validationAPI)

describe('useValidationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('looks up stored results, schemas and field types', () => {
      const store = useValidationStore()
      store.validationResults = { k: { is_valid: true } as never }
      store.jsonSchemas = { s: { json_schema: {} } as never }
      store.supportedFieldTypes = [{ name: 'text' }, { name: 'number' }]

      expect(store.getValidationResult('k')).toEqual({ is_valid: true })
      expect(store.getValidationResult('none')).toBeUndefined()
      expect(store.getJsonSchema('s')).toEqual({ json_schema: {} })
      expect(store.getSupportedFieldType('number')).toEqual({ name: 'number' })
      expect(store.getSupportedFieldType('none')).toBeUndefined()
    })
  })

  describe('validateEvidence', () => {
    it('stores the result under the key and returns it', async () => {
      const store = useValidationStore()
      api.validateEvidence.mockResolvedValue({ is_valid: true })

      const result = await store.validateEvidence({ score: 1 }, 'schema-1', 'custom')

      expect(api.validateEvidence).toHaveBeenCalledWith({
        evidence_data: { score: 1 },
        schema_id: 'schema-1'
      })
      expect(result).toEqual({ is_valid: true })
      expect(store.validationResults.custom).toEqual({ is_valid: true })
      expect(store.loading).toBe(false)
    })

    it('uses the default key when none is given', async () => {
      const store = useValidationStore()
      api.validateEvidence.mockResolvedValue({ is_valid: false })

      await store.validateEvidence({}, 's')

      expect(store.validationResults.default).toEqual({ is_valid: false })
    })

    it('records the error and rethrows', async () => {
      const store = useValidationStore()
      api.validateEvidence.mockRejectedValue(new Error('bad schema'))

      await expect(store.validateEvidence({}, 's')).rejects.toThrow('bad schema')
      expect(store.error).toBe('bad schema')
      expect(store.loading).toBe(false)
    })
  })

  describe('validateSchema and generateJsonSchema', () => {
    it('validateSchema forwards the definition and returns the result', async () => {
      const store = useValidationStore()
      api.validateSchema.mockResolvedValue({ valid: true })

      await expect(store.validateSchema({ type: 'object' })).resolves.toEqual({ valid: true })
      expect(api.validateSchema).toHaveBeenCalledWith({ schema_definition: { type: 'object' } })
    })

    it('validateSchema records errors and rethrows', async () => {
      const store = useValidationStore()
      api.validateSchema.mockRejectedValue(new Error('malformed'))

      await expect(store.validateSchema({})).rejects.toThrow('malformed')
      expect(store.error).toBe('malformed')
    })

    it('generateJsonSchema caches the schema by id', async () => {
      const store = useValidationStore()
      api.generateJsonSchema.mockResolvedValue({ json_schema: { type: 'object' } })

      await store.generateJsonSchema('s1')

      expect(api.generateJsonSchema).toHaveBeenCalledWith('s1')
      expect(store.jsonSchemas.s1).toEqual({ json_schema: { type: 'object' } })
    })

    it('generateJsonSchema records errors and rethrows', async () => {
      const store = useValidationStore()
      api.generateJsonSchema.mockRejectedValue(new Error('no schema'))

      await expect(store.generateJsonSchema('s1')).rejects.toThrow('no schema')
      expect(store.error).toBe('no schema')
    })
  })

  describe('cached catalog fetches', () => {
    it('fetchSupportedFieldTypes loads once and then serves the cache', async () => {
      const store = useValidationStore()
      api.getSupportedFieldTypes.mockResolvedValue([{ name: 'text' }])

      await expect(store.fetchSupportedFieldTypes()).resolves.toEqual([{ name: 'text' }])
      await expect(store.fetchSupportedFieldTypes()).resolves.toEqual([{ name: 'text' }])

      expect(api.getSupportedFieldTypes).toHaveBeenCalledTimes(1)
      expect(store.supportedFieldTypes).toEqual([{ name: 'text' }])
    })

    it('fetchSupportedFieldTypes records errors and rethrows', async () => {
      const store = useValidationStore()
      api.getSupportedFieldTypes.mockRejectedValue(new Error('field types'))

      await expect(store.fetchSupportedFieldTypes()).rejects.toThrow('field types')
      expect(store.error).toBe('field types')
    })

    it('fetchBusinessRules loads once and then serves the cache', async () => {
      const store = useValidationStore()
      api.getBusinessRules.mockResolvedValue([{ rule: 'r1' }])

      await expect(store.fetchBusinessRules()).resolves.toEqual([{ rule: 'r1' }])
      await expect(store.fetchBusinessRules()).resolves.toEqual([{ rule: 'r1' }])

      expect(api.getBusinessRules).toHaveBeenCalledTimes(1)
    })

    it('fetchBusinessRules records errors and rethrows', async () => {
      const store = useValidationStore()
      api.getBusinessRules.mockRejectedValue(new Error('rules'))

      await expect(store.fetchBusinessRules()).rejects.toThrow('rules')
      expect(store.error).toBe('rules')
    })
  })

  describe('validateField', () => {
    it('returns the field validation result', async () => {
      const store = useValidationStore()
      api.validateField.mockResolvedValue({ is_valid: true, errors: [] })

      await expect(store.validateField({ field: 'x' } as never)).resolves.toEqual({
        is_valid: true,
        errors: []
      })
    })

    it('records the error and rethrows', async () => {
      const store = useValidationStore()
      api.validateField.mockRejectedValue(new Error('field'))

      await expect(store.validateField({} as never)).rejects.toThrow('field')
      expect(store.error).toBe('field')
    })
  })

  describe('clearing', () => {
    it('clears one result, all results, and the error', () => {
      const store = useValidationStore()
      store.validationResults = { a: { is_valid: true } as never, b: { is_valid: false } as never }
      store.error = 'x'

      store.clearValidationResult('a')
      expect(Object.keys(store.validationResults)).toEqual(['b'])

      store.clearValidationResult('missing')
      expect(Object.keys(store.validationResults)).toEqual(['b'])

      store.clearAllValidationResults()
      expect(store.validationResults).toEqual({})

      store.clearError()
      expect(store.error).toBeNull()
    })
  })
})
