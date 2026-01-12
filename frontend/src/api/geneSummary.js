import apiClient from './client.js'

/**
 * Gene Summary API client for cross-scope aggregation
 */
export const geneSummaryAPI = {
  /**
   * Get public gene summary (unauthenticated)
   * @param {string} geneId - Gene UUID
   * @returns {Promise<Object|null>} Public gene summary or null if not found
   */
  async getPublicSummary(geneId) {
    try {
      const response = await apiClient.get(`/genes/${geneId}/summary`)
      return response.data
    } catch (error) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  /**
   * Get full gene summary (authenticated, includes private scopes)
   * @param {string} geneId - Gene UUID
   * @returns {Promise<Object>} Full gene summary
   */
  async getFullSummary(geneId) {
    const response = await apiClient.get(`/genes/${geneId}/summary/full`)
    return response.data
  },

  /**
   * Get list of scopes curating this gene
   * @param {string} geneId - Gene UUID
   * @returns {Promise<Array>} Array of scope summaries
   */
  async getGeneScopes(geneId) {
    const response = await apiClient.get(`/genes/${geneId}/scopes`)
    return response.data
  },

  /**
   * Manually recompute gene summary (admin only)
   * @param {string} geneId - Gene UUID
   * @returns {Promise<Object>} Recomputation result
   */
  async recomputeSummary(geneId) {
    const response = await apiClient.post(`/genes/${geneId}/summary/recompute`)
    return response.data
  }
}
