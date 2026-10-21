import apiClient from './client'
import type { Schema } from '@/types/api'

type PMIDValidationItem = Schema<'PMIDValidationResponse'>['results'][number]

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
   * @param pmids - Array of PMIDs to validate (max 50)
   * @example
   * const result = await publicationsAPI.validatePMIDs(['12345678', '23456789'])
   * // Returns: {
   * //   total_requested: 2,
   * //   valid_count: 2,
   * //   invalid_count: 0,
   * //   results: [{ pmid, is_valid, publication, error }]
   * // }
   */
  async validatePMIDs(
    pmids: string[],
    signal?: AbortSignal
  ): Promise<Schema<'PMIDValidationResponse'>> {
    const response = await apiClient.post<Schema<'PMIDValidationResponse'>>(
      '/publications/validate',
      { pmids },
      ...(signal ? [{ signal }] : [])
    )
    return response.data
  },

  /**
   * Validate a single PMID (convenience method)
   * @param pmid - Single PMID to validate
   * @example
   * const result = await publicationsAPI.validatePMID('12345678')
   * // Returns: { pmid, is_valid, publication, error }
   */
  async validatePMID(pmid: string): Promise<PMIDValidationItem> {
    const response = await this.validatePMIDs([pmid])
    return response.results[0] as PMIDValidationItem
  },

  /**
   * Get publication by PMID
   * @param pmid - PubMed ID
   * @example
   * const pub = await publicationsAPI.getPublication('12345678')
   * // Returns: { pmid, title, authors, journal, year, doi, ... }
   */
  async getPublication(pmid: string): Promise<Schema<'PublicationData'>> {
    const response = await apiClient.get<Schema<'PublicationData'>>(`/publications/${pmid}`)
    return response.data
  },

  /**
   * List cached publications
   * @param options - Query options
   * @param options.skip - Pagination offset (default: 0)
   * @param options.limit - Max results (default: 50, max: 100)
   * @param options.search - Optional search term for title/authors
   * @returns Array of publication data
   */
  async listPublications({
    skip = 0,
    limit = 50,
    search = null
  }: { skip?: number; limit?: number; search?: string | null } = {}): Promise<
    Schema<'PublicationData'>[]
  > {
    const params: Record<string, unknown> = { skip, limit }
    if (search) {
      params.search = search
    }
    const response = await apiClient.get<Schema<'PublicationData'>[]>('/publications', { params })
    return response.data
  },

  /**
   * Get publication cache statistics
   * @example
   * const stats = await publicationsAPI.getStats()
   * // Returns: { total_cached: 150, open_access_count: 45 }
   */
  async getStats(): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>('/publications/stats/count')
    return response.data
  }
}
