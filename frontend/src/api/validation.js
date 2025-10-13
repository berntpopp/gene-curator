import apiClient from './client.js'

export const validationAPI = {
  /**
   * Validate evidence data against schema
   */
  async validateEvidence(validationData) {
    const response = await apiClient.post('/validation/validate-evidence', validationData)
    return response.data
  },

  /**
   * Validate schema definition
   */
  async validateSchema(schemaData) {
    const response = await apiClient.post('/validation/validate-schema', schemaData)
    return response.data
  },

  /**
   * Generate JSON Schema for UI from schema definition
   */
  async generateJsonSchema(schemaId) {
    const response = await apiClient.get(`/validation/generate-json-schema/${schemaId}`)
    return response.data
  },

  /**
   * Get supported field types
   */
  async getSupportedFieldTypes() {
    const response = await apiClient.get('/validation/supported-field-types')
    return response.data
  },

  /**
   * Get business rules documentation
   */
  async getBusinessRules() {
    const response = await apiClient.get('/validation/business-rules')
    return response.data
  },

  /**
   * Validate field value
   */
  async validateField(fieldData) {
    const response = await apiClient.post('/validation/validate-field', fieldData)
    return response.data
  }
}
