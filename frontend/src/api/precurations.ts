import apiClient from './client'
import type { Schema } from '@/types/api'

/**
 * Precuration API client
 *
 * Handles all precuration-related API calls following RESTful conventions.
 * Precurations are the first stage in the curation workflow.
 *
 * @module api/precurations
 */
export const precurationsAPI = {
  /**
   * Get all precurations (with optional filters)
   * @param params - Query parameters (scope_id, gene_id, status, etc.)
   */
  async getPrecurations(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'PrecurationListResponse'>> {
    const response = await apiClient.get<Schema<'PrecurationListResponse'>>('/precurations/', {
      params
    })
    return response.data
  },

  /**
   * Get single precuration by ID
   * @param id - Precuration UUID
   */
  async getPrecuration(id: string): Promise<Schema<'Precuration'>> {
    const response = await apiClient.get<Schema<'Precuration'>>(`/precurations/${id}`)
    return response.data
  },

  /**
   * Create new precuration
   * @param data - Precuration data (gene_id, scope_id, precuration_schema_id, evidence_data)
   */
  async createPrecuration(data: Schema<'PrecurationCreate'>): Promise<Schema<'Precuration'>> {
    const response = await apiClient.post<Schema<'Precuration'>>('/precurations/', data)
    return response.data
  },

  /**
   * Update precuration
   * @param id - Precuration UUID
   * @param data - Updated precuration data (includes lock_version for optimistic locking)
   * @throws {409} If lock_version doesn't match (conflict)
   */
  async updatePrecuration(
    id: string,
    data: Schema<'PrecurationUpdate'>
  ): Promise<Schema<'Precuration'>> {
    const response = await apiClient.put<Schema<'Precuration'>>(`/precurations/${id}`, data)
    return response.data
  },

  /**
   * Save precuration as draft
   * @param id - Precuration UUID
   * @param data - Draft data with the lock_version this client loaded
   * @throws {409} If lock_version doesn't match (another tab saved first)
   */
  async saveDraft(
    id: string,
    data: Schema<'PrecurationDraftSave'>
  ): Promise<Schema<'Precuration'>> {
    const response = await apiClient.patch<Schema<'Precuration'>>(`/precurations/${id}/draft`, data)
    return response.data
  },

  /**
   * Submit precuration for peer review
   * @param id - Precuration UUID
   * @param data - Submission data
   */
  async submitPrecuration(
    id: string,
    data: Schema<'PrecurationSubmit'>
  ): Promise<Schema<'Precuration'>> {
    const response = await apiClient.post<Schema<'Precuration'>>(`/precurations/${id}/submit`, data)
    return response.data
  },

  /**
   * Complete precuration (mark as ready for curation without peer review)
   *
   * This is a simplified workflow path that skips peer review.
   * Use when precuration doesn't require 4-eyes principle validation.
   * After completion, curation can begin immediately.
   *
   * @param id - Precuration UUID
   */
  async completePrecuration(id: string): Promise<Schema<'Precuration'>> {
    const response = await apiClient.post<Schema<'Precuration'>>(`/precurations/${id}/complete`)
    return response.data
  },

  /**
   * Approve precuration (creates curation if configured)
   * @param id - Precuration UUID
   */
  async approvePrecuration(id: string): Promise<Schema<'PrecurationApprovalResult'>> {
    const response = await apiClient.post<Schema<'PrecurationApprovalResult'>>(
      `/precurations/${id}/approve`
    )
    return response.data
  },

  /**
   * Reject precuration
   * @param id - Precuration UUID
   * @param data - Rejection data (reason)
   */
  async rejectPrecuration(
    id: string,
    data: Record<string, unknown>
  ): Promise<Schema<'Precuration'>> {
    const response = await apiClient.post<Schema<'Precuration'>>(`/precurations/${id}/reject`, data)
    return response.data
  },

  /**
   * Delete precuration (soft delete)
   * @param id - Precuration UUID
   */
  async deletePrecuration(id: string): Promise<void> {
    await apiClient.delete(`/precurations/${id}`)
  },

  /**
   * Get precurations for a specific gene in a scope
   * @param geneId - Gene UUID
   * @param scopeId - Scope UUID
   */
  async getPrecurationsByGeneAndScope(
    geneId: string,
    scopeId: string
  ): Promise<Schema<'PrecurationListResponse'>> {
    const response = await apiClient.get<Schema<'PrecurationListResponse'>>('/precurations/', {
      params: { gene_id: geneId, scope_id: scopeId }
    })
    return response.data
  }
}
