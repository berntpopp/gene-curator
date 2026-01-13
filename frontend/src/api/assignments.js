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
   * Update gene assignment (curator, priority, notes, etc.)
   */
  async updateAssignment(assignmentId, updateData) {
    const response = await apiClient.put(`/gene-assignments/${assignmentId}`, updateData)
    return response.data
  },

  /**
   * Assign a curator to a gene-scope assignment
   */
  async assignCurator(assignmentId, curatorId) {
    const response = await apiClient.post(`/gene-assignments/${assignmentId}/assign-curator`, {
      curator_id: curatorId
    })
    return response.data
  },

  /**
   * Remove a gene assignment from scope (deactivate)
   * @param {string} assignmentId - Assignment UUID
   * @param {string} reason - Reason for removal
   */
  async removeAssignment(assignmentId, reason = 'Removed from scope') {
    const response = await apiClient.delete(`/gene-assignments/${assignmentId}`, {
      data: { reason }
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
