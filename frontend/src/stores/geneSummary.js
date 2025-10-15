import { defineStore } from 'pinia'
import { geneSummaryAPI } from '@/api/geneSummary.js'
import { logService } from '@/services/logService'

/**
 * Gene Summary store for cross-scope aggregation
 */
export const useGeneSummaryStore = defineStore('geneSummary', {
  state: () => ({
    publicSummaries: new Map(),
    fullSummaries: new Map(),
    loading: false,
    error: null
  }),

  getters: {
    /**
     * Get public summary for a gene
     */
    getPublicSummary: state => geneId => {
      return state.publicSummaries.get(geneId) || null
    },

    /**
     * Get full summary for a gene
     */
    getFullSummary: state => geneId => {
      return state.fullSummaries.get(geneId) || null
    }
  },

  actions: {
    /**
     * Fetch public gene summary (unauthenticated)
     */
    async fetchPublicSummary(geneId) {
      this.loading = true
      this.error = null

      try {
        const summary = await geneSummaryAPI.getPublicSummary(geneId)
        if (summary) {
          this.publicSummaries.set(geneId, summary)
          logService.info('Public gene summary fetched', { geneId })
        } else {
          logService.info('No public curations for gene', { geneId })
        }
        return summary
      } catch (error) {
        this.error = error.message || 'Failed to fetch gene summary'
        logService.error('Failed to fetch public summary', { geneId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Fetch full gene summary (authenticated, includes private scopes)
     */
    async fetchFullSummary(geneId) {
      this.loading = true
      this.error = null

      try {
        const summary = await geneSummaryAPI.getFullSummary(geneId)
        this.fullSummaries.set(geneId, summary)
        logService.info('Full gene summary fetched', { geneId })
        return summary
      } catch (error) {
        this.error = error.message || 'Failed to fetch full summary'
        logService.error('Failed to fetch full summary', { geneId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Manually recompute gene summary (admin only)
     */
    async recomputeSummary(geneId) {
      this.loading = true
      this.error = null

      try {
        await geneSummaryAPI.recomputeSummary(geneId)
        // Invalidate cached summaries
        this.publicSummaries.delete(geneId)
        this.fullSummaries.delete(geneId)
        logService.info('Gene summary recomputed', { geneId })
      } catch (error) {
        this.error = error.message || 'Failed to recompute summary'
        logService.error('Failed to recompute summary', { geneId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Clear all summaries from store
     */
    clearSummaries() {
      this.publicSummaries.clear()
      this.fullSummaries.clear()
      this.error = null
    },

    /**
     * Clear error state
     */
    clearError() {
      this.error = null
    }
  }
})
