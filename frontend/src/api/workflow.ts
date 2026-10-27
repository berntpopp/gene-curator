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

  /** Dry-run a transition: roles, 4-eyes and the pinned required-content check (#453). */
  async validateTransition(
    itemType: string,
    itemId: string,
    targetStage: Schema<'WorkflowTransitionRequest'>['target_stage']
  ): Promise<Schema<'WorkflowValidationResult'>> {
    const response = await apiClient.post<Schema<'WorkflowValidationResult'>>(
      `/workflow/${itemType}/${itemId}/validate-transition`,
      { target_stage: targetStage }
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
   * Submit a peer review decision (POST /workflow/reviews/{review_id}/submit)
   * @param reviewId - Peer review request UUID
   */
  async submitPeerReview(
    reviewId: string,
    reviewData: Schema<'PeerReviewSubmission'>
  ): Promise<Schema<'PeerReviewResult'>> {
    const response = await apiClient.post<Schema<'PeerReviewResult'>>(
      `/workflow/reviews/${reviewId}/submit`,
      reviewData
    )
    return response.data
  },

  /**
   * Transition any workflow item (precuration or curation) to another stage
   */
  async transitionItem(
    itemType: string,
    itemId: string,
    transitionData: Schema<'WorkflowTransitionRequest'>
  ): Promise<Schema<'WorkflowTransition'>> {
    const response = await apiClient.post<Schema<'WorkflowTransition'>>(
      `/workflow/${itemType}/${itemId}/transition`,
      transitionData
    )
    return response.data
  },

  /**
   * Get the stage-transition audit trail of any workflow item
   */
  async getWorkflowAuditTrail(
    itemType: string,
    itemId: string
  ): Promise<Schema<'WorkflowAuditTrail'>> {
    const response = await apiClient.get<Schema<'WorkflowAuditTrail'>>(
      `/workflow/${itemType}/${itemId}/audit-trail`
    )
    return response.data
  },

  /**
   * Get curation workflow history
   */
  async getCurationWorkflowHistory(curationId: string): Promise<Schema<'WorkflowAuditTrail'>> {
    const response = await apiClient.get<Schema<'WorkflowAuditTrail'>>(
      `/workflow/curation/${curationId}/audit-trail`
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
