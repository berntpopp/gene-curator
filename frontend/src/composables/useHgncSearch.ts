/**
 * Composable for HGNC gene search with debouncing
 *
 * Provides reactive gene search for autocomplete functionality
 *
 * @example
 * import { useHgncSearch } from '@/composables/useHgncSearch'
 *
 * const { query, results, isSearching, error, search, fetchGene, reset } = useHgncSearch()
 * query.value = 'BRCA' // Auto-searches after 300ms debounce
 */

import { ref, watch } from 'vue'
import type { Ref } from 'vue'
import { externalValidationAPI } from '@/api'
import { logService } from '@/services/logService'
import type { Schema } from '@/types/api'

export type HgncGene = Schema<'HGNCGeneSearchResult'>
type HGNCSearchResponse = Schema<'HGNCSearchResponse'>

export interface HgncSearchOptions {
  debounceMs?: number
  minQueryLength?: number
  limit?: number
}

export type BulkValidationStatus = 'valid' | 'suggestion' | 'not_found'

export interface BulkValidationEntry {
  input: string
  gene: HgncGene | null
  status: BulkValidationStatus
  message?: string
  alternatives: HgncGene[]
}

export interface BulkValidationResult {
  valid: string[]
  invalid: string[]
  results: BulkValidationEntry[]
}

export interface UseHgncSearchReturn {
  query: Ref<string>
  results: Ref<HgncGene[]>
  isSearching: Ref<boolean>
  error: Ref<string | null>
  totalResults: Ref<number>
  search: (searchQuery?: string) => Promise<HgncGene[]>
  fetchGene: (hgncId: string) => Promise<HgncGene | null>
  validateBulk: (identifiers: string[]) => Promise<BulkValidationResult>
  reset: () => void
}

/** Typed wrapper: the JS API client's return type is not precise enough to infer. */
const searchHgnc = (query: string, limit: number): Promise<HGNCSearchResponse> =>
  externalValidationAPI.searchHGNC(query, limit) as Promise<HGNCSearchResponse>

const fetchHgncGene = (hgncId: string): Promise<HGNCSearchResponse> =>
  externalValidationAPI.fetchHGNCGene(hgncId) as Promise<HGNCSearchResponse>

