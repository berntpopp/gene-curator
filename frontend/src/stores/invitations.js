/**
 * Invitations Pinia Store
 *
 * Manages state for user's pending scope invitations.
 * Follows the same patterns as other stores in the application.
 *
 * @see frontend/src/api/invitations.js
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { invitationsApi } from '@/api/invitations'
import { logService } from '@/services/logService'

export const useInvitationsStore = defineStore('invitations', () => {
  // ============================================
  // STATE
  // ============================================

  const invitations = ref([])
  const loading = ref(false)
  const error = ref(null)
  const lastFetched = ref(null)

  // ============================================
  // GETTERS
  // ============================================

  /**
   * Count of pending (non-expired) invitations
   */
  const pendingCount = computed(() => {
    return invitations.value.filter(inv => !inv.is_expired).length
  })

  /**
   * Only non-expired invitations
   */
  const pendingInvitations = computed(() => {
    return invitations.value.filter(inv => !inv.is_expired)
  })

  /**
   * Expired invitations
   */
  const expiredInvitations = computed(() => {
    return invitations.value.filter(inv => inv.is_expired)
  })

  /**
   * Check if we have pending invitations
   */
  const hasPendingInvitations = computed(() => {
    return pendingCount.value > 0
  })

  // ============================================
  // ACTIONS
  // ============================================

  /**
   * Fetch pending invitations for current user
   *
   * @param {Object} options
   * @param {boolean} [options.includeExpired=false] - Include expired invitations
   * @param {boolean} [options.force=false] - Force refresh even if recently fetched
   * @returns {Promise<Array>} Array of invitations
   */
  async function fetchPendingInvitations(options = {}) {
    // Skip if recently fetched (within 30 seconds) unless forced
    const now = Date.now()
    if (!options.force && lastFetched.value && now - lastFetched.value < 30000) {
      logService.debug('Skipping invitation fetch - recently fetched', {
        lastFetched: lastFetched.value
      })
      return invitations.value
    }

    loading.value = true
    error.value = null

    try {
      const response = await invitationsApi.getPendingInvitations({
        includeExpired: options.includeExpired || false
      })

      invitations.value = response.invitations || []
      lastFetched.value = now

      logService.debug('Fetched pending invitations', {
        count: invitations.value.length,
        pendingCount: pendingCount.value
      })

      return invitations.value
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch invitations'
      logService.error('Failed to fetch invitations', {
        error: err.message,
        stack: err.stack
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Accept an invitation
   *
   * @param {string} invitationId - Invitation UUID
   * @param {string} scopeId - Scope UUID (needed for API path)
   * @returns {Promise<Object>} Accepted membership
   */
  async function acceptInvitation(invitationId, scopeId) {
    loading.value = true
    error.value = null

    try {
      // Use scope memberships endpoint for accept
      const { default: apiClient } = await import('@/api/client.js')
      const response = await apiClient.post(`/scopes/${scopeId}/invitations/${invitationId}/accept`)

      // Remove from local state
      invitations.value = invitations.value.filter(inv => inv.id !== invitationId)

      logService.info('Accepted scope invitation', {
        invitationId,
        scopeId
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to accept invitation'
      logService.error('Failed to accept invitation', {
        invitationId,
        scopeId,
        error: err.message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Decline an invitation
   *
   * @param {string} invitationId - Invitation UUID
   * @returns {Promise<void>}
   */
  async function declineInvitation(invitationId) {
    loading.value = true
    error.value = null

    try {
      await invitationsApi.declineInvitation(invitationId)

      // Remove from local state
      invitations.value = invitations.value.filter(inv => inv.id !== invitationId)

      logService.info('Declined scope invitation', { invitationId })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to decline invitation'
      logService.error('Failed to decline invitation', {
        invitationId,
        error: err.message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear all invitations (for logout)
   */
  function clearInvitations() {
    invitations.value = []
    lastFetched.value = null
    error.value = null
  }

  /**
   * Reset store state
   */
  function $reset() {
    invitations.value = []
    loading.value = false
    error.value = null
    lastFetched.value = null
  }

  return {
    // State
    invitations,
    loading,
    error,
    lastFetched,

    // Getters
    pendingCount,
    pendingInvitations,
    expiredInvitations,
    hasPendingInvitations,

    // Actions
    fetchPendingInvitations,
    acceptInvitation,
    declineInvitation,
    clearInvitations,
    $reset
  }
})

export default useInvitationsStore
