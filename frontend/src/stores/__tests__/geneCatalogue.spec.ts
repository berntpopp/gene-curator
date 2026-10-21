import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Schema } from '@/types/api'
import { setActivePinia, createPinia } from 'pinia'
import { useGeneCatalogueStore } from '@/stores/geneCatalogue'
import { geneCatalogueAPI } from '@/api/geneCatalogue'

vi.mock('@/api/geneCatalogue', () => ({
  geneCatalogueAPI: {
    getCatalogue: vi.fn(),
    getAvailableClassifications: vi.fn(),
    getAvailableDiseases: vi.fn(),
    getAvailableScopes: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(geneCatalogueAPI)

const entry = (geneId: string) =>
  ({ gene_id: geneId, approved_symbol: geneId }) as Schema<'GeneCatalogueEntry'>

describe('useGeneCatalogueStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('finds entries, tracks expansion and reports active filters', () => {
      const store = useGeneCatalogueStore()
      store.entries = [entry('g1')]
      store.expandedGeneIds = new Set(['g1'])

      expect(store.getEntryByGeneId('g1')).toEqual(entry('g1'))
      expect(store.getEntryByGeneId('zz')).toBeUndefined()
      expect(store.isGeneExpanded('g1')).toBe(true)
      expect(store.isGeneExpanded('g2')).toBe(false)
      expect(store.expandedGenes).toEqual(['g1'])
      expect(store.hasActiveFilters).toBe(false)

      store.filters.chromosome = '17'
      expect(store.hasActiveFilters).toBe(true)
    })

    it('computes total pages from total and page size', () => {
      const store = useGeneCatalogueStore()
      store.pagination.total = 45
      store.pagination.perPage = 20
      expect(store.totalPages).toBe(3)
    })
  })

  describe('fetchCatalogue', () => {
    it('sends skip/limit and filters and stores entries, pagination and summary', async () => {
      const store = useGeneCatalogueStore()
      store.filters.search = 'BRCA'
      store.filters.scopeId = 's1'
      store.pagination.page = 2
      api.getCatalogue.mockResolvedValue({
        entries: [entry('g1')],
        total: 25,
        skip: 20,
        limit: 20,
        has_next: true,
        has_prev: true,
        summary: {
          total_genes_curated: 5,
          total_curations: 9,
          total_scopes: 2,
          classification_summary: { definitive: 3 }
        }
      })

      const response = await store.fetchCatalogue()

      expect(api.getCatalogue).toHaveBeenCalledWith({
        skip: 20,
        limit: 20,
        search: 'BRCA',
        classification: undefined,
        disease: undefined,
        scope_id: 's1',
        chromosome: undefined,
        sort_by: 'approved_symbol',
        sort_order: 'asc'
      })
      expect(response).toHaveProperty('total', 25)
      expect(store.entries).toHaveLength(1)
      expect(store.pagination).toMatchObject({ total: 25, hasNext: true, hasPrev: true })
      expect(store.summary).toEqual({
        totalGenesCurated: 5,
        totalCurations: 9,
        totalScopes: 2,
        classificationSummary: { definitive: 3 }
      })
      expect(store.loading).toBe(false)
    })

    it('uses the page from params and keeps the summary when none is returned', async () => {
      const store = useGeneCatalogueStore()
      store.summary.totalCurations = 7
      api.getCatalogue.mockResolvedValue({} as Schema<'GeneCatalogueResponse'>)

      await store.fetchCatalogue({ page: 3 })

      expect(api.getCatalogue).toHaveBeenCalledWith(expect.objectContaining({ skip: 40 }))
      expect(store.entries).toEqual([])
      expect(store.pagination).toMatchObject({ total: 0, hasNext: false, hasPrev: false })
      expect(store.summary.totalCurations).toBe(7)
    })

    it('defaults missing summary fields to zero', async () => {
      const store = useGeneCatalogueStore()
      api.getCatalogue.mockResolvedValue({ summary: {} } as Schema<'GeneCatalogueResponse'>)

      await store.fetchCatalogue()

      expect(store.summary).toEqual({
        totalGenesCurated: 0,
        totalCurations: 0,
        totalScopes: 0,
        classificationSummary: {}
      })
    })

    it('records the error and rethrows with a fallback message', async () => {
      const store = useGeneCatalogueStore()
      api.getCatalogue.mockRejectedValue(new Error('down'))

      await expect(store.fetchCatalogue()).rejects.toThrow('down')
      expect(store.error).toEqual({ message: 'down' })
      expect(store.loading).toBe(false)

      api.getCatalogue.mockRejectedValue({})
      await expect(store.fetchCatalogue()).rejects.toEqual({})
      expect(store.error).toEqual({ message: 'Failed to fetch catalogue' })
    })
  })

  describe('loadFilterOptions', () => {
    it('loads options once and caches them', async () => {
      const store = useGeneCatalogueStore()
      api.getAvailableClassifications.mockResolvedValue(['definitive'])
      api.getAvailableDiseases.mockResolvedValue(['d1'])
      api.getAvailableScopes.mockResolvedValue(null as never)

      const options = await store.loadFilterOptions()

      expect(options).toEqual({
        classifications: ['definitive'],
        diseases: ['d1'],
        scopes: [],
        loaded: true
      })

      await store.loadFilterOptions()
      expect(api.getAvailableClassifications).toHaveBeenCalledTimes(1)
    })

    it('a failed option call leaves that list empty and sets no page error', async () => {
      const store = useGeneCatalogueStore()
      api.getAvailableClassifications.mockResolvedValue(['definitive'])
      api.getAvailableDiseases.mockResolvedValue(['d1'])
      api.getAvailableScopes.mockRejectedValue(new Error('scopes'))

      const options = await store.loadFilterOptions()

      expect(options).toEqual({
        classifications: ['definitive'],
        diseases: ['d1'],
        scopes: [],
        loaded: true
      })
      expect(store.error).toBeNull()
    })
  })

  describe('filters and pagination', () => {
    it('updateFilters merges and resets the page; clearFilters restores defaults', () => {
      const store = useGeneCatalogueStore()
      store.pagination.page = 5
      store.updateFilters({ classification: 'strong' })
      expect(store.filters.classification).toBe('strong')
      expect(store.filters.sortBy).toBe('approved_symbol')
      expect(store.pagination.page).toBe(1)

      store.clearFilters()
      expect(store.filters.classification).toBeNull()
      expect(store.pagination.page).toBe(1)
    })

    it('setPage sets the page', () => {
      const store = useGeneCatalogueStore()
      store.setPage(4)
      expect(store.pagination.page).toBe(4)
    })
  })

  describe('row expansion', () => {
    it('toggles, expands, collapses and collapses all rows', () => {
      const store = useGeneCatalogueStore()

      store.toggleGeneExpanded('g1')
      expect(store.isGeneExpanded('g1')).toBe(true)
      store.toggleGeneExpanded('g1')
      expect(store.isGeneExpanded('g1')).toBe(false)

      store.expandGene('g2')
      store.expandGene('g3')
      expect(store.expandedGenes.sort()).toEqual(['g2', 'g3'])

      store.collapseGene('g2')
      expect(store.expandedGenes).toEqual(['g3'])

      store.collapseAll()
      expect(store.expandedGenes).toEqual([])
    })
  })

  describe('clearError and $reset', () => {
    it('clearError resets the error', () => {
      const store = useGeneCatalogueStore()
      store.error = { message: 'x' }
      store.clearError()
      expect(store.error).toBeNull()
    })

    it('$reset restores every slice to its initial value', () => {
      const store = useGeneCatalogueStore()
      store.entries = [entry('g1')]
      store.loading = true
      store.error = { message: 'x' }
      store.pagination.total = 9
      store.filters.search = 'q'
      store.summary.totalScopes = 4
      store.filterOptions.loaded = true
      store.expandedGeneIds = new Set(['g1'])

      store.$reset()

      expect(store.entries).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.pagination).toEqual({
        page: 1,
        perPage: 20,
        total: 0,
        hasNext: false,
        hasPrev: false
      })
      expect(store.filters.search).toBeNull()
      expect(store.summary.totalScopes).toBe(0)
      expect(store.filterOptions.loaded).toBe(false)
      expect(store.expandedGenes).toEqual([])
    })
  })
})
