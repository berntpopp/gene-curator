/**
 * Invitations API client for user-facing invitation endpoints.
 *
 * Provides methods for fetching, accepting, and declining scope invitations.
 * These are the endpoints available to any authenticated user for managing
 * their own pending invitations.
 *
 * @see backend/app/api/v1/endpoints/invitations.py
 */
import apiClient from '@/api/client'
import type { Schema } from '@/types/api'

export const invitationsApi = {
  /**
   * Get current user's pending invitations
   *
   * @param options - Query options
   * @param options.includeExpired - Include expired invitations (default false)
   * @returns Invitations list with total count
   * @example
   * const { invitations, total } = await invitationsApi.getPendingInvitations()
   */
  async getPendingInvitations(
    options: { includeExpired?: boolean } = {}
  ): Promise<Schema<'PendingInvitationsListResponse'>> {
    const params: Record<string, boolean> = {}
    if (options.includeExpired) {
      params.include_expired = true
    }
    const response = await apiClient.get<Schema<'PendingInvitationsListResponse'>>(
      '/me/invitations',
      { params }
    )
    return response.data
  },

  /**
   * Accept a scope invitation (POST /scopes/{scope_id}/invitations/{membership_id}/accept)
   *
   * @param scopeId - Scope UUID the invitation belongs to
   * @param membershipId - Invitation (membership) UUID
   * @returns Accepted membership
   */
  async acceptInvitation(
    scopeId: string,
    membershipId: string
  ): Promise<Schema<'ScopeMembershipResponse'>> {
    const response = await apiClient.post<Schema<'ScopeMembershipResponse'>>(
      `/scopes/${scopeId}/invitations/${membershipId}/accept`
    )
    return response.data
  },

  /**
   * Decline a scope invitation
   *
   * @param invitationId - Invitation UUID
   *
   * @example
   * await invitationsApi.declineInvitation('uuid-here')
   */
  async declineInvitation(invitationId: string): Promise<void> {
    await apiClient.post(`/invitations/${invitationId}/decline`)
  }
}

export default invitationsApi
