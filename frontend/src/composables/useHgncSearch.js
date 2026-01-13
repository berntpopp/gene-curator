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
import { externalValidationAPI } from '@/api'
import { logService } from '@/services/logService'

// Simple debounce implementation
function debounce(fn, delay) {
  let timeoutId
  return function (...args) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

/**
 * HGNC gene search composable
 * @param {Object} options - Configuration options
 * @param {number} options.debounceMs - Debounce delay in milliseconds (default: 300)
 * @param {number} options.minQueryLength - Minimum query length to trigger search (default: 2)
 * @param {number} options.limit - Maximum results to return (default: 10)
 * @returns {Object} Search state and methods
 */
export function useHgncSearch(options = {}) {
  const { debounceMs = 300, minQueryLength = 2, limit = 10 } = options

  // Reactive state
  const query = ref('')
  const results = ref([])
  const isSearching = ref(false)
  const error = ref(null)
  const totalResults = ref(0)

  /**
   * Debounced search function
   */
  const searchDebounced = debounce(async searchQuery => {
    if (!searchQuery || searchQuery.length < minQueryLength) {
      results.value = []
      totalResults.value = 0
      return
    }

    isSearching.value = true
    error.value = null

    try {
      const response = await externalValidationAPI.searchHGNC(searchQuery, limit)

      results.value = response.results || []
      totalResults.value = response.total_results || 0

      logService.debug('HGNC search completed', {
        query: searchQuery,
        resultsCount: results.value.length
      })
    } catch (e) {
      error.value = e.message || 'Search failed'
      results.value = []
      totalResults.value = 0
      logService.error('HGNC search error', { query: searchQuery, error: e.message })
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
   * @param {string} searchQuery - Optional query (uses current query if not provided)
   * @returns {Promise<Array>} Search results
   */
  async function search(searchQuery) {
    const queryToSearch = searchQuery || query.value

    if (!queryToSearch || queryToSearch.length < minQueryLength) {
      results.value = []
      totalResults.value = 0
      return []
    }

    isSearching.value = true
    error.value = null

    try {
      const response = await externalValidationAPI.searchHGNC(queryToSearch, limit)

      results.value = response.results || []
      totalResults.value = response.total_results || 0

      logService.info('HGNC manual search completed', {
        query: queryToSearch,
        resultsCount: results.value.length
      })

      return results.value
    } catch (e) {
      error.value = e.message || 'Search failed'
      results.value = []
      totalResults.value = 0
      logService.error('HGNC manual search error', { query: queryToSearch, error: e.message })
      return []
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Fetch a single gene by HGNC ID
   * @param {string} hgncId - HGNC ID (e.g., "HGNC:1100" or "1100")
   * @returns {Promise<Object|null>} Gene data or null if not found
   */
  async function fetchGene(hgncId) {
    if (!hgncId) return null

    isSearching.value = true
    error.value = null

    try {
      const response = await externalValidationAPI.fetchHGNCGene(hgncId)

      if (response.results && response.results.length > 0) {
        logService.debug('HGNC gene fetched', {
          hgncId,
          symbol: response.results[0].symbol
        })
        return response.results[0]
      }

      return null
    } catch (e) {
      error.value = e.message || 'Failed to fetch gene'
      logService.error('HGNC fetch error', { hgncId, error: e.message })
      return null
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Validate and fetch multiple genes by symbol or HGNC ID
   * @param {Array<string>} identifiers - Array of gene symbols or HGNC IDs
   * @returns {Promise<Object>} Object with valid, invalid, and results arrays
   */
  async function validateBulk(identifiers) {
    if (!identifiers || identifiers.length === 0) {
      return { valid: [], invalid: [], results: [] }
    }

    isSearching.value = true
    error.value = null

    const valid = []
    const invalid = []
    const validationResults = []

    try {
      for (const identifier of identifiers) {
        const trimmed = identifier.trim()
        if (!trimmed) continue

        // Search for the gene - fetch multiple results to find exact match
        const response = await externalValidationAPI.searchHGNC(trimmed, 10)
        const allResults = response.results || []

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

            const bestMatch = sortedResults[0]
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
      error.value = e.message || 'Bulk validation failed'
      logService.error('HGNC bulk validation error', { error: e.message })
      return { valid: [], invalid: identifiers, results: [] }
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Reset search state
   */
  function reset() {
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
