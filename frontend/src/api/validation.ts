import apiClient from './client'
import type { Schema } from '@/types/api'

export const validationAPI = {
  /**
   * Validate evidence data against schema
   */
  async validateEvidence(
    validationData: Record<string, unknown>
  ): Promise<Schema<'ValidationResponse'>> {
    const response = await apiClient.post<Schema<'ValidationResponse'>>(
      '/validation/validate-evidence',
      validationData
    )
    return response.data
  },

  /**
   * Validate schema definition
   */
  async validateSchema(
    schemaData: Schema<'SchemaValidationRequest'>
  ): Promise<Schema<'ValidationResponse'>> {
    const response = await apiClient.post<Schema<'ValidationResponse'>>(
      '/validation/validate-schema',
      schemaData
    )
    return response.data
  },

  /**
   * Generate JSON Schema for UI from schema definition
   */
  async generateJsonSchema(schemaId: string): Promise<unknown> {
    const response = await apiClient.get<{ json_schema?: unknown }>(
      `/validation/schema/${schemaId}/json-schema`
    )
    // Extract json_schema from the response wrapper
    return response.data.json_schema || response.data
  },

  /**
   * Get supported field types
   */
  async getSupportedFieldTypes(): Promise<unknown> {
    const response = await apiClient.get<unknown>('/validation/supported-field-types')
    return response.data
  },

  /**
   * Get business rules documentation
   */
  async getBusinessRules(): Promise<unknown> {
    const response = await apiClient.get<unknown>('/validation/business-rules')
    return response.data
  },

  /**
   * Validate field value
   */
  async validateField(
    fieldData: Schema<'FieldValidationRequest'>
  ): Promise<Schema<'FieldValidationResponse'>> {
    const response = await apiClient.post<Schema<'FieldValidationResponse'>>(
      '/validation/validate-field',
      fieldData
    )
    return response.data
  }
}
