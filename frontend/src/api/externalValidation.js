import apiClient from './client.js'

/**
 * External Validation API client for HGNC, PubMed, HPO validation
 */
export const externalValidationAPI = {
  /**
   * Validate HGNC gene symbol
   * @param {string} geneSymbol - Gene symbol to validate
   * @param {boolean} skipCache - Skip cache and force fresh validation
   * @returns {Promise<Object>} Validation result with gene data
   */
  async validateHGNC(geneSymbol, skipCache = false) {
    const response = await apiClient.post('/external-validation/validate/hgnc', null, {
      params: { gene_symbol: geneSymbol, skip_cache: skipCache }
    })
    return response.data
  },

  /**
   * Validate PubMed ID
   * @param {string} pmid - PubMed ID to validate
   * @param {boolean} skipCache - Skip cache and force fresh validation
   * @returns {Promise<Object>} Validation result with publication data
   */
  async validatePubMed(pmid, skipCache = false) {
    const response = await apiClient.post('/external-validation/validate/pubmed', null, {
      params: { pmid, skip_cache: skipCache }
    })
    return response.data
  },

  /**
   * Validate HPO term
   * @param {string} hpoTerm - HPO term to validate (e.g., HP:0001250)
   * @param {boolean} skipCache - Skip cache and force fresh validation
   * @returns {Promise<Object>} Validation result with HPO term data
   */
  async validateHPO(hpoTerm, skipCache = false) {
    const response = await apiClient.post('/external-validation/validate/hpo', null, {
      params: { hpo_term: hpoTerm, skip_cache: skipCache }
    })
    return response.data
  },

  /**
   * Batch validate multiple values
   * @param {string} validator - Validator name ('hgnc', 'pubmed', 'hpo')
   * @param {Array<string>} values - Array of values to validate
   * @returns {Promise<Object>} Map of value -> validation result
   */
  async validateBatch(validator, values) {
    const response = await apiClient.post('/external-validation/validate/batch', {
      validator_name: validator,
      values
    })
    return response.data
  },

  /**
   * Get cache statistics
   * @returns {Promise<Object>} Cache statistics by validator
   */
  async getCacheStatistics() {
    const response = await apiClient.get('/external-validation/cache/statistics')
    return response.data
  }
}
