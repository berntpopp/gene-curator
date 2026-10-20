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
    getSchemaUsageStatistics: vi.fn(),
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
      ] as never
      store.workflowPairs = [pair('w1')] as never

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
    it('stores schemas from the wrapped response', async () => {
      const store = useSchemasStore()
      api.getSchemas.mockResolvedValue({ schemas: [schema('a')] })

      const result = await store.fetchSchemas({ active: true })

      expect(api.getSchemas).toHaveBeenCalledWith({ active: true })
      expect(store.schemas.map(s => s.id)).toEqual(['a'])
      expect(result).toEqual({ schemas: [schema('a')] })
      expect(store.loading).toBe(false)
    })

    it('accepts a bare array response', async () => {
      const store = useSchemasStore()
      api.getSchemas.mockResolvedValue([schema('bare')])

      await store.fetchSchemas()

      expect(store.schemas.map(s => s.id)).toEqual(['bare'])
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
      store.schemas = [schema('a', { name: 'old' })] as never

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

      await expect(store.createSchema({} as never)).resolves.toEqual(schema('n'))
      expect(store.schemas.map(s => s.id)).toEqual(['n'])
    })

    it('createSchema records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.createSchema.mockRejectedValue(new Error('invalid'))

      await expect(store.createSchema({} as never)).rejects.toThrow('invalid')
      expect(store.error).toBe('invalid')
    })

    it('updateSchema replaces list and current entries', async () => {
      const store = useSchemasStore()
      store.schemas = [schema('a')] as never
      store.currentSchema = schema('a')
      api.updateSchema.mockResolvedValue(schema('a', { name: 'upd' }))

      await store.updateSchema('a', {} as never)

      expect(store.schemas[0]).toMatchObject({ name: 'upd' })
      expect(store.currentSchema).toMatchObject({ name: 'upd' })
    })

    it('updateSchema records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.updateSchema.mockRejectedValue(new Error('locked'))

      await expect(store.updateSchema('a', {} as never)).rejects.toThrow('locked')
      expect(store.error).toBe('locked')
    })

    it('deleteSchema removes the entry and clears current when matching', async () => {
      const store = useSchemasStore()
      store.schemas = [schema('a'), schema('b')] as never
      store.currentSchema = schema('a')
      api.deleteSchema.mockResolvedValue({} as never)

      await expect(store.deleteSchema('a')).resolves.toBe(true)

      expect(store.schemas.map(s => s.id)).toEqual(['b'])
      expect(store.currentSchema).toBeNull()
    })

    it('deleteSchema keeps an unrelated current schema and records errors', async () => {
      const store = useSchemasStore()
      store.currentSchema = schema('keep')
      api.deleteSchema.mockResolvedValueOnce({} as never)
      await store.deleteSchema('a')
      expect(store.currentSchema).toMatchObject({ id: 'keep' })

      api.deleteSchema.mockRejectedValueOnce(new Error('in use'))
      await expect(store.deleteSchema('a')).rejects.toThrow('in use')
      expect(store.error).toBe('in use')
    })
  })

  describe('usage statistics', () => {
    it('stores statistics per schema id', async () => {
      const store = useSchemasStore()
      api.getSchemaUsageStatistics.mockResolvedValue({ curations: 4 })

      await expect(store.fetchSchemaUsageStatistics('a')).resolves.toEqual({ curations: 4 })
      expect(store.schemaUsageStatistics.a).toEqual({ curations: 4 })
    })

    it('records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.getSchemaUsageStatistics.mockRejectedValue(new Error('stats'))

      await expect(store.fetchSchemaUsageStatistics('a')).rejects.toThrow('stats')
      expect(store.error).toBe('stats')
    })
  })

  describe('workflow pairs', () => {
    it('fetchWorkflowPairs stores pairs from either response shape', async () => {
      const store = useSchemasStore()
      api.getWorkflowPairs.mockResolvedValueOnce({ workflow_pairs: [pair('w1')] })
      await store.fetchWorkflowPairs({ active: true })
      expect(api.getWorkflowPairs).toHaveBeenCalledWith({ active: true })
      expect(store.workflowPairs.map(p => p.id)).toEqual(['w1'])

      api.getWorkflowPairs.mockResolvedValueOnce([pair('w2')])
      await store.fetchWorkflowPairs()
      expect(store.workflowPairs.map(p => p.id)).toEqual(['w2'])
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

      await expect(store.createWorkflowPair({} as never)).resolves.toEqual(pair('w1'))
      expect(store.workflowPairs.map(p => p.id)).toEqual(['w1'])
    })

    it('createWorkflowPair records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.createWorkflowPair.mockRejectedValue(new Error('bad pair'))

      await expect(store.createWorkflowPair({} as never)).rejects.toThrow('bad pair')
      expect(store.error).toBe('bad pair')
    })

    it('updateWorkflowPair replaces list and current entries', async () => {
      const store = useSchemasStore()
      store.workflowPairs = [pair('w1')] as never
      store.currentWorkflowPair = pair('w1')
      api.updateWorkflowPair.mockResolvedValue({ id: 'w1', name: 'renamed' })

      await store.updateWorkflowPair('w1', {} as never)

      expect(store.workflowPairs[0]).toMatchObject({ name: 'renamed' })
      expect(store.currentWorkflowPair).toMatchObject({ name: 'renamed' })
    })

    it('updateWorkflowPair records errors and rethrows', async () => {
      const store = useSchemasStore()
      api.updateWorkflowPair.mockRejectedValue(new Error('upd'))

      await expect(store.updateWorkflowPair('w1', {} as never)).rejects.toThrow('upd')
      expect(store.error).toBe('upd')
    })

    it('deleteWorkflowPair removes the pair and clears current when matching', async () => {
      const store = useSchemasStore()
      store.workflowPairs = [pair('w1'), pair('w2')] as never
      store.currentWorkflowPair = pair('w1')
      api.deleteWorkflowPair.mockResolvedValue({} as never)

      await expect(store.deleteWorkflowPair('w1')).resolves.toBe(true)

      expect(store.workflowPairs.map(p => p.id)).toEqual(['w2'])
      expect(store.currentWorkflowPair).toBeNull()
    })

    it('deleteWorkflowPair keeps an unrelated current pair and records errors', async () => {
      const store = useSchemasStore()
      store.currentWorkflowPair = pair('keep')
      api.deleteWorkflowPair.mockResolvedValueOnce({} as never)
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
