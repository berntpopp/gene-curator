import apiClient from './client.js'

export const genesAPI = {
  /**
   * Get all genes with assignment status
   */
  async getGenes(params = {}) {
    const response = await apiClient.get('/genes/', { params })
    return response.data
  },

  /**
   * Get gene by ID
   */
  async getGeneById(id) {
    const response = await apiClient.get(`/genes/${id}`)
    return response.data
  },

  /**
   * Create new gene
   */
  async createGene(geneData) {
    const response = await apiClient.post('/genes', geneData)
    return response.data
  },

  /**
   * Update gene
   */
  async updateGene(id, geneData) {
    const response = await apiClient.put(`/genes/${id}`, geneData)
    return response.data
  },

  /**
   * Delete gene
   */
  async deleteGene(id) {
    const response = await apiClient.delete(`/genes/${id}`)
    return response.data
  },

  /**
   * Bulk create genes
   */
  async bulkCreateGenes(bulkData) {
    const response = await apiClient.post('/genes/bulk', bulkData)
    return response.data
  },

  /**
   * Get gene scope assignments
   */
  async getGeneAssignments(id) {
    const response = await apiClient.get(`/genes/${id}/assignments`)
    return response.data
  },

  /**
   * Get gene curation progress by scope
   */
  async getGeneCurationProgress(id) {
    const response = await apiClient.get(`/genes/${id}/curation-progress`)
    return response.data
  },

  /**
   * Search genes
   */
  async searchGenes(searchParams) {
    const response = await apiClient.post('/genes/search', searchParams)
    return response.data
  },

  /**
   * Get gene statistics
   */
  async getStatistics() {
    const response = await apiClient.get('/genes/statistics')
    return response.data
  },

  /**
   * Validate gene against HGNC and return validation result
   * @param {string} geneId - Gene UUID to validate
   * @returns {Promise<Object>} Validation result with is_valid, warnings, errors, external_data
   */
  async validateGene(geneId) {
    const response = await apiClient.post(`/genes/${geneId}/validate`)
    return response.data
  },

  /**
   * Get gene by HGNC ID
   * @param {string} hgncId - HGNC ID (e.g., "HGNC:1100")
   * @returns {Promise<Object>} Gene data if found
   */
  async getGeneByHGNC(hgncId) {
    const response = await apiClient.get(`/genes/hgnc/${hgncId}`)
    return response.data
  },

  /**
   * Get gene by symbol
   * @param {string} symbol - Gene symbol (e.g., "BRCA1")
   * @returns {Promise<Object>} Gene data if found
   */
  async getGeneBySymbol(symbol) {
    const response = await apiClient.get(`/genes/symbol/${symbol}`)
    return response.data
  }
}
