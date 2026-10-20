import apiClient from './client'
import type { Schema } from '@/types/api'

type EvidenceValidationRequest =
  Schema<'app__api__v1__endpoints__schema_validation__ValidationRequest'>

export const validationAPI = {
  /**
   * Validate evidence data against schema
   */
  async validateEvidence(
    validationData: EvidenceValidationRequest
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
  async generateJsonSchema(schemaId: string): Promise<Schema<'JSONSchemaResponse'>> {
    const response = await apiClient.get<Schema<'JSONSchemaResponse'>>(
      `/validation/schema/${schemaId}/json-schema`
    )
    return response.data
  },

  /**
   * Get supported field types
   */
  async getSupportedFieldTypes(): Promise<Record<string, Record<string, unknown>>> {
    const response = await apiClient.get<Record<string, Record<string, unknown>>>(
      '/validation/supported-field-types'
    )
    return response.data
  },

  /**
   * Get business rules documentation
   */
  async getBusinessRules(): Promise<Record<string, Record<string, unknown>>> {
    const response = await apiClient.get<Record<string, Record<string, unknown>>>(
      '/validation/business-rules'
    )
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
