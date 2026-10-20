import apiClient from './client'
import type { Schema } from '@/types/api'

/**
 * Gene Summary API client for cross-scope aggregation
 */
export const geneSummaryAPI = {
  /**
   * Get public gene summary (unauthenticated)
   * @param geneId - Gene UUID
   * @returns Public gene summary or null if not found
   */
  async getPublicSummary(geneId: string): Promise<Schema<'GeneSummaryPublic'> | null> {
    try {
      const response = await apiClient.get<Schema<'GeneSummaryPublic'>>(`/genes/${geneId}/summary`)
      return response.data
    } catch (error) {
      if ((error as { response?: { status?: number } }).response?.status === 404) {
        return null
      }
      throw error
    }
  },

  /**
   * Get full gene summary (authenticated, includes private scopes)
   * @param geneId - Gene UUID
   */
  async getFullSummary(geneId: string): Promise<Schema<'GeneSummaryFull'>> {
    const response = await apiClient.get<Schema<'GeneSummaryFull'>>(`/genes/${geneId}/summary/full`)
    return response.data
  },

  /**
   * Get list of scopes curating this gene
   * @param geneId - Gene UUID
   */
  async getGeneScopes(geneId: string): Promise<unknown> {
    const response = await apiClient.get<unknown>(`/genes/${geneId}/scopes`)
    return response.data
  },

  /**
   * Manually recompute gene summary (admin only)
   * @param geneId - Gene UUID
   */
  async recomputeSummary(geneId: string): Promise<unknown> {
    const response = await apiClient.post<unknown>(`/genes/${geneId}/summary/recompute`)
    return response.data
  }
}
