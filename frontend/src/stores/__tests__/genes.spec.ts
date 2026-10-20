import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { GeneRecord } from '@/stores/genes'
import { setActivePinia, createPinia } from 'pinia'
import { useGenesStore } from '@/stores/genes'
import { genesAPI } from '@/api'

vi.mock('@/api', () => ({
  genesAPI: {
    getGenes: vi.fn(),
    getGeneById: vi.fn(),
    createGene: vi.fn(),
    updateGene: vi.fn(),
    deleteGene: vi.fn(),
    getGeneAssignments: vi.fn(),
    getGeneCurationProgress: vi.fn(),
    searchGenes: vi.fn(),
    getStatistics: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(genesAPI)

const gene = (id: string, extra: Record<string, unknown> = {}) =>
  ({
    id,
    approved_symbol: `GENE${id}`,
    ...extra
  }) as GeneRecord

describe('useGenesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('finds genes and filters by scope or assignment state', () => {
      const store = useGenesStore()
      store.genes = [
        gene('g1', { assignments: [{ scope_id: 's1' }] }),
        gene('g2', { assignments: [] }),
        gene('g3')
      ]

      expect(store.getGeneById('g2')?.id).toBe('g2')
      expect(store.getGeneById('zzz')).toBeUndefined()
      expect(store.getGenesByScope('s1').map(g => g.id)).toEqual(['g1'])
      expect(store.getUnassignedGenes.map(g => g.id)).toEqual(['g2', 'g3'])
    })

    it('returns stored assignments and progress with defaults', () => {
      const store = useGenesStore()
      store.geneAssignments = { g1: [{ id: 'a' } as never] }
      store.geneCurationProgress = { g1: { has_active_work: true } as never }

      expect(store.getGeneAssignments('g1')).toEqual([{ id: 'a' }])
      expect(store.getGeneAssignments('none')).toEqual([])
      expect(store.getGeneCurationProgress('g1')).toEqual({ has_active_work: true })
      expect(store.getGeneCurationProgress('none')).toEqual({})
    })
  })

  describe('fetchGenes', () => {
    it('merges search params and stores the list and pagination', async () => {
      const store = useGenesStore()
      store.updateSearchParams({ query: 'BRCA' })
      api.getGenes.mockResolvedValue({
        genes: [gene('g1')],
        pagination: { page: 1, per_page: 20, total: 1, pages: 1 }
      })

      const response = await store.fetchGenes({ sort_order: 'desc' })

      expect(api.getGenes).toHaveBeenCalledWith(
        expect.objectContaining({ query: 'BRCA', sort_by: 'approved_symbol', sort_order: 'desc' })
      )
      expect(store.genes).toHaveLength(1)
      expect(store.pagination.total).toBe(1)
      expect(response).toHaveProperty('genes')
    })

    it('falls back to data or the raw array', async () => {
      const store = useGenesStore()
      api.getGenes.mockResolvedValueOnce({ data: [gene('d')] })
      await store.fetchGenes()
      expect(store.genes.map(g => g.id)).toEqual(['d'])

      api.getGenes.mockResolvedValueOnce([gene('raw')])
      await store.fetchGenes()
      expect(store.genes.map(g => g.id)).toEqual(['raw'])
    })

    it('records the error and rethrows', async () => {
      const store = useGenesStore()
      api.getGenes.mockRejectedValue(new Error('down'))

      await expect(store.fetchGenes()).rejects.toThrow('down')
      expect(store.error).toBe('down')
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchGeneById', () => {
    it('sets current gene and replaces or appends the list entry', async () => {
      const store = useGenesStore()
      store.genes = [gene('g1', { approved_symbol: 'OLD' })]

      api.getGeneById.mockResolvedValueOnce(gene('g1', { approved_symbol: 'NEW' }))
      await store.fetchGeneById('g1')
      expect(store.currentGene?.approved_symbol).toBe('NEW')
      expect(store.genes[0]?.approved_symbol).toBe('NEW')

      api.getGeneById.mockResolvedValueOnce(gene('g2'))
      await store.fetchGeneById('g2')
      expect(store.genes.map(g => g.id)).toEqual(['g1', 'g2'])
    })

    it('records the error and rethrows', async () => {
      const store = useGenesStore()
      api.getGeneById.mockRejectedValue(new Error('404'))

      await expect(store.fetchGeneById('x')).rejects.toThrow('404')
      expect(store.error).toBe('404')
    })
  })

  describe('createGene / updateGene / deleteGene', () => {
    it('createGene appends the created gene', async () => {
      const store = useGenesStore()
      api.createGene.mockResolvedValue(gene('new'))

      await expect(store.createGene({} as never)).resolves.toEqual(gene('new'))
      expect(store.genes.map(g => g.id)).toEqual(['new'])
    })

    it('createGene records errors and rethrows', async () => {
      const store = useGenesStore()
      api.createGene.mockRejectedValue(new Error('dup'))

      await expect(store.createGene({} as never)).rejects.toThrow('dup')
      expect(store.error).toBe('dup')
    })

    it('updateGene replaces the list entry and the current gene', async () => {
      const store = useGenesStore()
      store.genes = [gene('g1')]
      store.currentGene = gene('g1')
      api.updateGene.mockResolvedValue(gene('g1', { approved_symbol: 'UPD' }))

      await store.updateGene('g1', {} as never)

      expect(store.genes[0]?.approved_symbol).toBe('UPD')
      expect(store.currentGene?.approved_symbol).toBe('UPD')
    })

    it('updateGene leaves unrelated state alone', async () => {
      const store = useGenesStore()
      store.currentGene = gene('other')
      api.updateGene.mockResolvedValue(gene('g1'))

      await store.updateGene('g1', {} as never)

      expect(store.currentGene?.id).toBe('other')
      expect(store.genes).toEqual([])
    })

    it('updateGene records errors and rethrows', async () => {
      const store = useGenesStore()
      api.updateGene.mockRejectedValue(new Error('locked'))

      await expect(store.updateGene('g1', {} as never)).rejects.toThrow('locked')
      expect(store.error).toBe('locked')
    })

    it('deleteGene removes the gene and clears current when it matches', async () => {
      const store = useGenesStore()
      store.genes = [gene('g1'), gene('g2')]
      store.currentGene = gene('g1')
      api.deleteGene.mockResolvedValue({} as never)

      await expect(store.deleteGene('g1')).resolves.toBe(true)

      expect(store.genes.map(g => g.id)).toEqual(['g2'])
      expect(store.currentGene).toBeNull()
    })

    it('deleteGene keeps an unrelated current gene and records errors', async () => {
      const store = useGenesStore()
      store.currentGene = gene('keep')
      api.deleteGene.mockResolvedValueOnce({} as never)
      await store.deleteGene('g1')
      expect(store.currentGene?.id).toBe('keep')

      api.deleteGene.mockRejectedValueOnce(new Error('nope'))
      await expect(store.deleteGene('g1')).rejects.toThrow('nope')
      expect(store.error).toBe('nope')
    })
  })

  describe('assignments and progress', () => {
    it('fetchGeneAssignments and fetchGeneCurationProgress store results by gene', async () => {
      const store = useGenesStore()
      api.getGeneAssignments.mockResolvedValue([{ id: 'a1' }])
      api.getGeneCurationProgress.mockResolvedValue({ has_active_work: false })

      await expect(store.fetchGeneAssignments('g1')).resolves.toEqual([{ id: 'a1' }])
      await expect(store.fetchGeneCurationProgress('g1')).resolves.toEqual({
        has_active_work: false
      })

      expect(store.geneAssignments.g1).toEqual([{ id: 'a1' }])
      expect(store.geneCurationProgress.g1).toEqual({ has_active_work: false })
    })

    it('records errors from both fetches and rethrows', async () => {
      const store = useGenesStore()
      api.getGeneAssignments.mockRejectedValue(new Error('a'))
      api.getGeneCurationProgress.mockRejectedValue(new Error('p'))

      await expect(store.fetchGeneAssignments('g1')).rejects.toThrow('a')
      expect(store.error).toBe('a')
      await expect(store.fetchGeneCurationProgress('g1')).rejects.toThrow('p')
      expect(store.error).toBe('p')
    })
  })

  describe('searchGenes', () => {
    it('stores results from either response shape', async () => {
      const store = useGenesStore()
      api.searchGenes.mockResolvedValueOnce({ genes: [gene('s1')] })
      await store.searchGenes({ query: 'x' })
      expect(store.searchResults.map(g => g.id)).toEqual(['s1'])

      api.searchGenes.mockResolvedValueOnce({ data: [gene('s2')] })
      await store.searchGenes({ query: 'y' })
      expect(store.searchResults.map(g => g.id)).toEqual(['s2'])
    })

    it('records errors and rethrows', async () => {
      const store = useGenesStore()
      api.searchGenes.mockRejectedValue(new Error('timeout'))

      await expect(store.searchGenes({})).rejects.toThrow('timeout')
      expect(store.error).toBe('timeout')
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchStatistics', () => {
    it('returns statistics and records errors', async () => {
      const store = useGenesStore()
      api.getStatistics.mockResolvedValueOnce({ total_genes: 3 })
      await expect(store.fetchStatistics()).resolves.toEqual({ total_genes: 3 })

      api.getStatistics.mockRejectedValueOnce(new Error('stats'))
      await expect(store.fetchStatistics()).rejects.toThrow('stats')
      expect(store.error).toBe('stats')
    })
  })

  describe('local state actions', () => {
    it('updateSearchParams merges, set/clear current gene and clear results', () => {
      const store = useGenesStore()
      store.updateSearchParams({ scope_id: 's1', sort_order: 'desc' })
      expect(store.searchParams).toMatchObject({ scope_id: 's1', sort_order: 'desc', query: '' })

      store.setCurrentGene(gene('g1'))
      expect(store.currentGene?.id).toBe('g1')
      store.clearCurrentGene()
      expect(store.currentGene).toBeNull()

      store.searchResults = [gene('x')]
      store.clearSearchResults()
      expect(store.searchResults).toEqual([])
    })

    it('clearError and $reset', () => {
      const store = useGenesStore()
      store.error = 'x'
      store.clearError()
      expect(store.error).toBeNull()

      store.genes = [gene('g1')]
      store.updateSearchParams({ query: 'q' })
      store.$reset()
      expect(store.genes).toEqual([])
      expect(store.searchParams.query).toBe('')
    })
  })
})
