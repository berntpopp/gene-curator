import { defineStore } from 'pinia'
import { externalValidationAPI } from '@/api/externalValidation.js'
import { logService } from '@/services/logService'

/**
 * External Validation store for HGNC, PubMed, HPO validation with caching
 */
export const useExternalValidationStore = defineStore('externalValidation', {
  state: () => ({
    cache: new Map(),
    loading: new Map(),
    error: null
  }),

  getters: {
    /**
     * Check if a value is currently being validated
     */
    isValidating: state => (validator, value) => {
      const cacheKey = `${validator}:${value.toLowerCase().trim()}`
      return state.loading.get(cacheKey) || false
    },

    /**
     * Get cached validation result
     */
    getCachedResult: state => (validator, value) => {
      const cacheKey = `${validator}:${value.toLowerCase().trim()}`
      return state.cache.get(cacheKey) || null
    }
  },

  actions: {
    /**
     * Get cache key for validator and value
     */
    _getCacheKey(validator, value) {
      return `${validator}:${value.toLowerCase().trim()}`
    },

    /**
     * Validate HGNC gene symbol
     */
    async validateHGNC(geneSymbol, skipCache = false) {
      const cacheKey = this._getCacheKey('hgnc', geneSymbol)

      // Check cache first
      if (!skipCache && this.cache.has(cacheKey)) {
        logService.info('Validation cache hit', { validator: 'hgnc', value: geneSymbol })
        return this.cache.get(cacheKey)
      }

      this.loading.set(cacheKey, true)
      this.error = null

      try {
        const result = await externalValidationAPI.validateHGNC(geneSymbol, skipCache)
        this.cache.set(cacheKey, result)
        logService.info('HGNC validation complete', {
          geneSymbol,
          isValid: result.is_valid
        })
        return result
      } catch (error) {
        this.error = error.message || 'Validation failed'
        logService.error('HGNC validation failed', { geneSymbol, error: error.message })
        throw error
      } finally {
        this.loading.delete(cacheKey)
      }
    },

    /**
     * Validate PubMed ID
     */
    async validatePubMed(pmid, skipCache = false) {
      const cacheKey = this._getCacheKey('pubmed', pmid)

      if (!skipCache && this.cache.has(cacheKey)) {
        logService.info('Validation cache hit', { validator: 'pubmed', value: pmid })
        return this.cache.get(cacheKey)
      }

      this.loading.set(cacheKey, true)
      this.error = null

      try {
        const result = await externalValidationAPI.validatePubMed(pmid, skipCache)
        this.cache.set(cacheKey, result)
        logService.info('PubMed validation complete', {
          pmid,
          isValid: result.is_valid
        })
        return result
      } catch (error) {
        this.error = error.message || 'Validation failed'
        logService.error('PubMed validation failed', { pmid, error: error.message })
        throw error
      } finally {
        this.loading.delete(cacheKey)
      }
    },

    /**
     * Validate HPO term
     */
    async validateHPO(hpoTerm, skipCache = false) {
      const cacheKey = this._getCacheKey('hpo', hpoTerm)

      if (!skipCache && this.cache.has(cacheKey)) {
        logService.info('Validation cache hit', { validator: 'hpo', value: hpoTerm })
        return this.cache.get(cacheKey)
      }

      this.loading.set(cacheKey, true)
      this.error = null

      try {
        const result = await externalValidationAPI.validateHPO(hpoTerm, skipCache)
        this.cache.set(cacheKey, result)
        logService.info('HPO validation complete', {
          hpoTerm,
          isValid: result.is_valid
        })
        return result
      } catch (error) {
        this.error = error.message || 'Validation failed'
        logService.error('HPO validation failed', { hpoTerm, error: error.message })
        throw error
      } finally {
        this.loading.delete(cacheKey)
      }
    },

    /**
     * Batch validate multiple values
     */
    async validateBatch(validator, values) {
      this.error = null

      try {
        const results = await externalValidationAPI.validateBatch(validator, values)
        // Cache all results
        Object.entries(results).forEach(([value, result]) => {
          const cacheKey = this._getCacheKey(validator, value)
          this.cache.set(cacheKey, result)
        })
        logService.info('Batch validation complete', { validator, count: values.length })
        return results
      } catch (error) {
        this.error = error.message || 'Batch validation failed'
        logService.error('Batch validation failed', { validator, error: error.message })
        throw error
      }
    },

    /**
     * Get cache statistics
     */
    async fetchCacheStatistics() {
      try {
        const stats = await externalValidationAPI.getCacheStatistics()
        logService.info('Cache statistics fetched', { stats })
        return stats
      } catch (error) {
        this.error = error.message || 'Failed to fetch cache statistics'
        logService.error('Failed to fetch cache statistics', { error: error.message })
        throw error
      }
    },

    /**
     * Clear validation cache
     */
    clearCache() {
      this.cache.clear()
      this.loading.clear()
      this.error = null
      logService.info('Validation cache cleared')
    },

    /**
     * Clear error state
     */
    clearError() {
      this.error = null
    }
  }
})
