/**
 * Notifications Store
 *
 * Manages notification state, badge counts, and read/unread tracking.
 * Provides reactive notification data for the notification badge and dashboard.
 *
 * Features:
 * - Unread count tracking
 * - Priority-based notifications (critical, warning, info)
 * - Mark as read functionality
 * - Real-time updates (ready for WebSocket integration)
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#notification-system
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// import apiClient from '@/api/client' // TODO: Uncomment when API endpoints are ready
import { logService } from '@/services/logService'

export const useNotificationsStore = defineStore('notifications', () => {
  // ========================================
  // State
  // ========================================

  const notifications = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ========================================
  // Getters (Computed)
  // ========================================

  /**
   * Unread notifications only
   */
  const unreadNotifications = computed(() => notifications.value.filter(n => !n.read))

  /**
   * Total unread count
   */
  const totalUnread = computed(() => unreadNotifications.value.length)

  /**
   * Critical priority unread count
   */
  const criticalCount = computed(
    () => unreadNotifications.value.filter(n => n.priority === 'critical').length
  )

  /**
   * Warning priority unread count
   */
  const warningCount = computed(
    () => unreadNotifications.value.filter(n => n.priority === 'warning').length
  )

  /**
   * Info priority unread count
   */
  const infoCount = computed(
    () => unreadNotifications.value.filter(n => n.priority === 'info').length
  )

  /**
   * Pending reviews count (for reviewers)
   */
  const pendingReviews = computed(
    () => unreadNotifications.value.filter(n => n.type === 'review_request').length
  )

  /**
   * Draft reminders count (for curators)
   */
  const draftReminders = computed(
    () => unreadNotifications.value.filter(n => n.type === 'draft_reminder').length
  )

  /**
   * Assignment notifications count
   */
  const assignmentNotifications = computed(
    () => unreadNotifications.value.filter(n => n.type === 'assignment').length
  )

  /**
   * Highest priority level of unread notifications
   * Used to determine badge color
   */
  const highestPriority = computed(() => {
    if (criticalCount.value > 0) return 'critical'
    if (warningCount.value > 0) return 'warning'
    return 'info'
  })

  // ========================================
  // Actions
  // ========================================

  /**
   * Fetch all notifications from API
   * @returns {Promise<void>}
   */
  const fetchNotifications = async () => {
    loading.value = true
    error.value = null

    try {
      // TODO: Replace with actual API endpoint when available
      // const response = await apiClient.get('/api/v1/notifications')
      // notifications.value = response.data

      // Mock data for now
      notifications.value = [
        // {
        //   id: 1,
        //   type: 'review_request',
        //   priority: 'critical',
        //   title: 'Review Requested',
        //   message: 'Gene ABC curation needs your review',
        //   read: false,
        //   created_at: new Date().toISOString(),
        //   link: { name: 'CurationDetail', params: { id: 1 } }
        // }
      ]

      logService.debug('Fetched notifications', {
        count: notifications.value.length,
        unread: totalUnread.value
      })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch notifications'
      logService.error('Failed to fetch notifications', {
        error: err.message,
        stack: err.stack
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Mark a notification as read
   * @param {number} notificationId - Notification ID
   * @returns {Promise<void>}
   */
  const markAsRead = async notificationId => {
    try {
      // TODO: Replace with actual API endpoint when available
      // await apiClient.patch(`/api/v1/notifications/${notificationId}/read`)

      // Update local state
      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.read = true
        logService.debug('Marked notification as read', { notificationId })
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to mark notification as read'
      logService.error('Failed to mark notification as read', {
        notificationId,
        error: err.message,
        stack: err.stack
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
      // TODO: Replace with actual API endpoint when available
      // await apiClient.patch('/api/v1/notifications/read-all')

      // Update local state
      notifications.value.forEach(n => {
        n.read = true
      })

      logService.info('Marked all notifications as read', {
        count: notifications.value.length
      })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to mark all notifications as read'
      logService.error('Failed to mark all notifications as read', {
        error: err.message,
        stack: err.stack
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
   * @param {number} notificationId - Notification ID
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
  // WebSocket Integration (Future)
  // ========================================

  /**
   * Initialize WebSocket connection for real-time notifications
   * TODO: Implement when backend supports WebSocket
   */
  const initializeWebSocket = () => {
    // WebSocket logic here
    logService.info('WebSocket notifications not yet implemented')
  }

  /**
   * Disconnect WebSocket
   */
  const disconnectWebSocket = () => {
    // WebSocket cleanup here
    logService.debug('WebSocket disconnected')
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
    criticalCount,
    warningCount,
    infoCount,
    pendingReviews,
    draftReminders,
    assignmentNotifications,
    highestPriority,

    // Actions
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    addNotification,
    removeNotification,
    clearAll,
    clearError,
    initializeWebSocket,
    disconnectWebSocket
  }
})

export default useNotificationsStore
