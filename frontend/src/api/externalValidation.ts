import apiClient from './client'
import type { Schema } from '@/types/api'

/**
 * External Validation API client for HGNC, PubMed, HPO validation
 */
export const externalValidationAPI = {
  /**
   * Validate HGNC gene symbol
   * @param geneSymbol - Gene symbol to validate
   * @param skipCache - Skip cache and force fresh validation
   */
  async validateHGNC(geneSymbol: string, skipCache = false): Promise<Schema<'ValidationResult'>> {
    const response = await apiClient.post<Schema<'ValidationResult'>>(
      '/external-validation/validate/hgnc',
      null,
      { params: { gene_symbol: geneSymbol, skip_cache: skipCache } }
    )
    return response.data
  },

  /**
   * Validate PubMed ID
   * @param pmid - PubMed ID to validate
   * @param skipCache - Skip cache and force fresh validation
   */
  async validatePubMed(pmid: string, skipCache = false): Promise<Schema<'ValidationResult'>> {
    const response = await apiClient.post<Schema<'ValidationResult'>>(
      '/external-validation/validate/pubmed',
      null,
      { params: { pmid, skip_cache: skipCache } }
    )
    return response.data
  },

  /**
   * Validate HPO term
   * @param hpoTerm - HPO term to validate (e.g., HP:0001250)
   * @param skipCache - Skip cache and force fresh validation
   */
  async validateHPO(hpoTerm: string, skipCache = false): Promise<Schema<'ValidationResult'>> {
    const response = await apiClient.post<Schema<'ValidationResult'>>(
      '/external-validation/validate/hpo',
      null,
      { params: { hpo_term: hpoTerm, skip_cache: skipCache } }
    )
    return response.data
  },

  /**
   * Batch validate multiple values
   * @param validator - Validator name ('hgnc', 'pubmed', 'hpo')
   * @param values - Array of values to validate
   * @returns Map of value -> validation result
   */
  async validateBatch(validator: string, values: string[]): Promise<unknown> {
    const response = await apiClient.post<unknown>('/external-validation/validate/batch', {
      validator_name: validator,
      values
    })
    return response.data
  },

  /**
   * Get cache statistics
   * @returns Cache statistics by validator
   */
  async getCacheStatistics(): Promise<unknown> {
    const response = await apiClient.get<unknown>('/external-validation/cache/statistics')
    return response.data
  },

  /**
   * Search HGNC database for genes (for autocomplete)
   * @param query - Search query (gene symbol, HGNC ID, or name)
   * @param limit - Maximum number of results (default: 10)
   */
  async searchHGNC(query: string, limit = 10): Promise<Schema<'HGNCSearchResponse'>> {
    const response = await apiClient.post<Schema<'HGNCSearchResponse'>>(
      '/external-validation/hgnc/search',
      { query, limit }
    )
    return response.data
  },

  /**
   * Fetch a single gene by HGNC ID
   * @param hgncId - HGNC ID (e.g., "HGNC:1100" or "1100")
   */
  async fetchHGNCGene(hgncId: string): Promise<Schema<'HGNCSearchResponse'>> {
    const response = await apiClient.get<Schema<'HGNCSearchResponse'>>(
      `/external-validation/hgnc/fetch/${hgncId}`
    )
    return response.data
  }
}
