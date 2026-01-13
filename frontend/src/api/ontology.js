import apiClient from './client.js'

/**
 * Ontology Search API client for MONDO, OMIM, and HPO
 *
 * Provides search and lookup functionality for biomedical ontologies:
 * - MONDO: Monarch Disease Ontology (diseases)
 * - OMIM: Online Mendelian Inheritance in Man (diseases)
 * - HPO: Human Phenotype Ontology (phenotypes)
 */
export const ontologyAPI = {
  /**
   * Search MONDO ontology for diseases
   * @param {string} query - Search query (disease name or MONDO ID)
   * @param {number} limit - Maximum results (default: 10)
   * @returns {Promise<Object>} Search response with matching diseases
   * @example
   * const result = await ontologyAPI.searchMONDO('intellectual disability', 10)
   * // Returns: { query, total_results, results: [{ mondo_id, label, definition, ... }] }
   */
  async searchMONDO(query, limit = 10) {
    const response = await apiClient.post('/ontology/mondo/search', {
      query,
      limit
    })
    return response.data
  },

  /**
   * Search OMIM for diseases
   * @param {string} query - Search query (disease name or OMIM ID)
   * @param {number} limit - Maximum results (default: 10)
   * @returns {Promise<Object>} Search response with matching diseases
   * @example
   * const result = await ontologyAPI.searchOMIM('Ogden syndrome', 10)
   * // Returns: { query, total_results, results: [{ omim_id, name, mondo_id, gene_symbols }] }
   */
  async searchOMIM(query, limit = 10) {
    const response = await apiClient.post('/ontology/omim/search', {
      query,
      limit
    })
    return response.data
  },

  /**
   * Get detailed OMIM disease information
   * @param {string} omimId - OMIM ID (e.g., "OMIM:300855" or "300855")
   * @returns {Promise<Object>} Full disease details with phenotypes and genes
   * @example
   * const disease = await ontologyAPI.getOMIMDisease('300855')
   * // Returns: { omim_id, name, mondo_id, description, phenotypes: { category: [...] }, genes: [...] }
   */
  async getOMIMDisease(omimId) {
    const response = await apiClient.get(`/ontology/omim/${encodeURIComponent(omimId)}`)
    return response.data
  },

  /**
   * Search HPO ontology for phenotypes
   * @param {string} query - Search query (phenotype name or HPO ID)
   * @param {number} limit - Maximum results (default: 10)
   * @returns {Promise<Object>} Search response with matching phenotypes
   * @example
   * const result = await ontologyAPI.searchHPO('seizure', 10)
   * // Returns: { query, total_results, results: [{ hpo_id, name, definition, synonyms, descendant_count }] }
   */
  async searchHPO(query, limit = 10) {
    const response = await apiClient.post('/ontology/hpo/search', {
      query,
      limit
    })
    return response.data
  },

  /**
   * Validate an HPO term ID
   * @param {string} hpoId - HPO term ID (e.g., "HP:0001250")
   * @returns {Promise<Object>} Search response with single result if valid
   */
  async validateHPO(hpoId) {
    const response = await apiClient.get(`/ontology/hpo/${encodeURIComponent(hpoId)}/validate`)
    return response.data
  },

  /**
   * Get HPO inheritance patterns
   * Returns all valid inheritance pattern terms, categorized as Mendelian and Non-Mendelian.
   * Results are cached server-side.
   * @returns {Promise<Object>} Inheritance patterns response
   * @example
   * const patterns = await ontologyAPI.getInheritancePatterns()
   * // Returns: {
   * //   total_patterns: 14,
   * //   mendelian: [{ hpo_id: "HP:0000006", name: "Autosomal dominant inheritance", ... }],
   * //   non_mendelian: [{ hpo_id: "HP:0010984", name: "Digenic inheritance", ... }],
   * //   cached: false
   * // }
   */
  async getInheritancePatterns() {
    const response = await apiClient.get('/ontology/hpo/inheritance')
    return response.data
  }
}
