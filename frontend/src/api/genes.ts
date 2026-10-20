import apiClient from './client'
import type { Schema } from '@/types/api'
import type { MessageResponse } from './responses'

export const genesAPI = {
  /**
   * Get all genes with assignment status
   */
  async getGenes(params: Record<string, unknown> = {}): Promise<Schema<'GeneListResponse'>> {
    const response = await apiClient.get<Schema<'GeneListResponse'>>('/genes/', { params })
    return response.data
  },

  /**
   * Get gene by ID
   */
  async getGeneById(id: string): Promise<Schema<'GeneWithAssignments'>> {
    const response = await apiClient.get<Schema<'GeneWithAssignments'>>(`/genes/${id}`)
    return response.data
  },

  /**
   * Create new gene
   */
  async createGene(geneData: Schema<'GeneCreate'>): Promise<Schema<'Gene'>> {
    const response = await apiClient.post<Schema<'Gene'>>('/genes', geneData)
    return response.data
  },

  /**
   * Update gene
   */
  async updateGene(id: string, geneData: Schema<'GeneUpdate'>): Promise<Schema<'Gene'>> {
    const response = await apiClient.put<Schema<'Gene'>>(`/genes/${id}`, geneData)
    return response.data
  },

  /**
   * Delete gene
   */
  async deleteGene(id: string): Promise<MessageResponse> {
    const response = await apiClient.delete<MessageResponse>(`/genes/${id}`)
    return response.data
  },

  /**
   * Bulk create genes
   */
  async bulkCreateGenes(
    bulkData: Schema<'GeneBulkCreate'>
  ): Promise<Schema<'GeneBulkCreateResponse'>> {
    const response = await apiClient.post<Schema<'GeneBulkCreateResponse'>>('/genes/bulk', bulkData)
    return response.data
  },

  /**
   * Get gene scope assignments
   */
  async getGeneAssignments(id: string): Promise<Schema<'GeneAssignmentStatus'>> {
    const response = await apiClient.get<Schema<'GeneAssignmentStatus'>>(`/genes/${id}/assignments`)
    return response.data
  },

  /**
   * Get gene curation progress by scope
   */
  async getGeneCurationProgress(id: string): Promise<Schema<'GeneCurationProgress'>> {
    const response = await apiClient.get<Schema<'GeneCurationProgress'>>(`/genes/${id}/progress`)
    return response.data
  },

  /**
   * Search genes (GET /genes/search; query, chromosome, hgnc_id, scope_id, skip, limit, ...)
   */
  async searchGenes(searchParams: Record<string, unknown> = {}): Promise<Schema<'GeneSummary'>[]> {
    const response = await apiClient.get<Schema<'GeneSummary'>[]>('/genes/search', {
      params: searchParams
    })
    return response.data
  },

  /**
   * Get gene statistics
   */
  async getStatistics(): Promise<Schema<'GeneStatistics'>> {
    const response = await apiClient.get<Schema<'GeneStatistics'>>('/genes/statistics')
    return response.data
  },

  /**
   * Validate gene against HGNC and return validation result
   * @param geneId - Gene UUID to validate
   */
  async validateGene(geneId: string): Promise<Schema<'GeneValidationResult'>> {
    const response = await apiClient.post<Schema<'GeneValidationResult'>>(
      `/genes/${geneId}/validate`
    )
    return response.data
  },

  /**
   * Get gene by HGNC ID
   * @param hgncId - HGNC ID (e.g., "HGNC:1100")
   */
  async getGeneByHGNC(hgncId: string): Promise<Schema<'Gene'>> {
    const response = await apiClient.get<Schema<'Gene'>>(`/genes/hgnc/${hgncId}`)
    return response.data
  },

  /**
   * Get gene by symbol
   * @param symbol - Gene symbol (e.g., "BRCA1")
   */
  async getGeneBySymbol(symbol: string): Promise<Schema<'Gene'>[]> {
    const response = await apiClient.get<Schema<'Gene'>[]>(`/genes/symbol/${symbol}`)
    return response.data
  }
}
