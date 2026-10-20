/**
 * Gene Catalogue API client.
 *
 * The Gene Catalogue is a read-only aggregation layer that provides a unified view
 * of genes with finished curations across all scopes. This API client only supports
 * read operations.
 */
import apiClient from './client'
import type { Schema } from '@/types/api'

export interface CatalogueQuery {
  skip?: number
  limit?: number
  search?: string
  classification?: string
  disease?: string
  scope_id?: string
  chromosome?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export const geneCatalogueAPI = {
  /**
   * Get the Gene Catalogue with filtering and pagination.
   *
   * @param params - Query parameters
   * @param params.skip - Number of records to skip (default: 0)
   * @param params.limit - Maximum records to return (default: 20, max: 100)
   * @param params.search - Search gene symbol, HGNC ID, or aliases
   * @param params.classification - Filter by classification (definitive, strong, etc.)
   * @param params.disease - Search/filter by disease name
   * @param params.scope_id - Filter by specific scope UUID
   * @param params.chromosome - Filter by chromosome
   * @param params.sort_by - Sort field (approved_symbol, total_curations, chromosome)
   * @param params.sort_order - Sort order (asc or desc)
   * @returns Catalogue response with entries, pagination, and summary stats
   */
  async getCatalogue(params: CatalogueQuery = {}): Promise<Schema<'GeneCatalogueResponse'>> {
    const response = await apiClient.get<Schema<'GeneCatalogueResponse'>>('/gene-catalogue/', {
      params
    })
    return response.data
  },

  /**
   * Get available classifications for filtering.
   *
   * @returns List of classification values with active curations
   */
  async getAvailableClassifications(): Promise<string[]> {
    const response = await apiClient.get<string[]>('/gene-catalogue/filters/classifications')
    return response.data
  },

  /**
   * Get available diseases for filtering.
   *
   * @param limit - Maximum diseases to return (default: 50, max: 200)
   * @returns List of unique disease names
   */
  async getAvailableDiseases(limit = 50): Promise<string[]> {
    const response = await apiClient.get<string[]>('/gene-catalogue/filters/diseases', {
      params: { limit }
    })
    return response.data
  },

  /**
   * Get scopes available for filtering.
   *
   * @returns List of scopes with active curations
   */
  async getAvailableScopes(): Promise<Schema<'ScopeFilterOption'>[]> {
    const response = await apiClient.get<Schema<'ScopeFilterOption'>[]>(
      '/gene-catalogue/filters/scopes'
    )
    return response.data
  }
}
