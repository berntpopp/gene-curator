import apiClient from './client'
import type { Schema } from '@/types/api'

export const schemasAPI = {
  /**
   * Get all curation schemas
   */
  async getSchemas(params: Record<string, unknown> = {}): Promise<Schema<'CurationSchema'>[]> {
    const response = await apiClient.get<Schema<'CurationSchema'>[]>('/schemas/curation-schemas', {
      params
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
   * Delete curation schema
   */
  async deleteSchema(id: string): Promise<unknown> {
    const response = await apiClient.delete<unknown>(`/schemas/curation-schemas/${id}`)
    return response.data
  },

  /**
   * Get schema usage statistics
   */
  async getSchemaUsageStatistics(id: string): Promise<unknown> {
    const response = await apiClient.get<unknown>(
      `/schemas/curation-schemas/${id}/usage-statistics`
    )
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
  async deleteWorkflowPair(id: string): Promise<unknown> {
    const response = await apiClient.delete<unknown>(`/schemas/workflow-pairs/${id}`)
    return response.data
  }
}
