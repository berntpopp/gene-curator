import apiClient from './client.js'

export const workflowAPI = {
  /**
   * Get workflow analytics
   */
  async getWorkflowAnalytics(params = {}) {
    const response = await apiClient.get('/workflow/analytics', { params })
    return response.data
  },

  /**
   * Transition curation to next workflow stage
   */
  async transitionCuration(curationId, transitionData) {
    const response = await apiClient.post(
      `/workflow/curation/${curationId}/transition`,
      transitionData
    )
    return response.data
  },

  /**
   * Get workflow state for an item
   * @param {string} itemType - Item type (curation, precuration)
   * @param {string} itemId - Item UUID
   */
  async getWorkflowState(itemType, itemId) {
    const response = await apiClient.get(`/workflow/${itemType}/${itemId}/state`)
    return response.data
  },

  /**
   * Get available transitions for curation
   * Uses workflow state endpoint which returns available_transitions in response
   */
  async getAvailableTransitions(curationId) {
    const response = await apiClient.get(`/workflow/curation/${curationId}/state`)
    return response.data?.available_transitions || []
  },

  /**
   * Get peer reviewers for workflow stage
   */
  async getPeerReviewers(params = {}) {
    const response = await apiClient.get('/workflow/peer-reviewers', { params })
    return response.data
  },

  /**
   * Submit peer review
   * Uses transition endpoint — the dedicated review endpoint does not exist
   * CurationDetailView already uses transitionCuration() directly for approve/reject
   */
  async submitPeerReview(curationId, reviewData) {
    const response = await apiClient.post(`/workflow/curation/${curationId}/transition`, reviewData)
    return response.data
  },

  /**
   * Get curation workflow history
   */
  async getCurationWorkflowHistory(curationId) {
    const response = await apiClient.get(`/workflow/curation/${curationId}/history`)
    return response.data
  },

  /**
   * Get workflow statistics by stage
   */
  async getWorkflowStatistics(params = {}) {
    const response = await apiClient.get('/workflow/statistics', { params })
    return response.data
  }
}
