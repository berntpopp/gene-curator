import apiClient from './client'
import type { Schema } from '@/types/api'

/**
 * Evidence API client for ClinGen SOP v11 evidence management
 */
export const evidenceAPI = {
  /**
   * Get all evidence items for a curation
   * @param curationId - Curation UUID
   */
  async getEvidenceItems(curationId: string): Promise<Schema<'EvidenceItem'>[]> {
    const response = await apiClient.get<Schema<'EvidenceItem'>[]>(
      `/curations/${curationId}/evidence`
    )
    return response.data
  },

  /**
   * Create new evidence item
   * @param curationId - Curation UUID
   * @param data - Evidence item data
   */
  async createEvidenceItem(
    curationId: string,
    data: Schema<'EvidenceItemCreate'>
  ): Promise<Schema<'EvidenceItem'>> {
    const response = await apiClient.post<Schema<'EvidenceItem'>>(
      `/curations/${curationId}/evidence`,
      data
    )
    return response.data
  },

  /**
   * Update evidence item
   * @param curationId - Curation UUID
   * @param itemId - Evidence item UUID
   * @param data - Updated evidence data
   */
  async updateEvidenceItem(
    curationId: string,
    itemId: string,
    data: Schema<'EvidenceItemUpdate'>
  ): Promise<Schema<'EvidenceItem'>> {
    const response = await apiClient.put<Schema<'EvidenceItem'>>(
      `/curations/${curationId}/evidence/${itemId}`,
      data
    )
    return response.data
  },

  /**
   * Delete evidence item (soft delete)
   * @param curationId - Curation UUID
   * @param itemId - Evidence item UUID
   */
  async deleteEvidenceItem(curationId: string, itemId: string): Promise<void> {
    await apiClient.delete(`/curations/${curationId}/evidence/${itemId}`)
  }
}