// Simple debounce implementation
function debounce<T extends unknown[]>(
  fn: (...args: T) => void,
  delay: number
): (...args: T) => void {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  return function (...args: T) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

function errorMessageOf(e: unknown): string | undefined {
  return e instanceof Error ? e.message : undefined
}

/**
 * HGNC gene search composable
 */
export function useHgncSearch(options: HgncSearchOptions = {}): UseHgncSearchReturn {
  const { debounceMs = 300, minQueryLength = 2, limit = 10 } = options

  // Reactive state
  const query = ref('')
  const results = ref<HgncGene[]>([])
  const isSearching = ref(false)
  const error = ref<string | null>(null)
  const totalResults = ref(0)

  /**
   * Debounced search function
   */
  const searchDebounced = debounce(async (searchQuery: string) => {
    if (!searchQuery || searchQuery.length < minQueryLength) {
      results.value = []
      totalResults.value = 0
      return
    }

    isSearching.value = true
    error.value = null

    try {
      const response = await searchHgnc(searchQuery, limit)

      results.value = response.results || []
      totalResults.value = response.total_results || 0

      logService.debug('HGNC search completed', {
        query: searchQuery,
        resultsCount: results.value.length
      })
    } catch (e) {
      error.value = errorMessageOf(e) || 'Search failed'
      results.value = []
      totalResults.value = 0
      logService.error('HGNC search error', { query: searchQuery, error: errorMessageOf(e) })
    } finally {
      isSearching.value = false
    }
  }, debounceMs)

  // Watch query changes for automatic search
  watch(query, newQuery => {
    searchDebounced(newQuery)
  })

  /**
   * Manually trigger search without debouncing
   * @param searchQuery - Optional query (uses current query if not provided)
   * @returns Search results
   */
  async function search(searchQuery?: string): Promise<HgncGene[]> {
    const queryToSearch = searchQuery || query.value

    if (!queryToSearch || queryToSearch.length < minQueryLength) {
      results.value = []
      totalResults.value = 0
      return []
    }

    isSearching.value = true
    error.value = null

    try {
      const response = await searchHgnc(queryToSearch, limit)

      results.value = response.results || []
      totalResults.value = response.total_results || 0

      logService.info('HGNC manual search completed', {
        query: queryToSearch,
        resultsCount: results.value.length
      })

      return results.value
    } catch (e) {
      error.value = errorMessageOf(e) || 'Search failed'
      results.value = []
      totalResults.value = 0
      logService.error('HGNC manual search error', {
        query: queryToSearch,
        error: errorMessageOf(e)
      })
      return []
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Fetch a single gene by HGNC ID
   * @param hgncId - HGNC ID (e.g., "HGNC:1100" or "1100")
   * @returns Gene data or null if not found
   */
  async function fetchGene(hgncId: string): Promise<HgncGene | null> {
    if (!hgncId) return null

    isSearching.value = true
    error.value = null

    try {
      const response = await fetchHgncGene(hgncId)

      const first = response.results?.[0]
      if (first) {
        logService.debug('HGNC gene fetched', {
          hgncId,
          symbol: first.symbol
        })
        return first
      }

      return null
    } catch (e) {
      error.value = errorMessageOf(e) || 'Failed to fetch gene'
      logService.error('HGNC fetch error', { hgncId, error: errorMessageOf(e) })
      return null
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Validate and fetch multiple genes by symbol or HGNC ID
   * @param identifiers - Array of gene symbols or HGNC IDs
   * @returns Object with valid, invalid, and results arrays
   */
  async function validateBulk(identifiers: string[]): Promise<BulkValidationResult> {
    if (!identifiers || identifiers.length === 0) {
      return { valid: [], invalid: [], results: [] }
    }

    isSearching.value = true
    error.value = null

    const valid: string[] = []
    const invalid: string[] = []
    const validationResults: BulkValidationEntry[] = []

    try {
      for (const identifier of identifiers) {
        const trimmed = identifier.trim()
        if (!trimmed) continue

        // Search for the gene - fetch multiple results to find exact match
        const response = await searchHgnc(trimmed, 10)
        const allResults: HgncGene[] = response.results || []

        if (allResults.length > 0) {
          // First, look for an exact symbol match (case-insensitive)
          const exactSymbolMatch = allResults.find(
            g => g.symbol.toUpperCase() === trimmed.toUpperCase()
          )

          // Then check for exact HGNC ID match
          const exactIdMatch = allResults.find(
            g =>
              g.hgnc_id.toUpperCase() === trimmed.toUpperCase() ||
              g.hgnc_id.replace('HGNC:', '') === trimmed
          )

          const exactMatch = exactSymbolMatch || exactIdMatch

          if (exactMatch) {
            // Found exact match
            valid.push(trimmed)
            validationResults.push({
              input: trimmed,
              gene: exactMatch,
              status: 'valid',
              alternatives: allResults.filter(g => g.hgnc_id !== exactMatch.hgnc_id).slice(0, 3)
            })
          } else {
            // No exact match - provide alternatives sorted by relevance
            // Prefer genes where symbol starts with input, then contains input
            const sortedResults = [...allResults].sort((a, b) => {
              const aStartsWith = a.symbol.toUpperCase().startsWith(trimmed.toUpperCase())
              const bStartsWith = b.symbol.toUpperCase().startsWith(trimmed.toUpperCase())
              if (aStartsWith && !bStartsWith) return -1
              if (!aStartsWith && bStartsWith) return 1
              // Prefer shorter symbols (more likely to be the main gene, not AS1 etc)
              return a.symbol.length - b.symbol.length
            })

            const bestMatch = sortedResults[0] as HgncGene // allResults.length > 0 here
            const alternatives = sortedResults.slice(1, 4)

            invalid.push(trimmed)
            validationResults.push({
              input: trimmed,
              gene: bestMatch,
              status: 'suggestion',
              message: `Did you mean ${bestMatch.symbol}?`,
              alternatives
            })
          }
        } else {
          invalid.push(trimmed)
          validationResults.push({
            input: trimmed,
            gene: null,
            status: 'not_found',
            alternatives: []
          })
        }
      }

      logService.info('HGNC bulk validation completed', {
        total: identifiers.length,
        valid: valid.length,
        invalid: invalid.length
      })

      return { valid, invalid, results: validationResults }
    } catch (e) {
      error.value = errorMessageOf(e) || 'Bulk validation failed'
      logService.error('HGNC bulk validation error', { error: errorMessageOf(e) })
      return { valid: [], invalid: identifiers, results: [] }
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Reset search state
   */
  function reset(): void {
    query.value = ''
    results.value = []
    totalResults.value = 0
    error.value = null
    isSearching.value = false
  }

  return {
    // State
    query,
    results,
    isSearching,
    error,
    totalResults,
    // Methods
    search,
    fetchGene,
    validateBulk,
    reset
  }
}
