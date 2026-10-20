import apiClient from './client'
import type { Schema } from '@/types/api'
import type { MessageResponse } from './responses'

export const usersApi = {
  /**
   * Get all users with pagination
   */
  async getUsers(params: Record<string, unknown> = {}): Promise<Schema<'UserResponse'>[]> {
    const response = await apiClient.get<Schema<'UserResponse'>[]>('/users/', { params })
    return response.data
  },

  /**
   * Search users by name or email
   */
  async searchUsers(
    query: string,
    params: Record<string, unknown> = {}
  ): Promise<Schema<'UserResponse'>[]> {
    const response = await apiClient.get<Schema<'UserResponse'>[]>('/users/search', {
      params: { q: query, ...params }
    })
    return response.data
  },

  /**
   * Get user statistics
   */
  async getUserStatistics(): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>('/users/statistics')
    return response.data
  },

  /**
   * Get a specific user by ID
   */
  async getUser(userId: string): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.get<Schema<'UserResponse'>>(`/users/${userId}`)
    return response.data
  },

  /**
   * Create a new user
   */
  async createUser(userData: Schema<'UserCreate'>): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.post<Schema<'UserResponse'>>('/users/', userData)
    return response.data
  },

  /**
   * Update user information
   */
  async updateUser(
    userId: string,
    userData: Schema<'UserUpdate'>
  ): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.put<Schema<'UserResponse'>>(`/users/${userId}`, userData)
    return response.data
  },

  /**
   * Update user password (admin only)
   */
  async updateUserPassword(userId: string, newPassword: string): Promise<MessageResponse> {
    const response = await apiClient.put<MessageResponse>(`/users/${userId}/password`, {
      new_password: newPassword
    })
    return response.data
  },

  /**
   * Activate user account
   */
  async activateUser(userId: string): Promise<MessageResponse> {
    const response = await apiClient.put<MessageResponse>(`/users/${userId}/activate`)
    return response.data
  },

  /**
   * Deactivate user account
   */
  async deactivateUser(userId: string): Promise<MessageResponse> {
    const response = await apiClient.put<MessageResponse>(`/users/${userId}/deactivate`)
    return response.data
  },

  /**
   * Delete a user
   */
  async deleteUser(userId: string): Promise<MessageResponse> {
    const response = await apiClient.delete<MessageResponse>(`/users/${userId}`)
    return response.data
  },

  /**
   * Get user activity summary
   */
  async getUserActivity(userId: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(`/users/${userId}/activity`)
    return response.data
  }
}

export default usersApi
