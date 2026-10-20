import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGeneSummaryStore } from '@/stores/geneSummary'
import { geneSummaryAPI } from '@/api/geneSummary'

vi.mock('@/api/geneSummary', () => ({
  geneSummaryAPI: {
    getPublicSummary: vi.fn(),
    getFullSummary: vi.fn(),
    recomputeSummary: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(geneSummaryAPI)

describe('useGeneSummaryStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('getters return cached summaries or null', () => {
    const store = useGeneSummaryStore()
    store.publicSummaries.set('g1', { gene_id: 'g1' } as never)
    store.fullSummaries.set('g1', { gene_id: 'g1', is_stale: false } as never)

    expect(store.getPublicSummary('g1')).toEqual({ gene_id: 'g1' })
    expect(store.getPublicSummary('g2')).toBeNull()
    expect(store.getFullSummary('g1')).toEqual({ gene_id: 'g1', is_stale: false })
    expect(store.getFullSummary('g2')).toBeNull()
  })

  describe('fetchPublicSummary', () => {
    it('caches a found summary', async () => {
      const store = useGeneSummaryStore()
      api.getPublicSummary.mockResolvedValue({ gene_id: 'g1' })

      await expect(store.fetchPublicSummary('g1')).resolves.toEqual({ gene_id: 'g1' })
      expect(store.getPublicSummary('g1')).toEqual({ gene_id: 'g1' })
      expect(store.loading).toBe(false)
    })

    it('returns null without caching when no public curations exist', async () => {
      const store = useGeneSummaryStore()
      api.getPublicSummary.mockResolvedValue(null as never)

      await expect(store.fetchPublicSummary('g1')).resolves.toBeNull()
      expect(store.publicSummaries.size).toBe(0)
    })

    it('records the error and rethrows', async () => {
      const store = useGeneSummaryStore()
      api.getPublicSummary.mockRejectedValue(new Error('down'))

      await expect(store.fetchPublicSummary('g1')).rejects.toThrow('down')
      expect(store.error).toBe('down')
      expect(store.loading).toBe(false)
    })

    it('uses a fallback message when the error has none', async () => {
      const store = useGeneSummaryStore()
      api.getPublicSummary.mockRejectedValue({})

      await expect(store.fetchPublicSummary('g1')).rejects.toEqual({})
      expect(store.error).toBe('Failed to fetch gene summary')
    })
  })

  describe('fetchFullSummary', () => {
    it('caches the full summary', async () => {
      const store = useGeneSummaryStore()
      api.getFullSummary.mockResolvedValue({ gene_id: 'g1', total_scopes_curated: 2 })

      await expect(store.fetchFullSummary('g1')).resolves.toEqual({
        gene_id: 'g1',
        total_scopes_curated: 2
      })
      expect(store.getFullSummary('g1')).toMatchObject({ total_scopes_curated: 2 })
    })

    it('records the error and rethrows', async () => {
      const store = useGeneSummaryStore()
      api.getFullSummary.mockRejectedValue(new Error('403'))

      await expect(store.fetchFullSummary('g1')).rejects.toThrow('403')
      expect(store.error).toBe('403')
    })

    it('uses a fallback message when the error has none', async () => {
      const store = useGeneSummaryStore()
      api.getFullSummary.mockRejectedValue({})

      await expect(store.fetchFullSummary('g1')).rejects.toEqual({})
      expect(store.error).toBe('Failed to fetch full summary')
    })
  })

  describe('recomputeSummary', () => {
    it('invalidates both cached summaries for the gene', async () => {
      const store = useGeneSummaryStore()
      store.publicSummaries.set('g1', { gene_id: 'g1' } as never)
      store.fullSummaries.set('g1', { gene_id: 'g1' } as never)
      api.recomputeSummary.mockResolvedValue({} as never)

      await store.recomputeSummary('g1')

      expect(api.recomputeSummary).toHaveBeenCalledWith('g1')
      expect(store.getPublicSummary('g1')).toBeNull()
      expect(store.getFullSummary('g1')).toBeNull()
    })

    it('records the error and rethrows', async () => {
      const store = useGeneSummaryStore()
      api.recomputeSummary.mockRejectedValue(new Error('admin only'))

      await expect(store.recomputeSummary('g1')).rejects.toThrow('admin only')
      expect(store.error).toBe('admin only')
    })

    it('uses a fallback message when the error has none', async () => {
      const store = useGeneSummaryStore()
      api.recomputeSummary.mockRejectedValue({})

      await expect(store.recomputeSummary('g1')).rejects.toEqual({})
      expect(store.error).toBe('Failed to recompute summary')
    })
  })

  describe('clearing', () => {
    it('clearSummaries empties caches and error; clearError resets only the error', () => {
      const store = useGeneSummaryStore()
      store.publicSummaries.set('g1', { gene_id: 'g1' } as never)
      store.fullSummaries.set('g1', { gene_id: 'g1' } as never)
      store.error = 'x'

      store.clearError()
      expect(store.error).toBeNull()

      store.clearSummaries()
      expect(store.publicSummaries.size).toBe(0)
      expect(store.fullSummaries.size).toBe(0)
    })
  })
})
