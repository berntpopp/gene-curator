import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGenesStore, type GeneRecord, type GeneDetail } from '@/stores/genes'
import { genesAPI } from '@/api'
import type { Schema } from '@/types/api'

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
    countSearchGenes: vi.fn(),
    getStatistics: vi.fn()
  }
}))

const api = vi.mocked(genesAPI)

const gene = (id: string, over: Partial<GeneRecord> = {}): GeneRecord => ({
  id,
  hgnc_id: `HGNC:${id}`,
  approved_symbol: `GENE${id}`,
  chromosome: '1',
  location: '1p',
  is_assigned: false,
  has_active_work: false,
  ...over
})

const detail = (id: string, over: Partial<GeneDetail> = {}): GeneDetail =>
  ({
    id,
    hgnc_id: `HGNC:${id}`,
    approved_symbol: `GENE${id}`,
    is_assigned_to_any_scope: false,
    total_scope_assignments: 0,
    ...over
  }) as GeneDetail

const listResponse = (
  genes: GeneRecord[],
  over: Partial<Schema<'GeneListResponse'>> = {}
): Schema<'GeneListResponse'> => ({
  genes,
  total: genes.length,
  skip: 0,
  limit: 20,
  has_next: false,
  has_prev: false,
  ...over
})

describe('useGenesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('finds genes and filters unassigned ones', () => {
      const store = useGenesStore()
      store.genes = [gene('g1', { is_assigned: true }), gene('g2'), gene('g3')]

      expect(store.getGeneById('g2')?.id).toBe('g2')
      expect(store.getGeneById('zzz')).toBeUndefined()
      expect(store.getUnassignedGenes.map(g => g.id)).toEqual(['g2', 'g3'])
    })

    it('returns stored assignments and progress, undefined when missing', () => {
      const store = useGenesStore()
      const assignments = { gene_id: 'g1' } as Schema<'GeneAssignmentStatus'>
      const progress = { has_active_work: true } as Schema<'GeneCurationProgress'>
      store.geneAssignments = { g1: assignments }
      store.geneCurationProgress = { g1: progress }

      expect(store.getGeneAssignments('g1')).toEqual(assignments)
      expect(store.getGeneAssignments('none')).toBeUndefined()
      expect(store.getGeneCurationProgress('g1')).toEqual(progress)
      expect(store.getGeneCurationProgress('none')).toBeUndefined()
    })
  })

  describe('fetchGenes', () => {
    it('sends sort params, derives page state and stores the list', async () => {
      const store = useGenesStore()
      api.getGenes.mockResolvedValue(listResponse([gene('g1')], { total: 45, skip: 20, limit: 20 }))

      const response = await store.fetchGenes({ sort_order: 'desc' })

      expect(api.getGenes).toHaveBeenCalledWith({
        sort_by: 'approved_symbol',
        sort_order: 'desc',
        skip: 0,
        limit: 20
      })
      expect(store.genes.map(g => g.id)).toEqual(['g1'])
      expect(store.pagination).toEqual({ page: 2, per_page: 20, total: 45, pages: 3 })
      expect(response.genes).toHaveLength(1)
    })

    it('translates a 1-based page into skip/limit and drops null filters', async () => {
      const store = useGenesStore()
      store.updateSearchParams({ scope_id: 's1' })
      api.getGenes.mockResolvedValue(listResponse([]))

      await store.fetchGenes({ page: 3, has_active_work: null })

      expect(api.getGenes).toHaveBeenCalledWith(
        expect.objectContaining({ scope_id: 's1', skip: 40, limit: 20 })
      )
      expect(api.getGenes.mock.calls[0]?.[0]).not.toHaveProperty('has_active_work')
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
    it('sets current gene and replaces or appends the list row', async () => {
      const store = useGenesStore()
      store.genes = [gene('g1', { approved_symbol: 'OLD', has_active_work: true })]

      api.getGeneById.mockResolvedValueOnce(detail('g1', { approved_symbol: 'NEW' }))
      await store.fetchGeneById('g1')
      expect(store.currentGene?.approved_symbol).toBe('NEW')
      expect(store.genes[0]).toMatchObject({ approved_symbol: 'NEW', has_active_work: true })

      api.getGeneById.mockResolvedValueOnce(detail('g2', { is_assigned_to_any_scope: true }))
      await store.fetchGeneById('g2')
      expect(store.genes.map(g => g.id)).toEqual(['g1', 'g2'])
      expect(store.genes[1]?.is_assigned).toBe(true)
    })

    it('records the error and rethrows', async () => {
      const store = useGenesStore()
      api.getGeneById.mockRejectedValue(new Error('404'))

      await expect(store.fetchGeneById('x')).rejects.toThrow('404')
      expect(store.error).toBe('404')
    })
  })

  describe('createGene / updateGene / deleteGene', () => {
    const payload = { hgnc_id: 'HGNC:1', approved_symbol: 'A' }

    it('createGene appends the created gene as a list row', async () => {
      const store = useGenesStore()
      const created = { ...detail('new'), location: '2q' } as Schema<'Gene'>
      api.createGene.mockResolvedValue(created)

      await expect(store.createGene(payload)).resolves.toEqual(created)
      expect(store.genes.map(g => g.id)).toEqual(['new'])
      expect(store.genes[0]).toMatchObject({ location: '2q', chromosome: null, is_assigned: false })
    })

    it('createGene records errors and rethrows', async () => {
      const store = useGenesStore()
      api.createGene.mockRejectedValue(new Error('dup'))

      await expect(store.createGene(payload)).rejects.toThrow('dup')
      expect(store.error).toBe('dup')
    })

    it('updateGene replaces the list row and merges into the current gene', async () => {
      const store = useGenesStore()
      store.genes = [gene('g1')]
      store.currentGene = detail('g1', { total_scope_assignments: 2 })
      api.updateGene.mockResolvedValue({
        id: 'g1',
        hgnc_id: 'HGNC:g1',
        approved_symbol: 'UPD'
      } as Schema<'Gene'>)

      await store.updateGene('g1', {})

      expect(store.genes[0]?.approved_symbol).toBe('UPD')
      expect(store.currentGene?.approved_symbol).toBe('UPD')
      expect(store.currentGene?.total_scope_assignments).toBe(2)
    })

    it('updateGene leaves unrelated state alone', async () => {
      const store = useGenesStore()
      store.currentGene = detail('other')
      api.updateGene.mockResolvedValue(detail('g1') as Schema<'Gene'>)

      await store.updateGene('g1', {})

      expect(store.currentGene?.id).toBe('other')
      expect(store.genes).toEqual([])
    })

    it('updateGene records errors and rethrows', async () => {
      const store = useGenesStore()
      api.updateGene.mockRejectedValue(new Error('locked'))

      await expect(store.updateGene('g1', {})).rejects.toThrow('locked')
      expect(store.error).toBe('locked')
    })

    it('deleteGene removes the gene and clears current when it matches', async () => {
      const store = useGenesStore()
      store.genes = [gene('g1'), gene('g2')]
      store.currentGene = detail('g1')
      api.deleteGene.mockResolvedValue({})

      await expect(store.deleteGene('g1')).resolves.toBe(true)

      expect(store.genes.map(g => g.id)).toEqual(['g2'])
      expect(store.currentGene).toBeNull()
    })

    it('deleteGene keeps an unrelated current gene and records errors', async () => {
      const store = useGenesStore()
      store.currentGene = detail('keep')
      api.deleteGene.mockResolvedValueOnce({})
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
      const assignments = { gene_id: 'g1' } as Schema<'GeneAssignmentStatus'>
      const progress = { has_active_work: false } as Schema<'GeneCurationProgress'>
      api.getGeneAssignments.mockResolvedValue(assignments)
      api.getGeneCurationProgress.mockResolvedValue(progress)

      await expect(store.fetchGeneAssignments('g1')).resolves.toEqual(assignments)
      await expect(store.fetchGeneCurationProgress('g1')).resolves.toEqual(progress)

      expect(store.geneAssignments.g1).toEqual(assignments)
      expect(store.geneCurationProgress.g1).toEqual(progress)
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
    it('queries the search endpoint and stores the summaries', async () => {
      const store = useGenesStore()
      api.searchGenes.mockResolvedValueOnce([gene('s1')])
      api.countSearchGenes.mockResolvedValueOnce(41)

      await store.searchGenes({ query: 'x', page: 2 })

      expect(store.searchTotal).toBe(41)
      expect(api.countSearchGenes).toHaveBeenCalledWith({ query: 'x' })
      expect(api.searchGenes).toHaveBeenCalledWith({ query: 'x', skip: 20, limit: 20 })
      expect(store.searchResults.map(g => g.id)).toEqual(['s1'])
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
      const stats = { total_genes: 3 } as Schema<'GeneStatistics'>
      api.getStatistics.mockResolvedValueOnce(stats)
      await expect(store.fetchStatistics()).resolves.toEqual(stats)

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

      store.setCurrentGene(detail('g1'))
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
