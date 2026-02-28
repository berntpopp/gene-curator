import apiClient from './client.js'

export const notificationsAPI = {
  /**
   * Get current user's notifications
   * @param {Object} params - Query params (is_read, skip, limit)
   */
  async getNotifications(params = {}) {
    const response = await apiClient.get('/notifications', { params })
    return response.data
  },

  /**
   * Mark a single notification as read
   * @param {string} id - Notification UUID
   */
  async markAsRead(id) {
    const response = await apiClient.patch(`/notifications/${id}/read`)
    return response.data
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead() {
    const response = await apiClient.patch('/notifications/read-all')
    return response.data
  }
}
