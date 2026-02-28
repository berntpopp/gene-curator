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

const POLL_INTERVAL_MS = 60000

export const useNotificationsStore = defineStore('notifications', () => {
  // ========================================
  // State
  // ========================================

  const notifications = ref([])
  const loading = ref(false)
  const error = ref(null)
  let pollTimer = null

  // Toast notification state
  const toasts = ref([])
  let toastIdCounter = 0

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
  const fetchNotifications = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await notificationsAPI.getNotifications({ limit: 50 })
      notifications.value = response.notifications || []

      logService.debug('Fetched notifications', {
        count: notifications.value.length,
        unread: totalUnread.value
      })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch notifications'
      logService.error('Failed to fetch notifications', {
        error: err.message
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
  const markAsRead = async notificationId => {
    try {
      await notificationsAPI.markAsRead(notificationId)

      // Update local state
      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.is_read = true
        logService.debug('Marked notification as read', { notificationId })
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to mark notification as read'
      logService.error('Failed to mark notification as read', {
        notificationId,
        error: err.message
      })
      throw err
    }
  }

  /**
   * Mark all notifications as read
   * @returns {Promise<void>}
   */
  const markAllAsRead = async () => {
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
      error.value = err.response?.data?.detail || 'Failed to mark all notifications as read'
      logService.error('Failed to mark all notifications as read', {
        error: err.message
      })
      throw err
    }
  }

  /**
   * Add a notification (for real-time updates)
   * @param {Object} notification - Notification object
   */
  const addNotification = notification => {
    notifications.value.unshift(notification)
    logService.debug('Added notification', { notification })
  }

  /**
   * Remove a notification
   * @param {string} notificationId - Notification UUID
   */
  const removeNotification = notificationId => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index !== -1) {
      notifications.value.splice(index, 1)
      logService.debug('Removed notification', { notificationId })
    }
  }

  /**
   * Clear all notifications
   */
  const clearAll = () => {
    notifications.value = []
    error.value = null
    logService.info('Cleared all notifications')
  }

  /**
   * Clear error state
   */
  const clearError = () => {
    error.value = null
  }

  // ========================================
  // Polling
  // ========================================

  /**
   * Start polling for new notifications every 60 seconds
   */
  const startPolling = () => {
    stopPolling()
    fetchNotifications()
    pollTimer = setInterval(fetchNotifications, POLL_INTERVAL_MS)
    logService.debug('Notification polling started', { intervalMs: POLL_INTERVAL_MS })
  }

  /**
   * Stop polling for notifications
   */
  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      logService.debug('Notification polling stopped')
    }
  }

  // ========================================
  // Toast Notifications
  // ========================================

  /**
   * Add a toast notification (temporary snackbar message)
   * @param {string} message - Toast message to display
   * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
   * @param {number} timeout - Auto-dismiss timeout in ms (default: 5000)
   * @returns {number} Toast ID
   */
  const addToast = (message, type = 'info', timeout = 5000) => {
    const id = ++toastIdCounter
    const toast = {
      id,
      message,
      type,
      timeout,
      visible: true
    }

    toasts.value.push(toast)

    logService.debug('Toast notification added', { id, message, type })

    // Auto-dismiss after timeout
    if (timeout > 0) {
      setTimeout(() => {
        removeToast(id)
      }, timeout)
    }

    return id
  }

  /**
   * Remove a toast notification
   * @param {number} toastId - Toast ID to remove
   */
  const removeToast = toastId => {
    const index = toasts.value.findIndex(t => t.id === toastId)
    if (index !== -1) {
      toasts.value.splice(index, 1)
      logService.debug('Toast notification removed', { toastId })
    }
  }

  /**
   * Clear all toast notifications
   */
  const clearToasts = () => {
    toasts.value = []
    logService.debug('All toasts cleared')
  }

  // ========================================
  // Return Public API
  // ========================================

  return {
    // State
    notifications,
    loading,
    error,
    toasts,

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
    addToast,
    removeToast,
    clearToasts
  }
})

export default useNotificationsStore
