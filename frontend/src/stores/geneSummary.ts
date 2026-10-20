import { defineStore } from 'pinia'
import { toApiError, apiData } from './apiError'
import { geneSummaryAPI } from '@/api/geneSummary'
import { logService } from '@/services/logService'
import type { Schema } from '@/types/api'

/**
 * Gene Summary store for cross-scope aggregation
 */
export const useGeneSummaryStore = defineStore('geneSummary', {
  state: () => ({
    publicSummaries: new Map<string, Schema<'GeneSummaryPublic'>>(),
    fullSummaries: new Map<string, Schema<'GeneSummaryFull'>>(),
    loading: false,
    error: null as string | null
  }),

  getters: {
    /**
     * Get public summary for a gene
     */
    getPublicSummary: state => (geneId: string) => {
      return state.publicSummaries.get(geneId) || null
    },

    /**
     * Get full summary for a gene
     */
    getFullSummary: state => (geneId: string) => {
      return state.fullSummaries.get(geneId) || null
    }
  },

  actions: {
    /**
     * Fetch public gene summary (unauthenticated)
     */
    async fetchPublicSummary(geneId: string) {
      this.loading = true
      this.error = null

      try {
        const summary = apiData<Schema<'GeneSummaryPublic'> | null>(
          await geneSummaryAPI.getPublicSummary(geneId)
        )
        if (summary) {
          this.publicSummaries.set(geneId, summary)
          logService.info('Public gene summary fetched', { geneId })
        } else {
          logService.info('No public curations for gene', { geneId })
        }
        return summary
      } catch (error) {
        this.error = toApiError(error).message || 'Failed to fetch gene summary'
        logService.error('Failed to fetch public summary', {
          geneId,
          error: toApiError(error).message
        })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Fetch full gene summary (authenticated, includes private scopes)
     */
    async fetchFullSummary(geneId: string) {
      this.loading = true
      this.error = null

      try {
        const summary = apiData<Schema<'GeneSummaryFull'>>(
          await geneSummaryAPI.getFullSummary(geneId)
        )
        this.fullSummaries.set(geneId, summary)
        logService.info('Full gene summary fetched', { geneId })
        return summary
      } catch (error) {
        this.error = toApiError(error).message || 'Failed to fetch full summary'
        logService.error('Failed to fetch full summary', {
          geneId,
          error: toApiError(error).message
        })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Manually recompute gene summary (admin only)
     */
    async recomputeSummary(geneId: string) {
      this.loading = true
      this.error = null

      try {
        await geneSummaryAPI.recomputeSummary(geneId)
        // Invalidate cached summaries
        this.publicSummaries.delete(geneId)
        this.fullSummaries.delete(geneId)
        logService.info('Gene summary recomputed', { geneId })
      } catch (error) {
        this.error = toApiError(error).message || 'Failed to recompute summary'
        logService.error('Failed to recompute summary', {
          geneId,
          error: toApiError(error).message
        })
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
