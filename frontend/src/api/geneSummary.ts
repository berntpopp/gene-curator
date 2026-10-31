import apiClient from './client'
import type { Schema } from '@/types/api'

/**
 * Gene Summary API client for cross-scope aggregation
 */
export const geneSummaryAPI = {
  /**
   * Get public gene summary (unauthenticated)
   * @param geneId - Gene UUID
   * @returns Public gene summary; null when the gene has no public curation (200) or is unknown (404)
   */
  async getPublicSummary(geneId: string): Promise<Schema<'GeneSummaryPublic'> | null> {
    try {
      const response = await apiClient.get<Schema<'GeneSummaryPublic'> | null>(
        `/genes/${geneId}/summary`
      )
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
  }
}
