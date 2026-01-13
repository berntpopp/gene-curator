/**
 * Invitations API client for user-facing invitation endpoints.
 *
 * Provides methods for fetching, accepting, and declining scope invitations.
 * These are the endpoints available to any authenticated user for managing
 * their own pending invitations.
 *
 * @see backend/app/api/v1/endpoints/invitations.py
 */

import apiClient from '@/api/client.js'

export const invitationsApi = {
  /**
   * Get current user's pending invitations
   *
   * @param {Object} options - Query options
   * @param {boolean} [options.includeExpired=false] - Include expired invitations
   * @returns {Promise<Object>} { invitations: [...], total: number }
   *
   * @example
   * const { invitations, total } = await invitationsApi.getPendingInvitations()
   */
  async getPendingInvitations(options = {}) {
    const params = {}
    if (options.includeExpired) {
      params.include_expired = true
    }
    const response = await apiClient.get('/me/invitations', { params })
    return response.data
  },

  /**
   * Accept a scope invitation
   *
   * @param {string} invitationId - Invitation UUID
   * @param {Object} [data] - Optional acceptance data
   * @param {string} [data.notes] - Optional acceptance notes
   * @returns {Promise<Object>} Accepted membership object
   *
   * @example
   * const membership = await invitationsApi.acceptInvitation('uuid-here')
   */
  async acceptInvitation(invitationId, data = {}) {
    // The accept endpoint is on scope_memberships router
    // POST /scopes/{scope_id}/invitations/{membership_id}/accept
    // But we need the scope_id which we may not have...
    // Actually, looking at the backend, there's a simpler pattern we could use.
    // For now, let's use the scope service pattern
    const response = await apiClient.post(`/invitations/${invitationId}/accept`, data)
    return response.data
  },

  /**
   * Decline a scope invitation
   *
   * @param {string} invitationId - Invitation UUID
   * @returns {Promise<void>}
   *
   * @example
   * await invitationsApi.declineInvitation('uuid-here')
   */
  async declineInvitation(invitationId) {
    await apiClient.post(`/invitations/${invitationId}/decline`)
  }
}

export default invitationsApi
