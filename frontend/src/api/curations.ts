import apiClient from './client'
import type { Schema } from '@/types/api'

/** The UI needs the full curation and score trace; the API defaults to concise answers. */
const FULL = { params: { detail: true } }

/**
 * Curation API client
 *
 * Handles all curation-related API calls following RESTful conventions.
 * Curations are the second stage in the workflow after precuration.
 *
 * @module api/curations
 */
export const curationsAPI = {
  /**
   * Get all curations (with optional filters)
   * @param params - Query parameters (scope_id, gene_id, status, etc.)
   */
  async getCurations(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'CurationListResponse'>> {
    const response = await apiClient.get<Schema<'CurationListResponse'>>('/curations/', { params })
    return response.data
  },

  /**
   * Get single curation by ID
   * @param id - Curation UUID
   */
  async getCuration(id: string): Promise<Schema<'CurationDetail'>> {
    const response = await apiClient.get<Schema<'CurationDetail'>>(`/curations/${id}`, FULL)
    return response.data
  },

  /**
   * Create new curation
   * @param data - Curation data (gene_id, scope_id, curation_schema_id, optional precuration_id, evidence_data)
   */
  async createCuration(data: Schema<'CurationCreate'>): Promise<Schema<'Curation'>> {
    const response = await apiClient.post<Schema<'Curation'>>('/curations/', data)
    return response.data
  },

  /**
   * Update curation
   * @param id - Curation UUID
   * @param data - Updated curation data (includes lock_version for optimistic locking)
   * @throws {409} If lock_version doesn't match (conflict)
   */
  async updateCuration(id: string, data: Schema<'CurationUpdate'>): Promise<Schema<'Curation'>> {
    const response = await apiClient.put<Schema<'Curation'>>(`/curations/${id}`, data, FULL)
    return response.data
  },

  /**
   * Save curation as draft
   * @param id - Curation UUID
   * @param data - Draft data
   */
  async saveDraft(id: string, data: Schema<'CurationDraftSave'>): Promise<Schema<'Curation'>> {
    const response = await apiClient.patch<Schema<'Curation'>>(`/curations/${id}/draft`, data, FULL)
    return response.data
  },

  /**
   * Submit curation (mark as complete)
   * @param id - Curation UUID
   * @param data - Submission data
   */
  async submitCuration(
    id: string,
    data: Partial<Schema<'CurationSubmit'>> = {}
  ): Promise<Schema<'Curation'>> {
    const response = await apiClient.post<Schema<'Curation'>>(`/curations/${id}/submit`, data, FULL)
    return response.data
  },

  /** A scope admin's audited correction of a legacy curation's disease entity (#453). */
  async correctDisease(id: string, data: Schema<'DiseaseCorrection'>): Promise<Schema<'Curation'>> {
    const response = await apiClient.post<Schema<'Curation'>>(
      `/curations/${id}/disease-correction`,
      data
    )
    return response.data
  },

  /**
   * Delete curation (soft delete)
   * @param id - Curation UUID
   */
  async deleteCuration(id: string): Promise<void> {
    await apiClient.delete(`/curations/${id}`)
  },

  /**
   * Calculate ClinGen score for curation
   * @param id - Curation UUID
   */
  async calculateScore(id: string): Promise<Schema<'CurationScoreResponse'>> {
    const response = await apiClient.get<Schema<'CurationScoreResponse'>>(`/curations/${id}/score`)
    return response.data
  }
}
