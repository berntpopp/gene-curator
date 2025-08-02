import apiClient from './client.js'

export const schemasAPI = {
  /**
   * Get all schemas
   */
  async getSchemas(params = {}) {
    const response = await apiClient.get('/schemas', { params })
    return response.data
  },

  /**
   * Get schema by ID
   */
  async getSchemaById(id) {
    const response = await apiClient.get(`/schemas/${id}`)
    return response.data
  },

  /**
   * Create new schema
   */
  async createSchema(schemaData) {
    const response = await apiClient.post('/schemas', schemaData)
    return response.data
  },

  /**
   * Update schema
   */
  async updateSchema(id, schemaData) {
    const response = await apiClient.put(`/schemas/${id}`, schemaData)
    return response.data
  },

  /**
   * Delete schema
   */
  async deleteSchema(id) {
    const response = await apiClient.delete(`/schemas/${id}`)
    return response.data
  },

  /**
   * Get schema usage statistics
   */
  async getSchemaUsageStatistics(id) {
    const response = await apiClient.get(`/schemas/${id}/usage-statistics`)
    return response.data
  },

  /**
   * Get workflow pairs for schema
   */
  async getWorkflowPairs(params = {}) {
    const response = await apiClient.get('/schemas/workflow-pairs', { params })
    return response.data
  },

  /**
   * Create workflow pair
   */
  async createWorkflowPair(pairData) {
    const response = await apiClient.post('/schemas/workflow-pairs', pairData)
    return response.data
  },

  /**
   * Get workflow pair by ID
   */
  async getWorkflowPairById(id) {
    const response = await apiClient.get(`/schemas/workflow-pairs/${id}`)
    return response.data
  },

  /**
   * Update workflow pair
   */
  async updateWorkflowPair(id, pairData) {
    const response = await apiClient.put(`/schemas/workflow-pairs/${id}`, pairData)
    return response.data
  },

  /**
   * Delete workflow pair
   */
  async deleteWorkflowPair(id) {
    const response = await apiClient.delete(`/schemas/workflow-pairs/${id}`)
    return response.data
  }
}
