/**
 * Session Timeout composable - detects and warns about JWT expiration
 *
 * Monitors JWT token expiration and shows warning before timeout.
 * Prevents silent logouts and data loss from expired sessions.
 *
 * Design principles:
 * - KISS: Simple timer-based checking
 * - User-centric: 5-minute warning before expiration
 * - Proactive: Allows session extension without interruption
 *
 * @example
 * const { showWarning, timeRemaining, extendSession } = useSessionTimeout()
 *
 * // In template:
 * <session-timeout-warning
 *   v-model="showWarning"
 *   :time-remaining="timeRemaining"
 *   @extend="extendSession"
 * />
 */

import { ref, onMounted, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getTokenExpiry } from '@/utils/jwt'
import { useLogger } from './useLogger'

export interface UseSessionTimeoutReturn {
  showWarning: Ref<boolean>
  timeRemaining: Ref<number>
  extendSession: () => Promise<void>
  dismissWarning: () => void
  checkTokenExpiry: () => void
}

export function useSessionTimeout(): UseSessionTimeoutReturn {
  const authStore = useAuthStore()
  const logger = useLogger()

  const showWarning = ref(false)
  const timeRemaining = ref(0) // seconds
  const warningThreshold = 5 * 60 * 1000 // 5 minutes in milliseconds

  let checkInterval: ReturnType<typeof setInterval> | null = null

  /**
   * Check token expiration and update state
   * Runs every minute to check token status
   */
  function checkTokenExpiry(): void {
    // Skip if not authenticated
    const expiresAt = authStore.token ? getTokenExpiry(authStore.token) : null
    if (expiresAt === null) {
      return
    }

    const remaining = expiresAt - Date.now()

    // Update time remaining (in seconds)
    timeRemaining.value = Math.max(0, Math.floor(remaining / 1000))

    // Show warning if within threshold
    if (remaining < warningThreshold && remaining > 0) {
      if (!showWarning.value) {
        showWarning.value = true
        logger.warn('Session expiring soon', {
          remaining: timeRemaining.value,
          expiresAt: new Date(expiresAt).toISOString()
        })
      }
    }

    // Token expired - logout
    else if (remaining <= 0) {
      if (showWarning.value) {
        showWarning.value = false
      }

      logger.error('Session expired', {
        expiresAt: new Date(expiresAt).toISOString()
      })

      // Trigger logout (will redirect to login page)
      authStore.logout()
    }

    // Token valid and not near expiration
    else if (showWarning.value && remaining >= warningThreshold) {
      // Hide warning if session was extended
      showWarning.value = false
      logger.info('Session warning dismissed', {
        remaining: timeRemaining.value
      })
    }
  }

  /**
   * Extend session by refreshing JWT token
   * Called when user clicks "Extend Session" button
   */
  async function extendSession(): Promise<void> {
    try {
      logger.info('Attempting to extend session')
      const newToken = await authStore.refreshAccessToken()
      const newExpiry = getTokenExpiry(newToken)

      showWarning.value = false
      timeRemaining.value = 0

      logger.info('Session extended successfully', {
        newExpiresAt: newExpiry ? new Date(newExpiry).toISOString() : 'unknown'
      })
    } catch (error) {
      logger.error('Failed to extend session', {
        error: error instanceof Error ? error.message : undefined
      })

      // Show error to user (they'll need to re-login)
      throw error
    }
  }

  /**
   * Dismiss warning without extending session
   * User can continue working but will be logged out at expiration
   */
  function dismissWarning(): void {
    showWarning.value = false
    logger.debug('Session timeout warning dismissed')
  }

  /**
   * Setup interval on mount
   */
  onMounted(() => {
    // Check immediately
    checkTokenExpiry()

    // Then check every minute
    checkInterval = setInterval(checkTokenExpiry, 60000)

    logger.debug('Session timeout monitoring started', {
      checkInterval: 60000
    })
  })

  /**
   * Cleanup on unmount
   */
  onBeforeUnmount(() => {
    if (checkInterval) {
      clearInterval(checkInterval)
      checkInterval = null
      logger.debug('Session timeout monitoring stopped')
    }
  })

  return {
    // State
    showWarning,
    timeRemaining,

    // Methods
    extendSession,
    dismissWarning,
    checkTokenExpiry // Export for manual checking if needed
  }
}
