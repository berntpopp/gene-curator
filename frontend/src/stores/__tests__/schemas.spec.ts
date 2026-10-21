import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Schema } from '@/types/api'
import { setActivePinia, createPinia } from 'pinia'
import { useSchemasStore } from '@/stores/schemas'
import { schemasAPI } from '@/api'

vi.mock('@/api', () => ({
  schemasAPI: {
    getSchemas: vi.fn(),
    getSchemaById: vi.fn(),
    createSchema: vi.fn(),
    updateSchema: vi.fn(),
    deleteSchema: vi.fn(),
    validateCurationSchema: vi.fn(),
    getWorkflowPairs: vi.fn(),
    createWorkflowPair: vi.fn(),
    updateWorkflowPair: vi.fn(),
    deleteWorkflowPair: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(schemasAPI)

const schema = (id: string, extra: Record<string, unknown> = {}) =>
  ({ id, name: id, ...extra }) as Schema<'CurationSchema'>
const pair = (id: string) => ({ id, name: `pair-${id}` }) as Schema<'WorkflowPair'>

const newSchema: Schema<'CurationSchemaCreate'> = {
  name: 's',
  version: '1',
  schema_type: 'curation',
  field_definitions: {},
  workflow_states: {},
  ui_configuration: {},
  is_active: true,
  use_dynamic_form: true
}

const newPair: Schema<'WorkflowPairCreate'> = {
  name: 'p',
  version: '1',
  precuration_schema_id: 'a',
  curation_schema_id: 'b',
  is_active: true
}

describe('useSchemasStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('finds and filters schemas by type', () => {
      const store = useSchemasStore()
      store.schemas = [
        schema('a', { schema_type: 'precuration' }),
        schema('b', { schema_type: 'curation' }),
        schema('c', { schema_type: 'combined' })
      ]
      store.workflowPairs = [pair('w1')]

      expect(store.getSchemaById('b')).toMatchObject({ id: 'b' })
      expect(store.getSchemaById('none')).toBeUndefined()
      expect(store.getSchemasByType('curation').map(s => s.id)).toEqual(['b'])
      expect(store.getPrecurationSchemas.map(s => s.id)).toEqual(['a', 'c'])
      expect(store.getCurationSchemas.map(s => s.id)).toEqual(['b', 'c'])
      expect(store.getWorkflowPairById('w1')).toMatchObject({ id: 'w1' })
      expect(store.getWorkflowPairById('zz')).toBeUndefined()
    })
  })

  describe('fetchSchemas', () => {
    it('stores the schema list', async () => {
      const store = useSchemasStore()
      api.getSchemas.mockResolvedValue([schema('a')])

      const result = await store.fetchSchemas({ active: true })

      expect(api.getSchemas).toHaveBeenCalledWith({ active: true })
      expect(store.schemas.map(s => s.id)).toEqual(['a'])
      expect(result).toEqual([schema('a')])
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows', async () => {
      const store = useSchemasStore()
      api.getSchemas.mockRejectedValue(new Error('down'))

      await expect(store.fetchSchemas()).rejects.toThrow('down')
      expect(store.error).toBe('down')
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchSchemaById', () => {
    it('sets current schema and replaces or appends the list entry', async () => {
      const store = useSchemasStore()
      store.schemas = [schema('a', { name: 'old' })]

      api.getSchemaById.mockResolvedValueOnce(schema('a', { name: 'new' }))
      await store.fetchSchemaById('a')
      expect(store.currentSchema).toMatchObject({ name: 'new' })
      expect(store.schemas[0]).toMatchObject({ name: 'new' })

      api.getSchemaById.mockResolvedValueOnce(schema('b'))
      await store.fetchSchemaById('b')
      expect(store.schemas.map(s => s.id)).toEqual(['a', 'b'])
    })

    it('records the error and rethrows', async () => {
      const store = useSchemasStore()
      api.getSchemaById.mockRejectedValue(new Error('404'))

      await expect(store.fetchSchemaById('x')).rejects.toThrow('404')
      expect(store.error).toBe('404')
    })
  })

  describe('createSchema / updateSchema / deleteSchema', () => {
    it('createSchema appends the new schema', async () => {
      const store = useSchemasStore()
      api.createSchema.mockResolvedValue(schema('n'))

      await expect(store.createSchema(newSchema)).resolves.toEqual(schema('n'))
      expect(store.schemas.map(s => s.id)).toEqual(['n'])
    })

    it('createSchema records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.createSchema.mockRejectedValue(new Error('invalid'))

      await expect(store.createSchema(newSchema)).rejects.toThrow('invalid')
      expect(store.error).toBe('invalid')
    })

    it('updateSchema replaces list and current entries', async () => {
      const store = useSchemasStore()
      store.schemas = [schema('a')]
      store.currentSchema = schema('a')
      api.updateSchema.mockResolvedValue(schema('a', { name: 'upd' }))

      await store.updateSchema('a', {})

      expect(store.schemas[0]).toMatchObject({ name: 'upd' })
      expect(store.currentSchema).toMatchObject({ name: 'upd' })
    })

    it('updateSchema records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.updateSchema.mockRejectedValue(new Error('locked'))

      await expect(store.updateSchema('a', {})).rejects.toThrow('locked')
      expect(store.error).toBe('locked')
    })

    it('deleteSchema removes the entry and clears current when matching', async () => {
      const store = useSchemasStore()
      store.schemas = [schema('a'), schema('b')]
      store.currentSchema = schema('a')
      api.deleteSchema.mockResolvedValue({})

      await expect(store.deleteSchema('a')).resolves.toBe(true)

      expect(store.schemas.map(s => s.id)).toEqual(['b'])
      expect(store.currentSchema).toBeNull()
    })

    it('deleteSchema keeps an unrelated current schema and records errors', async () => {
      const store = useSchemasStore()
      store.currentSchema = schema('keep')
      api.deleteSchema.mockResolvedValueOnce({})
      await store.deleteSchema('a')
      expect(store.currentSchema).toMatchObject({ id: 'keep' })

      api.deleteSchema.mockRejectedValueOnce(new Error('in use'))
      await expect(store.deleteSchema('a')).rejects.toThrow('in use')
      expect(store.error).toBe('in use')
    })
  })

  describe('validateSchema', () => {
    it('validates a stored schema server-side', async () => {
      const store = useSchemasStore()
      const outcome = { is_valid: true } as Schema<'SchemaValidationResult'>
      api.validateCurationSchema.mockResolvedValue(outcome)

      await expect(store.validateSchema('a')).resolves.toBe(outcome)
      expect(api.validateCurationSchema).toHaveBeenCalledWith('a')
    })

    it('records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.validateCurationSchema.mockRejectedValue(new Error('invalid'))

      await expect(store.validateSchema('a')).rejects.toThrow('invalid')
      expect(store.error).toBe('invalid')
    })
  })

  describe('duplicateSchema', () => {
    it('creates an inactive copy with a bumped patch version and the original name', async () => {
      const store = useSchemasStore()
      api.getSchemaById.mockResolvedValue(
        schema('a', { name: 'orig', version: '1.0.0', is_active: true, schema_hash: 'h' })
      )
      api.createSchema.mockResolvedValue(schema('b', { name: 'orig' }))

      const copy = await store.duplicateSchema('a')

      const sent = api.createSchema.mock.calls[0]?.[0]
      expect(sent).toMatchObject({ name: 'orig', version: '1.0.1', is_active: false })
      expect(sent).not.toHaveProperty('id')
      expect(sent).not.toHaveProperty('schema_hash')
      expect(copy.id).toBe('b')
      expect(store.schemas.map(s => s.id)).toEqual(['b'])
    })

    it('appends .1 when the version has no numeric patch', async () => {
      const store = useSchemasStore()
      api.getSchemaById.mockResolvedValue(schema('a', { version: '11.0-beta' }))
      api.createSchema.mockResolvedValue(schema('b'))

      await store.duplicateSchema('a')

      expect(api.createSchema.mock.calls[0]?.[0]).toMatchObject({ version: '11.0-beta.1' })
    })
  })

  describe('workflow pairs', () => {
    it('fetchWorkflowPairs stores the pairs', async () => {
      const store = useSchemasStore()
      api.getWorkflowPairs.mockResolvedValueOnce([pair('w1')])
      await store.fetchWorkflowPairs({ active: true })
      expect(api.getWorkflowPairs).toHaveBeenCalledWith({ active: true })
      expect(store.workflowPairs.map(p => p.id)).toEqual(['w1'])
    })

    it('fetchWorkflowPairs records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.getWorkflowPairs.mockRejectedValue(new Error('wp'))

      await expect(store.fetchWorkflowPairs()).rejects.toThrow('wp')
      expect(store.error).toBe('wp')
      expect(store.loading).toBe(false)
    })

    it('createWorkflowPair appends the new pair', async () => {
      const store = useSchemasStore()
      api.createWorkflowPair.mockResolvedValue(pair('w1'))

      await expect(store.createWorkflowPair(newPair)).resolves.toEqual(pair('w1'))
      expect(store.workflowPairs.map(p => p.id)).toEqual(['w1'])
    })

    it('createWorkflowPair records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.createWorkflowPair.mockRejectedValue(new Error('bad pair'))

      await expect(store.createWorkflowPair(newPair)).rejects.toThrow('bad pair')
      expect(store.error).toBe('bad pair')
    })

    it('updateWorkflowPair replaces list and current entries', async () => {
      const store = useSchemasStore()
      store.workflowPairs = [pair('w1')]
      store.currentWorkflowPair = pair('w1')
      api.updateWorkflowPair.mockResolvedValue({ ...pair('w1'), name: 'renamed' })

      await store.updateWorkflowPair('w1', {})

      expect(store.workflowPairs[0]).toMatchObject({ name: 'renamed' })
      expect(store.currentWorkflowPair).toMatchObject({ name: 'renamed' })
    })

    it('updateWorkflowPair records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.updateWorkflowPair.mockRejectedValue(new Error('upd'))

      await expect(store.updateWorkflowPair('w1', {})).rejects.toThrow('upd')
      expect(store.error).toBe('upd')
    })

    it('deleteWorkflowPair removes the pair and clears current when matching', async () => {
      const store = useSchemasStore()
      store.workflowPairs = [pair('w1'), pair('w2')]
      store.currentWorkflowPair = pair('w1')
      api.deleteWorkflowPair.mockResolvedValue({})

      await expect(store.deleteWorkflowPair('w1')).resolves.toBe(true)

      expect(store.workflowPairs.map(p => p.id)).toEqual(['w2'])
      expect(store.currentWorkflowPair).toBeNull()
    })

    it('deleteWorkflowPair keeps an unrelated current pair and records errors', async () => {
      const store = useSchemasStore()
      store.currentWorkflowPair = pair('keep')
      api.deleteWorkflowPair.mockResolvedValueOnce({})
      await store.deleteWorkflowPair('w1')
      expect(store.currentWorkflowPair).toMatchObject({ id: 'keep' })

      api.deleteWorkflowPair.mockRejectedValueOnce(new Error('used'))
      await expect(store.deleteWorkflowPair('w1')).rejects.toThrow('used')
      expect(store.error).toBe('used')
    })
  })

  describe('local state actions', () => {
    it('setters and clearers update current selections', () => {
      const store = useSchemasStore()
      store.setCurrentSchema(schema('a'))
      expect(store.currentSchema).toMatchObject({ id: 'a' })
      store.clearCurrentSchema()
      expect(store.currentSchema).toBeNull()

      store.setCurrentWorkflowPair(pair('w1'))
      expect(store.currentWorkflowPair).toMatchObject({ id: 'w1' })
    })

    it('clearError resets the error', () => {
      const store = useSchemasStore()
      store.error = 'x'
      store.clearError()
      expect(store.error).toBeNull()
    })
  })
})
