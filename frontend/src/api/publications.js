import apiClient from './client.js'

/**
 * Publications API client for PMID validation and publication data
 *
 * Provides validation of PubMed IDs using Europe PMC API with caching.
 * Publications are stored locally to reduce API calls and enable
 * association with curations and evidence items.
 */
export const publicationsAPI = {
  /**
   * Validate one or more PubMed IDs
   * @param {string[]} pmids - Array of PMIDs to validate (max 50)
   * @returns {Promise<Object>} Validation response with results
   * @example
   * const result = await publicationsAPI.validatePMIDs(['12345678', '23456789'])
   * // Returns: {
   * //   total_requested: 2,
   * //   valid_count: 2,
   * //   invalid_count: 0,
   * //   results: [{ pmid, is_valid, publication, error }]
   * // }
   */
  async validatePMIDs(pmids) {
    const response = await apiClient.post('/publications/validate', {
      pmids
    })
    return response.data
  },

  /**
   * Validate a single PMID (convenience method)
   * @param {string} pmid - Single PMID to validate
   * @returns {Promise<Object>} Validation result for the PMID
   * @example
   * const result = await publicationsAPI.validatePMID('12345678')
   * // Returns: { pmid, is_valid, publication, error }
   */
  async validatePMID(pmid) {
    const response = await this.validatePMIDs([pmid])
    return response.results[0]
  },

  /**
   * Get publication by PMID
   * @param {string} pmid - PubMed ID
   * @returns {Promise<Object>} Publication data
   * @example
   * const pub = await publicationsAPI.getPublication('12345678')
   * // Returns: { pmid, title, authors, journal, year, doi, ... }
   */
  async getPublication(pmid) {
    const response = await apiClient.get(`/publications/${pmid}`)
    return response.data
  },

  /**
   * List cached publications
   * @param {Object} options - Query options
   * @param {number} options.skip - Pagination offset (default: 0)
   * @param {number} options.limit - Max results (default: 50, max: 100)
   * @param {string} options.search - Optional search term for title/authors
   * @returns {Promise<Object[]>} Array of publication data
   */
  async listPublications({ skip = 0, limit = 50, search = null } = {}) {
    const params = { skip, limit }
    if (search) {
      params.search = search
    }
    const response = await apiClient.get('/publications', { params })
    return response.data
  },

  /**
   * Get publication cache statistics
   * @returns {Promise<Object>} Cache statistics
   * @example
   * const stats = await publicationsAPI.getStats()
   * // Returns: { total_cached: 150, open_access_count: 45 }
   */
  async getStats() {
    const response = await apiClient.get('/publications/stats/count')
    return response.data
  }
}
