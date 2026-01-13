import apiClient from './client.js'

/**
 * Precuration API client
 *
 * Handles all precuration-related API calls following RESTful conventions.
 * Precurations are the first stage in the curation workflow.
 *
 * @module api/precurations
 */
export const precurationsAPI = {
  /**
   * Get all precurations (with optional filters)
   * @param {Object} params - Query parameters (scope_id, gene_id, status, etc.)
   * @returns {Promise<Array>} Array of precurations
   */
  async getPrecurations(params = {}) {
    const response = await apiClient.get('/precurations/', { params })
    return response.data
  },

  /**
   * Get single precuration by ID
   * @param {string} id - Precuration UUID
   * @returns {Promise<Object>} Precuration object
   */
  async getPrecuration(id) {
    const response = await apiClient.get(`/precurations/${id}`)
    return response.data
  },

  /**
   * Create new precuration
   * @param {Object} data - Precuration data
   * @param {string} data.gene_id - Gene UUID
   * @param {string} data.scope_id - Scope UUID
   * @param {string} data.precuration_schema_id - Schema UUID
   * @param {Object} data.evidence_data - Schema-agnostic evidence data
   * @returns {Promise<Object>} Created precuration
   */
  async createPrecuration(data) {
    const response = await apiClient.post('/precurations/', data)
    return response.data
  },

  /**
   * Update precuration
   * @param {string} id - Precuration UUID
   * @param {Object} data - Updated precuration data
   * @param {number} data.lock_version - Optimistic locking version
   * @returns {Promise<Object>} Updated precuration
   * @throws {409} If lock_version doesn't match (conflict)
   */
  async updatePrecuration(id, data) {
    const response = await apiClient.put(`/precurations/${id}`, data)
    return response.data
  },

  /**
   * Save precuration as draft
   * @param {string} id - Precuration UUID
   * @param {Object} data - Draft data
   * @returns {Promise<Object>} Updated precuration
   */
  async saveDraft(id, data) {
    const response = await apiClient.patch(`/precurations/${id}/draft`, data)
    return response.data
  },

  /**
   * Submit precuration (mark as complete)
   * @param {string} id - Precuration UUID
   * @param {Object} data - Submission data
   * @returns {Promise<Object>} Submitted precuration
   */
  async submitPrecuration(id, data = {}) {
    const response = await apiClient.post(`/precurations/${id}/submit`, data)
    return response.data
  },

  /**
   * Approve precuration (creates curation if configured)
   * @param {string} id - Precuration UUID
   * @returns {Promise<Object>} Approval result with optional curation_id
   */
  async approvePrecuration(id) {
    const response = await apiClient.post(`/precurations/${id}/approve`)
    return response.data
  },

  /**
   * Reject precuration
   * @param {string} id - Precuration UUID
   * @param {Object} data - Rejection data
   * @param {string} data.reason - Rejection reason
   * @returns {Promise<Object>} Rejected precuration
   */
  async rejectPrecuration(id, data) {
    const response = await apiClient.post(`/precurations/${id}/reject`, data)
    return response.data
  },

  /**
   * Delete precuration (soft delete)
   * @param {string} id - Precuration UUID
   * @returns {Promise<void>}
   */
  async deletePrecuration(id) {
    await apiClient.delete(`/precurations/${id}`)
  },

  /**
   * Get precurations for a specific gene in a scope
   * @param {string} geneId - Gene UUID
   * @param {string} scopeId - Scope UUID
   * @returns {Promise<Array>} Array of precurations
   */
  async getPrecurationsByGeneAndScope(geneId, scopeId) {
    const response = await apiClient.get('/precurations/', {
      params: { gene_id: geneId, scope_id: scopeId }
    })
    return response.data
  },

  /**
   * Get precuration statistics
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Statistics object
   */
  async getPrecurationStatistics(params = {}) {
    const response = await apiClient.get('/precurations/statistics/', { params })
    return response.data
  },

  /**
   * Validate precuration data against schema
   * @param {Object} data - Precuration data to validate
   * @param {string} schemaId - Schema UUID
   * @returns {Promise<Object>} Validation result
   */
  async validatePrecurationData(data, schemaId) {
    const response = await apiClient.post('/precurations/validate', {
      data,
      schema_id: schemaId
    })
    return response.data
  }
}
