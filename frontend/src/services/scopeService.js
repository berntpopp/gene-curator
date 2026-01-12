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

import apiClient from '@/api/client.js'

export const scopeService = {
  /**
   * Fetch all scopes visible to current user
   *
   * @param {Object} params - Query parameters
   * @param {number} [params.limit] - Max results to return
   * @param {number} [params.offset] - Results offset for pagination
   * @param {boolean} [params.is_public] - Filter by public/private
   * @returns {Promise<Array>} Array of scope objects
   *
   * @example
   * const scopes = await scopeService.fetchScopes({ limit: 50 })
   */
  async fetchScopes(params = {}) {
    const response = await apiClient.get('/scopes/', { params })
    // Handle different response formats (array or object with scopes array)
    return response.data.scopes || response.data
  },

  /**
   * Fetch single scope by ID
   *
   * @param {string} scopeId - Scope UUID
   * @returns {Promise<Object>} Scope object
   *
   * @example
   * const scope = await scopeService.fetchScope('uuid-here')
   */
  async fetchScope(scopeId) {
    const response = await apiClient.get(`/scopes/${scopeId}`)
    return response.data
  },

  /**
   * Create new scope
   *
   * @param {Object} scopeData - Scope creation data
   * @param {string} scopeData.name - Machine-readable name (lowercase-with-dashes)
   * @param {string} scopeData.display_name - Human-readable display name
   * @param {string} [scopeData.description] - Scope description
   * @param {string} [scopeData.institution] - Institution name
   * @param {boolean} [scopeData.is_public] - Whether scope is public
   * @param {string} [scopeData.due_date] - Due date (ISO format)
   * @returns {Promise<Object>} Created scope object
   *
   * @example
   * const scope = await scopeService.createScope({
   *   name: 'kidney-genetics',
   *   display_name: 'Kidney Genetics',
   *   description: 'Kidney disease gene curation',
   *   is_public: false
   * })
   */
  async createScope(scopeData) {
    const response = await apiClient.post('/scopes/', scopeData)
    return response.data
  },

  /**
   * Update existing scope
   *
   * @param {string} scopeId - Scope UUID
   * @param {Object} scopeData - Updated scope data (partial update supported)
   * @returns {Promise<Object>} Updated scope object
   *
   * @example
   * const updated = await scopeService.updateScope(scopeId, {
   *   display_name: 'New Display Name',
   *   is_public: true
   * })
   */
  async updateScope(scopeId, scopeData) {
    const response = await apiClient.patch(`/scopes/${scopeId}`, scopeData)
    return response.data
  },

  /**
   * Delete scope
   *
   * @param {string} scopeId - Scope UUID
   * @returns {Promise<void>}
   *
   * @example
   * await scopeService.deleteScope(scopeId)
   */
  async deleteScope(scopeId) {
    await apiClient.delete(`/scopes/${scopeId}`)
  },

  /**
   * Fetch scope statistics
   *
   * @param {string} scopeId - Scope UUID
   * @returns {Promise<Object>} Scope statistics
   *
   * @example
   * const stats = await scopeService.fetchStatistics(scopeId)
   * // { total_genes: 100, completed_genes: 75, ... }
   */
  async fetchStatistics(scopeId) {
    const response = await apiClient.get(`/scopes/${scopeId}/statistics`)
    return response.data
  },

  /**
   * Fetch scope members
   *
   * @param {string} scopeId - Scope UUID
   * @returns {Promise<Array>} Array of membership objects
   *
   * @example
   * const members = await scopeService.fetchMembers(scopeId)
   * // [{ user_id: 'uuid', role: 'admin', ... }, ...]
   */
  async fetchMembers(scopeId) {
    const response = await apiClient.get(`/scopes/${scopeId}/members`)
    // Extract members array from response
    // API returns: { scope_id, total, members, active_count, pending_count, role_counts }
    return response.data.members || response.data
  },

  /**
   * Invite user to scope
   *
   * @param {string} scopeId - Scope UUID
   * @param {Object} invitationData - Invitation details
   * @param {string} [invitationData.email] - Email of user to invite (for new users)
   * @param {string} [invitationData.user_id] - User ID (for existing users)
   * @param {string} invitationData.role - Scope role (admin, curator, reviewer, viewer)
   * @returns {Promise<Object>} Invitation result
   *
   * @example
   * const result = await scopeService.inviteMember(scopeId, {
   *   email: 'newuser@example.com',
   *   role: 'curator'
   * })
   */
  async inviteMember(scopeId, invitationData) {
    const response = await apiClient.post(`/scopes/${scopeId}/invitations`, invitationData)
    return response.data
  },

  /**
   * Update member role within scope
   *
   * @param {string} scopeId - Scope UUID
   * @param {string} userId - User UUID
   * @param {string} newRole - New role (admin, curator, reviewer, viewer)
   * @returns {Promise<Object>} Updated membership object
   *
   * @example
   * await scopeService.updateMemberRole(scopeId, userId, 'reviewer')
   */
  async updateMemberRole(scopeId, userId, newRole) {
    const response = await apiClient.patch(`/scopes/${scopeId}/members/${userId}`, {
      role: newRole
    })
    return response.data
  },

  /**
   * Remove member from scope
   *
   * @param {string} scopeId - Scope UUID
   * @param {string} userId - User UUID
   * @returns {Promise<void>}
   *
   * @example
   * await scopeService.removeMember(scopeId, userId)
   */
  async removeMember(scopeId, userId) {
    await apiClient.delete(`/scopes/${scopeId}/members/${userId}`)
  },

  /**
   * Fetch user's role in scope
   *
   * @param {string} scopeId - Scope UUID
   * @param {string} userId - User UUID
   * @returns {Promise<Object|null>} Membership object or null
   *
   * @example
   * const membership = await scopeService.fetchUserRole(scopeId, userId)
   * // { role: 'admin', is_active: true, ... }
   */
  async fetchUserRole(scopeId, userId) {
    try {
      const members = await this.fetchMembers(scopeId)
      return members.find(m => m.user_id === userId) || null
    } catch (error) {
      // If not a member or no access, return null
      if (error.response?.status === 403 || error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  /**
   * Fetch scopes where user is a member
   *
   * @param {string} userId - User UUID
   * @returns {Promise<Array>} Array of scope objects
   *
   * @example
   * const userScopes = await scopeService.fetchUserScopes(userId)
   */
  async fetchUserScopes(userId) {
    const response = await apiClient.get(`/users/${userId}/scopes`)
    return response.data
  },

  /**
   * Accept scope invitation
   *
   * @param {string} invitationId - Invitation UUID
   * @returns {Promise<Object>} Accepted membership object
   *
   * @example
   * await scopeService.acceptInvitation(invitationId)
   */
  async acceptInvitation(invitationId) {
    const response = await apiClient.post(`/invitations/${invitationId}/accept`)
    return response.data
  },

  /**
   * Decline scope invitation
   *
   * @param {string} invitationId - Invitation UUID
   * @returns {Promise<void>}
   *
   * @example
   * await scopeService.declineInvitation(invitationId)
   */
  async declineInvitation(invitationId) {
    await apiClient.post(`/invitations/${invitationId}/decline`)
  }
}

export default scopeService
