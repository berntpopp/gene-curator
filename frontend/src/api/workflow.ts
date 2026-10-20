import apiClient from './client'
import type { Schema } from '@/types/api'

export const workflowAPI = {
  /**
   * Get workflow analytics
   */
  async getWorkflowAnalytics(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'WorkflowAnalytics'>> {
    const response = await apiClient.get<Schema<'WorkflowAnalytics'>>('/workflow/analytics', {
      params
    })
    return response.data
  },

  /**
   * Transition curation to next workflow stage
   */
  async transitionCuration(
    curationId: string,
    transitionData: Schema<'WorkflowTransitionRequest'>
  ): Promise<Schema<'WorkflowTransition'>> {
    const response = await apiClient.post<Schema<'WorkflowTransition'>>(
      `/workflow/curation/${curationId}/transition`,
      transitionData
    )
    return response.data
  },

  /**
   * Get workflow state for an item
   * @param itemType - Item type (curation, precuration)
   * @param itemId - Item UUID
   */
  async getWorkflowState(itemType: string, itemId: string): Promise<Schema<'WorkflowStateInfo'>> {
    const response = await apiClient.get<Schema<'WorkflowStateInfo'>>(
      `/workflow/${itemType}/${itemId}/state`
    )
    return response.data
  },

  /**
   * Get available transitions for curation
   * Uses workflow state endpoint which returns available_transitions in response
   */
  async getAvailableTransitions(
    curationId: string
  ): Promise<Schema<'WorkflowStateInfo'>['available_transitions']> {
    const response = await apiClient.get<Schema<'WorkflowStateInfo'>>(
      `/workflow/curation/${curationId}/state`
    )
    return response.data?.available_transitions || []
  },

  /**
   * Get peer reviewers for workflow stage
   */
  async getPeerReviewers(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'PeerReviewerResponse'>[]> {
    const response = await apiClient.get<Schema<'PeerReviewerResponse'>[]>(
      '/workflow/peer-reviewers',
      { params }
    )
    return response.data
  },

  /**
   * Submit peer review
   * Uses transition endpoint — the dedicated review endpoint does not exist
   * CurationDetailView already uses transitionCuration() directly for approve/reject
   */
  async submitPeerReview(
    curationId: string,
    reviewData: Schema<'WorkflowTransitionRequest'>
  ): Promise<Schema<'WorkflowTransition'>> {
    const response = await apiClient.post<Schema<'WorkflowTransition'>>(
      `/workflow/curation/${curationId}/transition`,
      reviewData
    )
    return response.data
  },

  /**
   * Get curation workflow history
   */
  async getCurationWorkflowHistory(curationId: string): Promise<Schema<'WorkflowAuditTrail'>> {
    const response = await apiClient.get<Schema<'WorkflowAuditTrail'>>(
      `/workflow/curation/${curationId}/history`
    )
    return response.data
  },

  /**
   * Get workflow statistics by stage
   */
  async getWorkflowStatistics(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'WorkflowStatistics'>> {
    const response = await apiClient.get<Schema<'WorkflowStatistics'>>('/workflow/statistics', {
      params
    })
    return response.data
  }
}
