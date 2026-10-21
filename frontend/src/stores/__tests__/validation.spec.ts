import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useValidationStore } from '@/stores/validation'
import { validationAPI } from '@/api'
import type { Schema } from '@/types/api'

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

const response = (is_valid: boolean): Schema<'ValidationResponse'> => ({
  is_valid,
  errors: [],
  warnings: [],
  field_validations: {},
  business_rule_violations: [],
  score_calculations: {},
  completeness_score: 1,
  required_fields_missing: [],
  suggested_improvements: []
})

const jsonSchema = (): Schema<'JSONSchemaResponse'> => ({
  json_schema: { type: 'object' },
  field_count: 1,
  validation_rules_count: 0
})

const fieldRequest: Schema<'FieldValidationRequest'> = {
  field_name: 'x',
  field_value: 1,
  field_config: {}
}

describe('useValidationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('looks up stored results, schemas and field types', () => {
      const store = useValidationStore()
      store.validationResults = { k: response(true) }
      store.jsonSchemas = { s: { properties: {} } }
      store.supportedFieldTypes = [{ name: 'text' }, { name: 'number' }]

      expect(store.getValidationResult('k')).toEqual(response(true))
      expect(store.getValidationResult('none')).toBeUndefined()
      expect(store.getJsonSchema('s')).toEqual({ properties: {} })
      expect(store.getSupportedFieldType('number')).toEqual({ name: 'number' })
      expect(store.getSupportedFieldType('none')).toBeUndefined()
    })
  })

  describe('validateEvidence', () => {
    it('stores the result under the key and returns it', async () => {
      const store = useValidationStore()
      api.validateEvidence.mockResolvedValue(response(true))

      const result = await store.validateEvidence({ score: 1 }, 'schema-1', 'custom')

      expect(api.validateEvidence).toHaveBeenCalledWith({
        evidence_data: { score: 1 },
        schema_id: 'schema-1'
      })
      expect(result).toEqual(response(true))
      expect(store.validationResults.custom).toEqual(response(true))

      await store.validateEvidence({ score: 1 }, 'schema-1', 'custom', 'v1')
      expect(api.validateEvidence).toHaveBeenLastCalledWith({
        evidence_data: { score: 1 },
        schema_id: 'schema-1',
        methodology_version_id: 'v1'
      })
      expect(store.loading).toBe(false)
    })

    it('uses the default key when none is given', async () => {
      const store = useValidationStore()
      api.validateEvidence.mockResolvedValue(response(false))

      await store.validateEvidence({}, 's')

      expect(store.validationResults.default).toEqual(response(false))
    })

    it('records the error and rethrows', async () => {
      const store = useValidationStore()
      api.validateEvidence.mockRejectedValue(new Error('bad schema'))

      await expect(store.validateEvidence({}, 's')).rejects.toThrow('bad schema')
      expect(store.error).toBe('bad schema')
      expect(store.loading).toBe(false)
    })

    it('keeps the newest reply when replies land out of order', async () => {
      const store = useValidationStore()
      const replies: Array<(r: Schema<'ValidationResponse'>) => void> = []
      api.validateEvidence.mockImplementation(() => new Promise(r => replies.push(r)))

      const older = store.validateEvidence({ v: 1 }, 's', 'form')
      const newer = store.validateEvidence({ v: 2 }, 's', 'form')
      replies[1]!(response(true))
      await expect(newer).resolves.toEqual(response(true))
      expect(store.loading).toBe(false)
      replies[0]!(response(false))
      await expect(older).resolves.toBeNull()

      expect(store.validationResults.form).toEqual(response(true))
    })

    it('drops a reply that was in flight when the key was cleared', async () => {
      const store = useValidationStore()
      let reply: (r: unknown) => void = () => {}
      api.validateEvidence.mockImplementation(() => new Promise((_, reject) => (reply = reject)))

      const pending = store.validateEvidence({}, 's', 'form')
      store.clearValidationResult('form')
      reply(new Error('late'))

      await expect(pending).resolves.toBeNull()
      expect(store.error).toBeNull()
      expect(store.validationResults.form).toBeUndefined()
    })
  })

  describe('validateSchema and generateJsonSchema', () => {
    it('validateSchema forwards the definition and returns the result', async () => {
      const store = useValidationStore()
      api.validateSchema.mockResolvedValue(response(true))

      await expect(store.validateSchema({ type: 'object' })).resolves.toEqual(response(true))
      expect(api.validateSchema).toHaveBeenCalledWith({ schema_definition: { type: 'object' } })
    })

    it('validateSchema records errors and rethrows', async () => {
      const store = useValidationStore()
      api.validateSchema.mockRejectedValue(new Error('malformed'))

      await expect(store.validateSchema({})).rejects.toThrow('malformed')
      expect(store.error).toBe('malformed')
    })

    it('a second generateJsonSchema for the same id does not call the API', async () => {
      const store = useValidationStore()
      api.generateJsonSchema.mockClear()
      api.generateJsonSchema.mockResolvedValue({ ...jsonSchema(), json_schema: { type: 'object' } })

      const [a, b] = await Promise.all([
        store.generateJsonSchema('dup'),
        store.generateJsonSchema('dup')
      ])
      await store.generateJsonSchema('dup')

      expect(api.generateJsonSchema).toHaveBeenCalledTimes(1)
      expect(a).toBe(b)
    })

    it('generateJsonSchema caches the schema by id', async () => {
      const store = useValidationStore()
      api.generateJsonSchema.mockResolvedValue({
        ...jsonSchema(),
        json_schema: { type: 'object', properties: { a: { type: 'string' } } }
      })

      await store.generateJsonSchema('s1')

      expect(api.generateJsonSchema).toHaveBeenCalledWith('s1')
      expect(store.getJsonSchema('s1')?.properties).toEqual({ a: { type: 'string' } })
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
      api.getSupportedFieldTypes.mockResolvedValue({ text: { description: 'Text input' } })
      const expected = [{ name: 'text', description: 'Text input' }]

      await expect(store.fetchSupportedFieldTypes()).resolves.toEqual(expected)
      await expect(store.fetchSupportedFieldTypes()).resolves.toEqual(expected)

      expect(api.getSupportedFieldTypes).toHaveBeenCalledTimes(1)
      expect(store.supportedFieldTypes).toEqual(expected)
    })

    it('fetchSupportedFieldTypes records errors and rethrows', async () => {
      const store = useValidationStore()
      api.getSupportedFieldTypes.mockRejectedValue(new Error('field types'))

      await expect(store.fetchSupportedFieldTypes()).rejects.toThrow('field types')
      expect(store.error).toBe('field types')
    })

    it('fetchBusinessRules loads once and then serves the cache', async () => {
      const store = useValidationStore()
      api.getBusinessRules.mockResolvedValue({ r1: { description: 'Rule one' } })
      const expected = [{ name: 'r1', description: 'Rule one' }]

      await expect(store.fetchBusinessRules()).resolves.toEqual(expected)
      await expect(store.fetchBusinessRules()).resolves.toEqual(expected)

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
      const outcome: Schema<'FieldValidationResponse'> = {
        field_name: 'x',
        is_valid: true,
        errors: [],
        warnings: [],
        suggestions: []
      }
      api.validateField.mockResolvedValue(outcome)

      await expect(store.validateField(fieldRequest)).resolves.toEqual(outcome)
    })

    it('records the error and rethrows', async () => {
      const store = useValidationStore()
      api.validateField.mockRejectedValue(new Error('field'))

      await expect(store.validateField(fieldRequest)).rejects.toThrow('field')
      expect(store.error).toBe('field')
    })
  })

  describe('clearing', () => {
    it('clears one result, all results, and the error', () => {
      const store = useValidationStore()
      store.validationResults = { a: response(true), b: response(false) }
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
