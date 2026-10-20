import apiClient from './client'
import type { Schema } from '@/types/api'

export const notificationsAPI = {
  /**
   * Get current user's notifications
   * @param params - Query params (is_read, skip, limit)
   */
  async getNotifications(
    params: Record<string, unknown> = {}
  ): Promise<Schema<'NotificationListResponse'>> {
    const response = await apiClient.get<Schema<'NotificationListResponse'>>('/notifications', {
      params
    })
    return response.data
  },

  /**
   * Mark a single notification as read
   * @param id - Notification UUID
   */
  async markAsRead(id: string): Promise<Schema<'NotificationResponse'>> {
    const response = await apiClient.patch<Schema<'NotificationResponse'>>(
      `/notifications/${id}/read`
    )
    return response.data
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(): Promise<unknown> {
    const response = await apiClient.patch<unknown>('/notifications/read-all')
    return response.data
  }
}
