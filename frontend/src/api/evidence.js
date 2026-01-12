import apiClient from './client.js'

/**
 * Evidence API client for ClinGen SOP v11 evidence management
 */
export const evidenceAPI = {
  /**
   * Get all evidence items for a curation
   * @param {string} curationId - Curation UUID
   * @returns {Promise<Array>} Array of evidence items
   */
  async getEvidenceItems(curationId) {
    const response = await apiClient.get(`/curations/${curationId}/evidence`)
    return response.data
  },

  /**
   * Create new evidence item
   * @param {string} curationId - Curation UUID
   * @param {Object} data - Evidence item data
   * @returns {Promise<Object>} Created evidence item
   */
  async createEvidenceItem(curationId, data) {
    const response = await apiClient.post(`/curations/${curationId}/evidence`, data)
    return response.data
  },

  /**
   * Update evidence item
   * @param {string} curationId - Curation UUID
   * @param {string} itemId - Evidence item UUID
   * @param {Object} data - Updated evidence data
   * @returns {Promise<Object>} Updated evidence item
   */
  async updateEvidenceItem(curationId, itemId, data) {
    const response = await apiClient.put(`/curations/${curationId}/evidence/${itemId}`, data)
    return response.data
  },

  /**
   * Delete evidence item (soft delete)
   * @param {string} curationId - Curation UUID
   * @param {string} itemId - Evidence item UUID
   * @returns {Promise<void>}
   */
  async deleteEvidenceItem(curationId, itemId) {
    await apiClient.delete(`/curations/${curationId}/evidence/${itemId}`)
  }
}
