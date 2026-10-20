import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Schema } from '@/types/api'
import { setActivePinia, createPinia } from 'pinia'
import { useExternalValidationStore } from '@/stores/externalValidation'
import { externalValidationAPI } from '@/api/externalValidation'
import { logService } from '@/services/logService'

vi.mock('@/api/externalValidation', () => ({
  externalValidationAPI: {
    validateHGNC: vi.fn(),
    validatePubMed: vi.fn(),
    validateHPO: vi.fn(),
    validateBatch: vi.fn(),
    getCacheStatistics: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(externalValidationAPI)

const OK: Schema<'ValidationResult'> = { is_valid: true, status: 'valid' }
const BAD: Schema<'ValidationResult'> = { is_valid: false, status: 'invalid' }
const BRCA1_OK: Schema<'ValidationResult'> = {
  is_valid: true,
  status: 'valid',
  data: { approved_symbol: 'BRCA1' }
}

describe('useExternalValidationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('cache keys and getters', () => {
    it('normalises the cache key by trimming and lower-casing the value', () => {
      const store = useExternalValidationStore()
      expect(store._getCacheKey('hgnc', '  BRCA1 ')).toBe('hgnc:brca1')
    })

    it('reads cached results and validation-in-progress state', () => {
      const store = useExternalValidationStore()
      store.cache.set('hgnc:brca1', OK)
      store.loading.set('pubmed:123', true)

      expect(store.getCachedResult('hgnc', 'BRCA1')).toEqual(OK)
      expect(store.getCachedResult('hgnc', 'unknown')).toBeNull()
      expect(store.isValidating('pubmed', '123')).toBe(true)
      expect(store.isValidating('hpo', 'HP:1')).toBe(false)
    })
  })

  describe('validateHGNC', () => {
    it('validates, caches and returns the result', async () => {
      const store = useExternalValidationStore()
      api.validateHGNC.mockResolvedValue(BRCA1_OK)

      await expect(store.validateHGNC('BRCA1')).resolves.toEqual(BRCA1_OK)
      expect(api.validateHGNC).toHaveBeenCalledWith('BRCA1', false)
      expect(store.cache.get('hgnc:brca1')).toEqual(BRCA1_OK)
      expect(store.loading.has('hgnc:brca1')).toBe(false)
    })

    it('serves the cached result without calling the API', async () => {
      const store = useExternalValidationStore()
      store.cache.set('hgnc:brca1', OK)

      await expect(store.validateHGNC('BRCA1')).resolves.toEqual(OK)
      expect(api.validateHGNC).not.toHaveBeenCalled()
      expect(logService.info).toHaveBeenCalledWith(
        'Validation cache hit',
        expect.objectContaining({ validator: 'hgnc' })
      )
    })

    it('bypasses the cache when skipCache is set', async () => {
      const store = useExternalValidationStore()
      store.cache.set('hgnc:brca1', OK)
      api.validateHGNC.mockResolvedValue(BAD)

      await expect(store.validateHGNC('BRCA1', true)).resolves.toEqual(BAD)
      expect(api.validateHGNC).toHaveBeenCalledWith('BRCA1', true)
      expect(store.cache.get('hgnc:brca1')).toEqual(BAD)
    })

    it('records the error, clears loading and rethrows', async () => {
      const store = useExternalValidationStore()
      api.validateHGNC.mockRejectedValue(new Error('timeout'))

      await expect(store.validateHGNC('BRCA1')).rejects.toThrow('timeout')
      expect(store.error).toBe('timeout')
      expect(store.loading.has('hgnc:brca1')).toBe(false)
      expect(logService.error).toHaveBeenCalledWith(
        'HGNC validation failed',
        expect.objectContaining({ geneSymbol: 'BRCA1', error: 'timeout' })
      )
    })

    it('uses a fallback message when the error has none', async () => {
      const store = useExternalValidationStore()
      api.validateHGNC.mockRejectedValue({})

      await expect(store.validateHGNC('BRCA1')).rejects.toEqual({})
      expect(store.error).toBe('Validation failed')
    })
  })

  describe('validatePubMed', () => {
    it('validates, caches and serves from cache afterwards', async () => {
      const store = useExternalValidationStore()
      api.validatePubMed.mockResolvedValue(OK)

      await store.validatePubMed('123')
      await store.validatePubMed('123')

      expect(api.validatePubMed).toHaveBeenCalledTimes(1)
      expect(store.cache.get('pubmed:123')).toEqual(OK)
    })

    it('records errors and rethrows', async () => {
      const store = useExternalValidationStore()
      api.validatePubMed.mockRejectedValue(new Error('pm'))

      await expect(store.validatePubMed('123')).rejects.toThrow('pm')
      expect(store.error).toBe('pm')
      expect(logService.error).toHaveBeenCalledWith(
        'PubMed validation failed',
        expect.objectContaining({ pmid: '123' })
      )
    })

    it('uses a fallback message and honours skipCache', async () => {
      const store = useExternalValidationStore()
      store.cache.set('pubmed:1', OK)
      api.validatePubMed.mockRejectedValue({})

      await expect(store.validatePubMed('1', true)).rejects.toEqual({})
      expect(api.validatePubMed).toHaveBeenCalledWith('1', true)
      expect(store.error).toBe('Validation failed')
    })
  })

  describe('validateHPO', () => {
    it('validates, caches and returns the result', async () => {
      const store = useExternalValidationStore()
      api.validateHPO.mockResolvedValue(OK)

      await expect(store.validateHPO('HP:0000001')).resolves.toEqual(OK)
      expect(store.cache.get('hpo:hp:0000001')).toEqual(OK)
    })

    it('serves the cache on a second call and skips it when asked', async () => {
      const store = useExternalValidationStore()
      api.validateHPO.mockResolvedValue(OK)

      await store.validateHPO('HP:1')
      await store.validateHPO('HP:1')
      expect(api.validateHPO).toHaveBeenCalledTimes(1)

      await store.validateHPO('HP:1', true)
      expect(api.validateHPO).toHaveBeenCalledTimes(2)
    })

    it('records errors and rethrows', async () => {
      const store = useExternalValidationStore()
      api.validateHPO.mockRejectedValue(new Error('hpo'))

      await expect(store.validateHPO('HP:1')).rejects.toThrow('hpo')
      expect(store.error).toBe('hpo')
      expect(logService.error).toHaveBeenCalledWith(
        'HPO validation failed',
        expect.objectContaining({ hpoTerm: 'HP:1' })
      )
    })

    it('uses a fallback message when the error has none', async () => {
      const store = useExternalValidationStore()
      api.validateHPO.mockRejectedValue({})

      await expect(store.validateHPO('HP:1')).rejects.toEqual({})
      expect(store.error).toBe('Validation failed')
    })
  })

  describe('validateBatch', () => {
    it('caches every returned result under its validator key', async () => {
      const store = useExternalValidationStore()
      api.validateBatch.mockResolvedValue({
        BRCA1: OK,
        XYZ: BAD
      })

      const results = await store.validateBatch('hgnc', ['BRCA1', 'XYZ'])

      expect(api.validateBatch).toHaveBeenCalledWith('hgnc', ['BRCA1', 'XYZ'])
      expect(results).toEqual({ BRCA1: OK, XYZ: BAD })
      expect(store.cache.get('hgnc:brca1')).toEqual(OK)
      expect(store.cache.get('hgnc:xyz')).toEqual(BAD)
    })

    it('records errors and rethrows with a fallback message', async () => {
      const store = useExternalValidationStore()
      api.validateBatch.mockRejectedValue(new Error('batch down'))

      await expect(store.validateBatch('pubmed', ['1'])).rejects.toThrow('batch down')
      expect(store.error).toBe('batch down')

      api.validateBatch.mockRejectedValue({})
      await expect(store.validateBatch('pubmed', ['1'])).rejects.toEqual({})
      expect(store.error).toBe('Batch validation failed')
    })
  })

  describe('fetchCacheStatistics', () => {
    it('returns the statistics', async () => {
      const store = useExternalValidationStore()
      api.getCacheStatistics.mockResolvedValue({ entries: 3 })

      await expect(store.fetchCacheStatistics()).resolves.toEqual({ entries: 3 })
    })

    it('records errors and rethrows with a fallback message', async () => {
      const store = useExternalValidationStore()
      api.getCacheStatistics.mockRejectedValue(new Error('stats'))

      await expect(store.fetchCacheStatistics()).rejects.toThrow('stats')
      expect(store.error).toBe('stats')

      api.getCacheStatistics.mockRejectedValue({})
      await expect(store.fetchCacheStatistics()).rejects.toEqual({})
      expect(store.error).toBe('Failed to fetch cache statistics')
    })
  })

  describe('clearing', () => {
    it('clearCache empties cache, loading and error', () => {
      const store = useExternalValidationStore()
      store.cache.set('hgnc:x', OK)
      store.loading.set('hgnc:y', true)
      store.error = 'boom'

      store.clearCache()

      expect(store.cache.size).toBe(0)
      expect(store.loading.size).toBe(0)
      expect(store.error).toBeNull()
    })

    it('clearError resets only the error', () => {
      const store = useExternalValidationStore()
      store.cache.set('hgnc:x', OK)
      store.error = 'boom'

      store.clearError()

      expect(store.error).toBeNull()
      expect(store.cache.size).toBe(1)
    })
  })
})
