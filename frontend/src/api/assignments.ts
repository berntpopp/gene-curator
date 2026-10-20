import apiClient from './client'
import type { Schema } from '@/types/api'

export const assignmentsAPI = {
  /**
   * Get all gene assignments
   */
  async getAssignments(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'GeneScopeAssignmentListResponse'>> {
    const response = await apiClient.get<Schema<'GeneScopeAssignmentListResponse'>>(
      '/gene-assignments',
      { params }
    )
    return response.data
  },

  /**
   * Create a single gene assignment
   */
  async createAssignment(
    assignmentData: Schema<'GeneScopeAssignmentCreate'>
  ): Promise<Schema<'GeneScopeAssignment'>> {
    const response = await apiClient.post<Schema<'GeneScopeAssignment'>>(
      '/gene-assignments',
      assignmentData
    )
    return response.data
  },

  /**
   * Bulk assign genes to scope
   */
  async bulkAssignGenes(
    assignmentData: Schema<'BulkGeneScopeAssignmentCreate'>
  ): Promise<Schema<'BulkGeneScopeAssignmentResponse'>> {
    const response = await apiClient.post<Schema<'BulkGeneScopeAssignmentResponse'>>(
      '/gene-assignments/bulk',
      assignmentData
    )
    return response.data
  },

  /**
   * Get curator workload
   */
  async getCuratorWorkload(curatorId: string): Promise<Schema<'CuratorWorkload'>> {
    const response = await apiClient.get<Schema<'CuratorWorkload'>>(
      `/gene-assignments/curator/${curatorId}/workload`
    )
    return response.data
  },

  /**
   * Get curator assignments
   */
  async getCuratorAssignments(
    curatorId: string,
    params: Record<string, unknown> = {}
  ): Promise<Schema<'GeneScopeAssignmentSummary'>[]> {
    const response = await apiClient.get<Schema<'GeneScopeAssignmentSummary'>[]>(
      `/gene-assignments/curator/${curatorId}/assignments`,
      { params }
    )
    return response.data
  },

  /**
   * Update assignment priority
   */
  async updateAssignmentPriority(assignmentId: string, priority: string): Promise<unknown> {
    const response = await apiClient.put<unknown>(`/gene-assignments/${assignmentId}/priority`, {
      priority_level: priority
    })
    return response.data
  },

  /**
   * Update gene assignment (curator, priority, notes, etc.)
   */
  async updateAssignment(
    assignmentId: string,
    updateData: Schema<'GeneScopeAssignmentUpdate'>
  ): Promise<Schema<'GeneScopeAssignment'>> {
    const response = await apiClient.put<Schema<'GeneScopeAssignment'>>(
      `/gene-assignments/${assignmentId}`,
      updateData
    )
    return response.data
  },

  /**
   * Assign a curator to a gene-scope assignment
   */
  async assignCurator(assignmentId: string, curatorId: string): Promise<unknown> {
    const response = await apiClient.post<unknown>(
      `/gene-assignments/${assignmentId}/assign-curator`,
      { curator_id: curatorId }
    )
    return response.data
  },

  /**
   * Remove a gene assignment from scope (deactivate)
   * @param assignmentId - Assignment UUID
   * @param reason - Reason for removal
   */
  async removeAssignment(assignmentId: string, reason = 'Removed from scope'): Promise<unknown> {
    const response = await apiClient.delete<unknown>(`/gene-assignments/${assignmentId}`, {
      data: { reason }
    })
    return response.data
  },

  /**
   * Get assignments by scope
   */
  async getAssignmentsByScope(
    scopeId: string,
    params: Record<string, unknown> = {}
  ): Promise<Schema<'GeneScopeAssignmentSummary'>[]> {
    const response = await apiClient.get<Schema<'GeneScopeAssignmentSummary'>[]>(
      `/gene-assignments/scope/${scopeId}`,
      { params }
    )
    return response.data
  },

  /**
   * Get available genes for scope assignment
   */
  async getAvailableGenesForScope(scopeId: string): Promise<Schema<'AvailableGene'>[]> {
    const response = await apiClient.get<Schema<'AvailableGene'>[]>(
      `/gene-assignments/scope/${scopeId}/available-genes`
    )
    return response.data
  },

  /**
   * Get scope assignment overview
   */
  async getScopeAssignmentOverview(scopeId: string): Promise<Schema<'ScopeAssignmentOverview'>> {
    const response = await apiClient.get<Schema<'ScopeAssignmentOverview'>>(
      `/gene-assignments/scope/${scopeId}/overview`
    )
    return response.data
  }
}
