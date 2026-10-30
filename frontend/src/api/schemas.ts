import apiClient from './client'
import type { Schema } from '@/types/api'
import type { MessageResponse } from './responses'

export const schemasAPI = {
  /**
   * Get all curation schemas
   */
  async getSchemas(params: Record<string, unknown> = {}): Promise<Schema<'CurationSchema'>[]> {
    // Full schemas for the UI; the API lists summary rows by default
    const response = await apiClient.get<Schema<'CurationSchema'>[]>('/schemas/curation-schemas', {
      params: { detail: true, ...params }
    })
    return response.data
  },

  /**
   * Get curation schema by ID
   */
  async getSchemaById(id: string): Promise<Schema<'CurationSchema'>> {
    const response = await apiClient.get<Schema<'CurationSchema'>>(
      `/schemas/curation-schemas/${id}`
    )
    return response.data
  },

  /**
   * Create new curation schema
   */
  async createSchema(
    schemaData: Schema<'CurationSchemaCreate'>
  ): Promise<Schema<'CurationSchema'>> {
    const response = await apiClient.post<Schema<'CurationSchema'>>(
      '/schemas/curation-schemas',
      schemaData
    )
    return response.data
  },

  /**
   * Update curation schema
   */
  async updateSchema(
    id: string,
    schemaData: Schema<'CurationSchemaUpdate'>
  ): Promise<Schema<'CurationSchema'>> {
    const response = await apiClient.put<Schema<'CurationSchema'>>(
      `/schemas/curation-schemas/${id}`,
      schemaData
    )
    return response.data
  },

  /**
   * Published methodology versions of a schema, newest first
   */
  async getVersions(id: string): Promise<Schema<'MethodologyVersion'>[]> {
    const response = await apiClient.get<Schema<'MethodologyVersion'>[]>(
      `/schemas/curation-schemas/${id}/versions`
    )
    return response.data
  },

  /**
   * Publish the schema's saved content as a new immutable methodology version (platform admin)
   */
  async publishVersion(id: string): Promise<Schema<'MethodologyVersion'>> {
    const response = await apiClient.post<Schema<'MethodologyVersion'>>(
      `/schemas/curation-schemas/${id}/versions`
    )
    return response.data
  },

  /**
   * One published methodology version (the snapshot a record is pinned to)
   */
  async getMethodologyVersion(id: string): Promise<Schema<'MethodologyVersion'>> {
    const response = await apiClient.get<Schema<'MethodologyVersion'>>(
      `/schemas/methodology-versions/${id}`
    )
    return response.data
  },

  /**
   * Derive a new inactive schema from a published version (records provenance)
   */
  async deriveSchema(
    id: string,
    versionId: string,
    body: Schema<'MethodologyDerive'>
  ): Promise<Schema<'CurationSchema'>> {
    const response = await apiClient.post<Schema<'CurationSchema'>>(
      `/schemas/curation-schemas/${id}/versions/${versionId}/derive`,
      body
    )
    return response.data
  },

  /**
   * Validate a stored curation schema (field definitions, scoring, validation rules)
   */
  async validateCurationSchema(id: string): Promise<Schema<'SchemaValidationResult'>> {
    const response = await apiClient.post<Schema<'SchemaValidationResult'>>(
      `/schemas/curation-schemas/${id}/validate`
    )
    return response.data
  },

  /**
   * Delete curation schema
   */
  async deleteSchema(id: string): Promise<MessageResponse> {
    const response = await apiClient.delete<MessageResponse>(`/schemas/curation-schemas/${id}`)
    return response.data
  },

  /**
   * Get workflow pairs for schema
   */
  async getWorkflowPairs(params: Record<string, unknown> = {}): Promise<Schema<'WorkflowPair'>[]> {
    const response = await apiClient.get<Schema<'WorkflowPair'>[]>('/schemas/workflow-pairs', {
      params
    })
    return response.data
  },

  /**
   * Create workflow pair
   */
  async createWorkflowPair(
    pairData: Schema<'WorkflowPairCreate'>
  ): Promise<Schema<'WorkflowPair'>> {
    const response = await apiClient.post<Schema<'WorkflowPair'>>(
      '/schemas/workflow-pairs',
      pairData
    )
    return response.data
  },

  /**
   * Get workflow pair by ID
   */
  async getWorkflowPairById(id: string): Promise<Schema<'WorkflowPair'>> {
    const response = await apiClient.get<Schema<'WorkflowPair'>>(`/schemas/workflow-pairs/${id}`)
    return response.data
  },

  /**
   * Update workflow pair
   */
  async updateWorkflowPair(
    id: string,
    pairData: Schema<'WorkflowPairUpdate'>
  ): Promise<Schema<'WorkflowPair'>> {
    const response = await apiClient.put<Schema<'WorkflowPair'>>(
      `/schemas/workflow-pairs/${id}`,
      pairData
    )
    return response.data
  },

  /**
   * Delete workflow pair
   */
  async deleteWorkflowPair(id: string): Promise<MessageResponse> {
    const response = await apiClient.delete<MessageResponse>(`/schemas/workflow-pairs/${id}`)
    return response.data
  }
}
