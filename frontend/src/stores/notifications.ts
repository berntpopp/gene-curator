/**
 * Notifications Store
 *
 * Manages notification state, badge counts, and read/unread tracking.
 * Provides reactive notification data for the notification badge and dashboard.
 *
 * Features:
 * - Unread count tracking
 * - Mark as read functionality
 * - 60-second polling for new notifications
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#notification-system
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationsAPI } from '@/api/notifications'
import { logService } from '@/services/logService'
import { showSnackbar } from '@/composables/useNotifications'
import { errorMessage, toApiError } from './apiError'
import type { Schema } from '@/types/api'

const POLL_INTERVAL_MS = 60000

export type Notification = Schema<'NotificationResponse'>

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export const useNotificationsStore = defineStore('notifications', () => {
  // ========================================
  // State
  // ========================================

  const notifications = ref<Notification[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  // ========================================
  // Getters (Computed)
  // ========================================

  /**
   * Unread notifications only
   */
  const unreadNotifications = computed(() => notifications.value.filter(n => !n.is_read))

  /**
   * Total unread count (drives badge)
   */
  const totalUnread = computed(() => unreadNotifications.value.length)

  /**
   * Pending reviews count (for reviewers)
   */
  const pendingReviews = computed(
    () => unreadNotifications.value.filter(n => n.type === 'review_assigned').length
  )

  // ========================================
  // Actions
  // ========================================

  /**
   * Fetch notifications from API
   * @returns {Promise<void>}
   */
  const fetchNotifications = async (): Promise<void> => {
    loading.value = true
    error.value = null

    try {
      const response = await notificationsAPI.getNotifications({ limit: 50 })

      notifications.value = response.notifications

      logService.debug('Fetched notifications', {
        count: notifications.value.length,
        unread: totalUnread.value
      })
    } catch (err) {
      error.value = errorMessage(err, 'Failed to fetch notifications')
      logService.error('Failed to fetch notifications', {
        error: toApiError(err).message
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Mark a notification as read
   * @param {string} notificationId - Notification UUID
   * @returns {Promise<void>}
   */
  const markAsRead = async (notificationId: string): Promise<void> => {
    try {
      await notificationsAPI.markAsRead(notificationId)

      // Update local state
      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.is_read = true
        logService.debug('Marked notification as read', { notificationId })
      }
    } catch (err) {
      error.value = errorMessage(err, 'Failed to mark notification as read')
      logService.error('Failed to mark notification as read', {
        notificationId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  /**
   * Mark all notifications as read
   * @returns {Promise<void>}
   */
  const markAllAsRead = async (): Promise<void> => {
    try {
      await notificationsAPI.markAllAsRead()

      // Update local state
      notifications.value.forEach(n => {
        n.is_read = true
      })

      logService.info('Marked all notifications as read', {
        count: notifications.value.length
      })
    } catch (err) {
      error.value = errorMessage(err, 'Failed to mark all notifications as read')
      logService.error('Failed to mark all notifications as read', {
        error: toApiError(err).message
      })
      throw err
    }
  }

  /**
   * Add a notification (for real-time updates)
   * @param {Object} notification - Notification object
   */
  const addNotification = (notification: Notification): void => {
    notifications.value.unshift(notification)
    logService.debug('Added notification', { notification })
  }

  /**
   * Remove a notification
   * @param {string} notificationId - Notification UUID
   */
  const removeNotification = (notificationId: string): void => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index !== -1) {
      notifications.value.splice(index, 1)
      logService.debug('Removed notification', { notificationId })
    }
  }

  /**
   * Clear all notifications
   */
  const clearAll = (): void => {
    notifications.value = []
    error.value = null
    logService.info('Cleared all notifications')
  }

  /**
   * Clear error state
   */
  const clearError = (): void => {
    error.value = null
  }

  // ========================================
  // Polling
  // ========================================

  /**
   * Start polling for new notifications every 60 seconds
   */
  const startPolling = (): void => {
    stopPolling()
    fetchNotifications()
    pollTimer = setInterval(fetchNotifications, POLL_INTERVAL_MS)
    logService.debug('Notification polling started', { intervalMs: POLL_INTERVAL_MS })
  }

  /**
   * Stop polling for notifications
   */
  const stopPolling = (): void => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      logService.debug('Notification polling stopped')
    }
  }

  // ========================================
  // Toast Notifications
  // ========================================

  /** Show a toast via the shared snackbar rendered by App.vue (one slot: a new toast replaces the old). */
  const addToast = (message: string, type: ToastType = 'info', timeout = 5000): void => {
    showSnackbar(message, type, timeout)
  }

  // ========================================
  // Return Public API
  // ========================================

  return {
    // State
    notifications,
    loading,
    error,

    // Computed
    unreadNotifications,
    totalUnread,
    pendingReviews,

    // Actions
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    addNotification,
    removeNotification,
    clearAll,
    clearError,
    startPolling,
    stopPolling,

    // Toast Actions
    addToast
  }
})

export default useNotificationsStore
