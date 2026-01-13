import apiClient from './client.js'

export const scopesAPI = {
  /**
   * Get all scopes
   */
  async getScopes(params = {}) {
    const response = await apiClient.get('/scopes', { params })
    return response.data
  },

  /**
   * Get scope by ID
   */
  async getScopeById(id) {
    const response = await apiClient.get(`/scopes/${id}`)
    return response.data
  },

  /**
   * Create new scope
   */
  async createScope(scopeData) {
    const response = await apiClient.post('/scopes', scopeData)
    return response.data
  },

  /**
   * Update scope (partial update)
   */
  async updateScope(id, scopeData) {
    const response = await apiClient.patch(`/scopes/${id}`, scopeData)
    return response.data
  },

  /**
   * Delete scope
   * @param {string} id - Scope ID
   * @param {Object} options - Options
   * @param {boolean} options.force - Force deletion even with active gene assignments
   */
  async deleteScope(id, { force = false } = {}) {
    const params = force ? { force: true } : {}
    const response = await apiClient.delete(`/scopes/${id}`, { params })
    return response.data
  },

  /**
   * Get scope statistics
   */
  async getScopeStatistics(id) {
    const response = await apiClient.get(`/scopes/${id}/statistics`)
    return response.data
  },

  /**
   * Get users in scope
   */
  async getScopeUsers(id) {
    const response = await apiClient.get(`/scopes/${id}/users`)
    return response.data
  },

  /**
   * Assign user to scope
   */
  async assignUserToScope(scopeId, userId, roleData) {
    const response = await apiClient.post(`/scopes/${scopeId}/users/${userId}`, roleData)
    return response.data
  },

  /**
   * Remove user from scope
   */
  async removeUserFromScope(scopeId, userId) {
    const response = await apiClient.delete(`/scopes/${scopeId}/users/${userId}`)
    return response.data
  }
}
