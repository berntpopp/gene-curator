/**
 * Scope API Service
 *
 * **SOLID - Single Responsibility Principle (SRP)**
 * This service handles ONLY network operations for scopes.
 * State management is delegated to the Pinia store.
 *
 * **Separation of Concerns**:
 * - Service Layer: Network calls, HTTP logic, error handling
 * - Store Layer: State management, caching, business logic
 * - Component Layer: UI rendering, user interactions
 *
 * **Benefits**:
 * - DRY: Reusable across multiple stores/components
 * - Testable: Easy to mock for testing
 * - Maintainable: Changes to API don't affect store logic
 * - Type-safe: Centralized request/response handling
 *
 * @example
 * ```javascript
 * // In Pinia store
 * import { scopeService } from '@/services/scopeService'
 *
 * async function fetchScopes() {
 *   const data = await scopeService.fetchScopes({ limit: 50 })
 *   scopes.value = data
 * }
 * ```
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-21-create-separate-api-service-layer
 */

import apiClient from '@/api/client'
import type { Schema } from '@/types/api'

type ScopeMember = Schema<'ScopeMemberListResponse'>['members'][number]
type ScopeListItem = Schema<'ScopeListItem'>

export interface MemberListOptions {
  includePending?: boolean
}

export const scopeService = {
  /**
   * Fetch all scopes visible to current user
   *
   * @param params - Query parameters
   * @param [params.limit] - Max results to return
   * @param [params.offset] - Results offset for pagination
   * @param [params.is_public] - Filter by public/private
   * @returns Array of scope objects
   *
   * @example
   * const scopes = await scopeService.fetchScopes({ limit: 50 })
   */
  async fetchScopes(params: Record<string, unknown> = {}): Promise<ScopeListItem[]> {
    const response = await apiClient.get<ScopeListItem[]>('/scopes/', { params })
    return response.data
  },

  /**
   * Fetch single scope by ID
   *
   * @param scopeId - Scope UUID
   * @returns Scope object
   *
   * @example
   * const scope = await scopeService.fetchScope('uuid-here')
   */
  async fetchScope(scopeId: string): Promise<Schema<'ScopeWithStats'>> {
    const response = await apiClient.get<Schema<'ScopeWithStats'>>(`/scopes/${scopeId}`)
    return response.data
  },

  /**
   * Create new scope
   *
   * @param scopeData - Scope creation data
   * @param scopeData.name - Machine-readable name (lowercase-with-dashes)
   * @param scopeData.display_name - Human-readable display name
   * @param [scopeData.description] - Scope description
   * @param [scopeData.institution] - Institution name
   * @param [scopeData.is_public] - Whether scope is public
   * @param [scopeData.due_date] - Due date (ISO format)
   * @returns Created scope object
   *
   * @example
   * const scope = await scopeService.createScope({
   *   name: 'kidney-genetics',
   *   display_name: 'Kidney Genetics',
   *   description: 'Kidney disease gene curation',
   *   is_public: false
   * })
   */
  async createScope(scopeData: Schema<'ScopeCreate'>): Promise<Schema<'Scope'>> {
    const response = await apiClient.post<Schema<'Scope'>>('/scopes/', scopeData)
    return response.data
  },

  /**
   * Update existing scope
   *
   * @param scopeId - Scope UUID
   * @param scopeData - Updated scope data (partial update supported)
   * @returns Updated scope object
   *
   * @example
   * const updated = await scopeService.updateScope(scopeId, {
   *   display_name: 'New Display Name',
   *   is_public: true
   * })
   */
  async updateScope(scopeId: string, scopeData: Schema<'ScopeUpdate'>): Promise<Schema<'Scope'>> {
    const response = await apiClient.patch<Schema<'Scope'>>(`/scopes/${scopeId}`, scopeData)
    return response.data
  },

  /**
   * Delete scope
   *
   * @param scopeId - Scope UUID
   * @example
   * await scopeService.deleteScope(scopeId)
   */
  async deleteScope(scopeId: string): Promise<void> {
    await apiClient.delete(`/scopes/${scopeId}`)
  },

  /**
   * Fetch scope statistics
   *
   * @param scopeId - Scope UUID
   * @returns Scope statistics
   *
   * @example
   * const stats = await scopeService.fetchStatistics(scopeId)
   * // { total_genes: 100, completed_genes: 75, ... }
   */
  async fetchStatistics(scopeId: string): Promise<Schema<'ScopeStatistics'>> {
    const response = await apiClient.get<Schema<'ScopeStatistics'>>(`/scopes/${scopeId}/statistics`)
    return response.data
  },

  /**
   * Fetch scope members
   *
   * @param scopeId - Scope UUID
   * @param options - Query options
   * @param [options.includePending=false] - Include pending invitations
   * @returns Member list response with statistics
   *
   * @example
   * const result = await scopeService.fetchMembers(scopeId, { includePending: true })
   * // { members: [...], total, active_count, pending_count, role_counts }
   */
  async fetchMembers(scopeId: string, options: MemberListOptions = {}): Promise<ScopeMember[]> {
    const params: Record<string, boolean> = {}
    if (options.includePending) {
      params.include_pending = true
    }
    const response = await apiClient.get<Schema<'ScopeMemberListResponse'>>(
      `/scopes/${scopeId}/members`,
      { params }
    )
    return response.data.members
  },

  /**
   * Fetch scope members with full statistics
   *
   * @param scopeId - Scope UUID
   * @param includePending - Include pending invitations
   * @returns Full member list response with statistics
   *
   * @example
   * const data = await scopeService.fetchMembersWithStats(scopeId, true)
   * // { scope_id, total, members, active_count, pending_count, role_counts }
   */
  async fetchMembersWithStats(
    scopeId: string,
    includePending = false
  ): Promise<Schema<'ScopeMemberListResponse'>> {
    const params = includePending ? { include_pending: true } : {}
    const response = await apiClient.get<Schema<'ScopeMemberListResponse'>>(
      `/scopes/${scopeId}/members`,
      { params }
    )
    return response.data
  },

  /**
   * Search users for invitation (scope admin only)
   *
   * Returns users who are NOT already members of the scope.
   *
   * @param scopeId - Scope UUID
   * @param query - Search query (name, email, or institution)
   * @param [limit=10] - Maximum results
   * @returns Array of user objects matching query
   *
   * @example
   * const users = await scopeService.searchUsersForInvite(scopeId, 'john')
   * // [{ id: 'uuid', name: 'John Doe', email: 'john@example.com', ... }, ...]
   */
  async searchUsersForInvite(
    scopeId: string,
    query: string,
    limit = 10
  ): Promise<Schema<'UserResponse'>[]> {
    const response = await apiClient.get<Schema<'UserResponse'>[]>(
      `/scopes/${scopeId}/users/search`,
      {
        params: { q: query, limit }
      }
    )
    return response.data
  },

  /**
   * Invite user to scope
   *
   * @param scopeId - Scope UUID
   * @param invitationData - Invitation details
   * @param [invitationData.email] - Email of user to invite (for new users)
   * @param [invitationData.user_id] - User ID (for existing users)
   * @param invitationData.role - Scope role (admin, curator, reviewer, viewer)
   * @returns Invitation result
   *
   * @example
   * const result = await scopeService.inviteMember(scopeId, {
   *   email: 'newuser@example.com',
   *   role: 'curator'
   * })
   */
  async inviteMember(
    scopeId: string,
    invitationData: Schema<'ScopeMembershipCreate'>
  ): Promise<Schema<'ScopeMembershipResponse'>> {
    const response = await apiClient.post<Schema<'ScopeMembershipResponse'>>(
      `/scopes/${scopeId}/invitations`,
      invitationData
    )
    return response.data
  },

  /**
   * Update member role within scope
   *
   * @param scopeId - Scope UUID
   * @param userId - User UUID
   * @param newRole - New role (admin, curator, reviewer, viewer)
   * @returns Updated membership object
   *
   * @example
   * await scopeService.updateMemberRole(scopeId, userId, 'reviewer')
   */
  async updateMemberRole(
    scopeId: string,
    userId: string,
    newRole: Schema<'ScopeRole'>
  ): Promise<Schema<'ScopeMembershipResponse'>> {
    const response = await apiClient.patch<Schema<'ScopeMembershipResponse'>>(
      `/scopes/${scopeId}/members/${userId}`,
      { role: newRole }
    )
    return response.data
  },

  /**
   * Remove member from scope
   *
   * @param scopeId - Scope UUID
   * @param userId - User UUID
   * @example
   * await scopeService.removeMember(scopeId, userId)
   */
  async removeMember(scopeId: string, userId: string): Promise<void> {
    await apiClient.delete(`/scopes/${scopeId}/members/${userId}`)
  },

  /**
   * Fetch user's role in scope
   *
   * @param scopeId - Scope UUID
   * @param userId - User UUID
   * @returns Membership object or null
   *
   * @example
   * const membership = await scopeService.fetchUserRole(scopeId, userId)
   * // { role: 'admin', is_active: true, ... }
   */
  async fetchUserRole(scopeId: string, userId: string): Promise<ScopeMember | null> {
    try {
      const members = await this.fetchMembers(scopeId)
      return members.find(m => m.user_id === userId) || null
    } catch (error) {
      // If not a member or no access, return null
      if (isHttpStatus(error, 403) || isHttpStatus(error, 404)) {
        return null
      }
      throw error
    }
  },

  /**
   * Decline scope invitation
   *
   * @param invitationId - Invitation UUID
   * @example
   * await scopeService.declineInvitation(invitationId)
   */
  async declineInvitation(invitationId: string): Promise<void> {
    await apiClient.post(`/invitations/${invitationId}/decline`)
  }
}

/** True when an axios-style error carries the given HTTP status */
function isHttpStatus(error: unknown, status: number): boolean {
  return (error as { response?: { status?: number } } | null)?.response?.status === status
}

export default scopeService
