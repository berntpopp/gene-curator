import apiClient from './client.js'

export const assignmentsAPI = {
  /**
   * Get all gene assignments
   */
  async getAssignments(params = {}) {
    const response = await apiClient.get('/gene-assignments', { params })
    return response.data
  },

  /**
   * Create a single gene assignment
   */
  async createAssignment(assignmentData) {
    const response = await apiClient.post('/gene-assignments', assignmentData)
    return response.data
  },

  /**
   * Bulk assign genes to scope
   */
  async bulkAssignGenes(assignmentData) {
    const response = await apiClient.post('/gene-assignments/bulk', assignmentData)
    return response.data
  },

  /**
   * Get curator workload
   */
  async getCuratorWorkload(curatorId) {
    const response = await apiClient.get(`/gene-assignments/curator/${curatorId}/workload`)
    return response.data
  },

  /**
   * Get curator assignments
   */
  async getCuratorAssignments(curatorId, params = {}) {
    const response = await apiClient.get(`/gene-assignments/curator/${curatorId}/assignments`, {
      params
    })
    return response.data
  },

  /**
   * Update assignment priority
   */
  async updateAssignmentPriority(assignmentId, priority) {
    const response = await apiClient.put(`/gene-assignments/${assignmentId}/priority`, {
      priority_level: priority
    })
    return response.data
  },

  /**
   * Get assignments by scope
   */
  async getAssignmentsByScope(scopeId, params = {}) {
    const response = await apiClient.get(`/gene-assignments/scope/${scopeId}`, { params })
    return response.data
  },

  /**
   * Get available genes for scope assignment
   */
  async getAvailableGenesForScope(scopeId) {
    const response = await apiClient.get(`/gene-assignments/scope/${scopeId}/available-genes`)
    return response.data
  },

  /**
   * Get scope assignment overview
   */
  async getScopeAssignmentOverview(scopeId) {
    const response = await apiClient.get(`/gene-assignments/scope/${scopeId}/overview`)
    return response.data
  }
}
