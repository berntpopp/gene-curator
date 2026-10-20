import apiClient from './client'
import type { Schema } from '@/types/api'

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
   * @param query - Search query (disease name or MONDO ID)
   * @param limit - Maximum results (default: 10)
   * @example
   * const result = await ontologyAPI.searchMONDO('intellectual disability', 10)
   * // Returns: { query, total_results, results: [{ mondo_id, label, definition, ... }] }
   */
  async searchMONDO(query: string, limit = 10): Promise<Schema<'MONDOSearchResponse'>> {
    const response = await apiClient.post<Schema<'MONDOSearchResponse'>>('/ontology/mondo/search', {
      query,
      limit
    })
    return response.data
  },

  /**
   * Search OMIM for diseases
   * @param query - Search query (disease name or OMIM ID)
   * @param limit - Maximum results (default: 10)
   * @example
   * const result = await ontologyAPI.searchOMIM('Ogden syndrome', 10)
   * // Returns: { query, total_results, results: [{ omim_id, name, mondo_id, gene_symbols }] }
   */
  async searchOMIM(query: string, limit = 10): Promise<Schema<'OMIMSearchResponse'>> {
    const response = await apiClient.post<Schema<'OMIMSearchResponse'>>('/ontology/omim/search', {
      query,
      limit
    })
    return response.data
  },

  /**
   * Get detailed OMIM disease information
   * @param omimId - OMIM ID (e.g., "OMIM:300855" or "300855")
   * @example
   * const disease = await ontologyAPI.getOMIMDisease('300855')
   * // Returns: { omim_id, name, mondo_id, description, phenotypes: { category: [...] }, genes: [...] }
   */
  async getOMIMDisease(omimId: string): Promise<Schema<'OMIMDiseaseResult'>> {
    const response = await apiClient.get<Schema<'OMIMDiseaseResult'>>(
      `/ontology/omim/${encodeURIComponent(omimId)}`
    )
    return response.data
  },

  /**
   * Search HPO ontology for phenotypes
   * @param query - Search query (phenotype name or HPO ID)
   * @param limit - Maximum results (default: 10)
   * @example
   * const result = await ontologyAPI.searchHPO('seizure', 10)
   * // Returns: { query, total_results, results: [{ hpo_id, name, definition, synonyms, descendant_count }] }
   */
  async searchHPO(query: string, limit = 10): Promise<Schema<'HPOSearchResponse'>> {
    const response = await apiClient.post<Schema<'HPOSearchResponse'>>('/ontology/hpo/search', {
      query,
      limit
    })
    return response.data
  },

  /**
   * Validate an HPO term ID
   * @param hpoId - HPO term ID (e.g., "HP:0001250")
   * @returns Search response with single result if valid
   */
  async validateHPO(hpoId: string): Promise<Schema<'HPOSearchResponse'>> {
    const response = await apiClient.get<Schema<'HPOSearchResponse'>>(
      `/ontology/hpo/${encodeURIComponent(hpoId)}/validate`
    )
    return response.data
  },

  /**
   * Get HPO inheritance patterns
   * Returns all valid inheritance pattern terms, categorized as Mendelian and Non-Mendelian.
   * Results are cached server-side.
   * @example
   * const patterns = await ontologyAPI.getInheritancePatterns()
   * // Returns: {
   * //   total_patterns: 14,
   * //   mendelian: [{ hpo_id: "HP:0000006", name: "Autosomal dominant inheritance", ... }],
   * //   non_mendelian: [{ hpo_id: "HP:0010984", name: "Digenic inheritance", ... }],
   * //   cached: false
   * // }
   */
  async getInheritancePatterns(): Promise<Schema<'HPOInheritanceResponse'>> {
    const response = await apiClient.get<Schema<'HPOInheritanceResponse'>>(
      '/ontology/hpo/inheritance'
    )
    return response.data
  }
}
