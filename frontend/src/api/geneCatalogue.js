/**
 * Gene Catalogue API client.
 *
 * The Gene Catalogue is a read-only aggregation layer that provides a unified view
 * of genes with finished curations across all scopes. This API client only supports
 * read operations.
 */

import apiClient from './client.js'

export const geneCatalogueAPI = {
  /**
   * Get the Gene Catalogue with filtering and pagination.
   *
   * @param {Object} params - Query parameters
   * @param {number} params.skip - Number of records to skip (default: 0)
   * @param {number} params.limit - Maximum records to return (default: 20, max: 100)
   * @param {string} params.search - Search gene symbol, HGNC ID, or aliases
   * @param {string} params.classification - Filter by classification (definitive, strong, etc.)
   * @param {string} params.disease - Search/filter by disease name
   * @param {string} params.scope_id - Filter by specific scope UUID
   * @param {string} params.chromosome - Filter by chromosome
   * @param {string} params.sort_by - Sort field (approved_symbol, total_curations, chromosome)
   * @param {string} params.sort_order - Sort order (asc or desc)
   * @returns {Promise<Object>} Catalogue response with entries, pagination, and summary stats
   */
  async getCatalogue(params = {}) {
    const response = await apiClient.get('/gene-catalogue/', { params })
    return response.data
  },

  /**
   * Get available classifications for filtering.
   *
   * @returns {Promise<string[]>} List of classification values with active curations
   */
  async getAvailableClassifications() {
    const response = await apiClient.get('/gene-catalogue/filters/classifications')
    return response.data
  },

  /**
   * Get available diseases for filtering.
   *
   * @param {number} limit - Maximum diseases to return (default: 50, max: 200)
   * @returns {Promise<string[]>} List of unique disease names
   */
  async getAvailableDiseases(limit = 50) {
    const response = await apiClient.get('/gene-catalogue/filters/diseases', {
      params: { limit }
    })
    return response.data
  },

  /**
   * Get scopes available for filtering.
   *
   * @returns {Promise<Object[]>} List of scopes with active curations
   */
  async getAvailableScopes() {
    const response = await apiClient.get('/gene-catalogue/filters/scopes')
    return response.data
  }
}
