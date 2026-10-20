import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useHgncSearch, type HgncGene } from '../useHgncSearch'

const api = vi.hoisted(() => ({
  searchHGNC: vi.fn(),
  fetchHGNCGene: vi.fn()
}))

vi.mock('@/api', () => ({
  externalValidationAPI: api
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const gene = (symbol: string, hgnc_id: string): HgncGene => ({
  symbol,
  hgnc_id,
  name: `${symbol} name`,
  alias_symbols: [],
  previous_symbols: []
})

describe('useHgncSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('search()', () => {
    it('returns empty results without calling the API for short queries', async () => {
      const { search, results, totalResults } = useHgncSearch()

      expect(await search('B')).toEqual([])
      expect(api.searchHGNC).not.toHaveBeenCalled()
      expect(results.value).toEqual([])
      expect(totalResults.value).toBe(0)
    })

    it('stores results and total from the API response', async () => {
      const genes = [gene('BRCA1', 'HGNC:1100')]
      api.searchHGNC.mockResolvedValue({ results: genes, total_results: 7 })
      const { search, results, totalResults, isSearching } = useHgncSearch({ limit: 5 })

      const returned = await search('BRCA')

      expect(api.searchHGNC).toHaveBeenCalledWith('BRCA', 5)
      expect(returned).toEqual(genes)
      expect(results.value).toEqual(genes)
      expect(totalResults.value).toBe(7)
      expect(isSearching.value).toBe(false)
    })

    it('uses the current query when no argument is given', async () => {
      api.searchHGNC.mockResolvedValue({ results: [], total_results: 0 })
      const { query, search } = useHgncSearch()

      query.value = 'TP5'
      await search()

      expect(api.searchHGNC).toHaveBeenCalledWith('TP5', 10)
    })

    it('captures errors and clears results', async () => {
      api.searchHGNC.mockRejectedValue(new Error('offline'))
      const { search, error, results } = useHgncSearch()

      expect(await search('BRCA')).toEqual([])
      expect(error.value).toBe('offline')
      expect(results.value).toEqual([])
    })
  })

  describe('debounced query', () => {
    it('searches automatically after the debounce delay', async () => {
      api.searchHGNC.mockResolvedValue({ results: [gene('KRAS', 'HGNC:6407')], total_results: 1 })
      const { query, results } = useHgncSearch({ debounceMs: 300 })

      query.value = 'KRAS'
      await vi.advanceTimersByTimeAsync(299)
      expect(api.searchHGNC).not.toHaveBeenCalled()
      await vi.advanceTimersByTimeAsync(10)

      expect(api.searchHGNC).toHaveBeenCalledWith('KRAS', 10)
      expect(results.value).toHaveLength(1)
    })

    it('clears results for queries below the minimum length', async () => {
      const { query, results, totalResults } = useHgncSearch()
      results.value = [gene('X', 'HGNC:1')]
      totalResults.value = 3

      query.value = 'X'
      await vi.advanceTimersByTimeAsync(400)

      expect(api.searchHGNC).not.toHaveBeenCalled()
      expect(results.value).toEqual([])
      expect(totalResults.value).toBe(0)
    })

    it('records debounced search errors', async () => {
      api.searchHGNC.mockRejectedValue(new Error('boom'))
      const { query, error } = useHgncSearch()

      query.value = 'BRCA'
      await vi.advanceTimersByTimeAsync(400)

      expect(error.value).toBe('boom')
    })
  })

  describe('fetchGene()', () => {
    it('returns the first matching gene', async () => {
      const found = gene('BRCA1', 'HGNC:1100')
      api.fetchHGNCGene.mockResolvedValue({ results: [found], total_results: 1 })
      const { fetchGene } = useHgncSearch()

      expect(await fetchGene('HGNC:1100')).toEqual(found)
      expect(api.fetchHGNCGene).toHaveBeenCalledWith('HGNC:1100')
    })

    it('returns null for empty id, no results or errors', async () => {
      const { fetchGene, error } = useHgncSearch()

      expect(await fetchGene('')).toBeNull()
      expect(api.fetchHGNCGene).not.toHaveBeenCalled()

      api.fetchHGNCGene.mockResolvedValueOnce({ results: [], total_results: 0 })
      expect(await fetchGene('HGNC:0')).toBeNull()

      api.fetchHGNCGene.mockRejectedValueOnce(new Error('404'))
      expect(await fetchGene('HGNC:9')).toBeNull()
      expect(error.value).toBe('404')
    })
  })

  describe('validateBulk()', () => {
    it('returns empty result for no identifiers', async () => {
      const { validateBulk } = useHgncSearch()

      expect(await validateBulk([])).toEqual({ valid: [], invalid: [], results: [] })
      expect(api.searchHGNC).not.toHaveBeenCalled()
    })

    it('classifies exact symbol, exact id, suggestion and not-found inputs', async () => {
      const brca1 = gene('BRCA1', 'HGNC:1100')
      const brca2 = gene('BRCA2', 'HGNC:1101')
      const brca1as = gene('BRCA1-AS1', 'HGNC:50000')
      api.searchHGNC.mockImplementation(async (term: string) => {
        if (term === 'brca1') return { results: [brca1, brca1as], total_results: 2 }
        if (term === '1101') return { results: [brca2], total_results: 1 }
        if (term === 'BRCA') return { results: [brca2, brca1], total_results: 2 }
        return { results: [], total_results: 0 }
      })
      const { validateBulk } = useHgncSearch()

      const outcome = await validateBulk(['brca1', ' 1101 ', 'BRCA', 'NOPE', '   '])

      expect(outcome.valid).toEqual(['brca1', '1101'])
      expect(outcome.invalid).toEqual(['BRCA', 'NOPE'])
      expect(outcome.results).toHaveLength(4)

      const exact = outcome.results[0]
      expect(exact).toMatchObject({ input: 'brca1', status: 'valid', gene: brca1 })
      expect(exact?.alternatives).toEqual([brca1as])

      expect(outcome.results[1]).toMatchObject({ input: '1101', status: 'valid', gene: brca2 })

      const suggestion = outcome.results[2]
      expect(suggestion).toMatchObject({
        input: 'BRCA',
        status: 'suggestion',
        message: 'Did you mean BRCA2?',
        gene: brca2
      })
      expect(suggestion?.alternatives).toEqual([brca1])

      expect(outcome.results[3]).toEqual({
        input: 'NOPE',
        gene: null,
        status: 'not_found',
        alternatives: []
      })
    })

    it('returns invalid list and error message when the API fails', async () => {
      api.searchHGNC.mockRejectedValue(new Error('server down'))
      const { validateBulk, error, isSearching } = useHgncSearch()

      const outcome = await validateBulk(['BRCA1'])

      expect(outcome).toEqual({ valid: [], invalid: ['BRCA1'], results: [] })
      expect(error.value).toBe('server down')
      expect(isSearching.value).toBe(false)
    })
  })

  describe('reset()', () => {
    it('clears query, results and error', () => {
      const { query, results, totalResults, error, reset } = useHgncSearch()
      query.value = 'BRCA'
      results.value = [gene('BRCA1', 'HGNC:1100')]
      totalResults.value = 4
      error.value = 'x'

      reset()

      expect(query.value).toBe('')
      expect(results.value).toEqual([])
      expect(totalResults.value).toBe(0)
      expect(error.value).toBeNull()
    })
  })
})
