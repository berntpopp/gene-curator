import apiClient from './client.js'

/**
 * Curation API client
 *
 * Handles all curation-related API calls following RESTful conventions.
 * Curations are the second stage in the workflow after precuration.
 *
 * @module api/curations
 */
export const curationsAPI = {
  /**
   * Get all curations (with optional filters)
   * @param {Object} params - Query parameters (scope_id, gene_id, status, etc.)
   * @returns {Promise<Array>} Array of curations
   */
  async getCurations(params = {}) {
    const response = await apiClient.get('/curations', { params })
    return response.data
  },

  /**
   * Get single curation by ID
   * @param {string} id - Curation UUID
   * @returns {Promise<Object>} Curation object
   */
  async getCuration(id) {
    const response = await apiClient.get(`/curations/${id}`)
    return response.data
  },

  /**
   * Create new curation
   * @param {Object} data - Curation data
   * @param {string} data.gene_id - Gene UUID
   * @param {string} data.scope_id - Scope UUID
   * @param {string} data.curation_schema_id - Schema UUID
   * @param {string} data.precuration_id - Optional parent precuration UUID
   * @param {Object} data.evidence_data - Schema-agnostic evidence data
   * @returns {Promise<Object>} Created curation
   */
  async createCuration(data) {
    const response = await apiClient.post('/curations', data)
    return response.data
  },

  /**
   * Update curation
   * @param {string} id - Curation UUID
   * @param {Object} data - Updated curation data
   * @param {number} data.lock_version - Optimistic locking version
   * @returns {Promise<Object>} Updated curation
   * @throws {409} If lock_version doesn't match (conflict)
   */
  async updateCuration(id, data) {
    const response = await apiClient.put(`/curations/${id}`, data)
    return response.data
  },

  /**
   * Save curation as draft
   * @param {string} id - Curation UUID
   * @param {Object} data - Draft data
   * @returns {Promise<Object>} Updated curation
   */
  async saveDraft(id, data) {
    const response = await apiClient.patch(`/curations/${id}/draft`, data)
    return response.data
  },

  /**
   * Submit curation (mark as complete)
   * @param {string} id - Curation UUID
   * @param {Object} data - Submission data
   * @returns {Promise<Object>} Submitted curation
   */
  async submitCuration(id, data = {}) {
    const response = await apiClient.post(`/curations/${id}/submit`, data)
    return response.data
  },

  /**
   * Delete curation (soft delete)
   * @param {string} id - Curation UUID
   * @returns {Promise<void>}
   */
  async deleteCuration(id) {
    await apiClient.delete(`/curations/${id}`)
  },

  /**
   * Get curations for a specific gene in a scope
   * @param {string} geneId - Gene UUID
   * @param {string} scopeId - Scope UUID
   * @returns {Promise<Array>} Array of curations
   */
  async getCurationsByGeneAndScope(geneId, scopeId) {
    const response = await apiClient.get('/curations', {
      params: { gene_id: geneId, scope_id: scopeId }
    })
    return response.data
  },

  /**
   * Get curation statistics
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Statistics object
   */
  async getCurationStatistics(params = {}) {
    const response = await apiClient.get('/curations/statistics', { params })
    return response.data
  },

  /**
   * Validate curation data against schema
   * @param {Object} data - Curation data to validate
   * @param {string} schemaId - Schema UUID
   * @returns {Promise<Object>} Validation result
   */
  async validateCurationData(data, schemaId) {
    const response = await apiClient.post('/curations/validate', {
      data,
      schema_id: schemaId
    })
    return response.data
  },

  /**
   * Add evidence item to curation
   * @param {string} id - Curation UUID
   * @param {Object} evidenceItem - Evidence item data
   * @param {string} evidenceItem.category - Evidence category (genetic/experimental/contradictory)
   * @param {string} evidenceItem.type - Evidence type
   * @param {string} evidenceItem.description - Evidence description
   * @param {Array<string>} evidenceItem.pmids - Associated PubMed IDs
   * @returns {Promise<Object>} Updated curation with new evidence item
   */
  async addEvidenceItem(id, evidenceItem) {
    const response = await apiClient.post(`/curations/${id}/evidence`, evidenceItem)
    return response.data
  },

  /**
   * Update evidence item
   * @param {string} curationId - Curation UUID
   * @param {string} evidenceId - Evidence item UUID
   * @param {Object} evidenceItem - Updated evidence data
   * @returns {Promise<Object>} Updated curation
   */
  async updateEvidenceItem(curationId, evidenceId, evidenceItem) {
    const response = await apiClient.put(
      `/curations/${curationId}/evidence/${evidenceId}`,
      evidenceItem
    )
    return response.data
  },

  /**
   * Delete evidence item
   * @param {string} curationId - Curation UUID
   * @param {string} evidenceId - Evidence item UUID
   * @returns {Promise<Object>} Updated curation
   */
  async deleteEvidenceItem(curationId, evidenceId) {
    const response = await apiClient.delete(`/curations/${curationId}/evidence/${evidenceId}`)
    return response.data
  },

  /**
   * Calculate ClinGen score for curation
   * @param {string} id - Curation UUID
   * @returns {Promise<Object>} Score breakdown
   */
  async calculateScore(id) {
    const response = await apiClient.get(`/curations/${id}/score`)
    return response.data
  }
}
