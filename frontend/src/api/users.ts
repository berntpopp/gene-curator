/**
 * User management API client for admin operations
 */
import axios, { type InternalAxiosRequestConfig } from 'axios'
import type { Schema } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1/users`,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token to requests
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Handle token refresh on 401 responses
apiClient.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post<Schema<'Token'>>(
            `${API_BASE_URL}/api/v1/auth/refresh`,
            {
              refresh_token: refreshToken
            }
          )

          const { access_token } = response.data
          localStorage.setItem('access_token', access_token)

          // Retry the original request
          const originalRequest = error.config as InternalAxiosRequestConfig
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient.request(originalRequest)
        } catch {
          // Refresh failed, redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export const usersApi = {
  /**
   * Get all users with pagination
   */
  async getUsers(params: Record<string, unknown> = {}): Promise<Schema<'UserResponse'>[]> {
    const response = await apiClient.get<Schema<'UserResponse'>[]>('/', { params })
    return response.data
  },

  /**
   * Search users by name or email
   */
  async searchUsers(
    query: string,
    params: Record<string, unknown> = {}
  ): Promise<Schema<'UserResponse'>[]> {
    const response = await apiClient.get<Schema<'UserResponse'>[]>('/search', {
      params: { q: query, ...params }
    })
    return response.data
  },

  /**
   * Get user statistics
   */
  async getUserStatistics(): Promise<unknown> {
    const response = await apiClient.get<unknown>('/statistics')
    return response.data
  },

  /**
   * Get a specific user by ID
   */
  async getUser(userId: string): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.get<Schema<'UserResponse'>>(`/${userId}`)
    return response.data
  },

  /**
   * Create a new user
   */
  async createUser(userData: Schema<'UserCreate'>): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.post<Schema<'UserResponse'>>('/', userData)
    return response.data
  },

  /**
   * Update user information
   */
  async updateUser(
    userId: string,
    userData: Schema<'UserUpdate'>
  ): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.put<Schema<'UserResponse'>>(`/${userId}`, userData)
    return response.data
  },

  /**
   * Update user password (admin only)
   */
  async updateUserPassword(userId: string, newPassword: string): Promise<unknown> {
    const response = await apiClient.put<unknown>(`/${userId}/password`, {
      new_password: newPassword
    })
    return response.data
  },

  /**
   * Activate user account
   */
  async activateUser(userId: string): Promise<unknown> {
    const response = await apiClient.put<unknown>(`/${userId}/activate`)
    return response.data
  },

  /**
   * Deactivate user account
   */
  async deactivateUser(userId: string): Promise<unknown> {
    const response = await apiClient.put<unknown>(`/${userId}/deactivate`)
    return response.data
  },

  /**
   * Delete a user
   */
  async deleteUser(userId: string): Promise<unknown> {
    const response = await apiClient.delete<unknown>(`/${userId}`)
    return response.data
  },

  /**
   * Get user activity summary
   */
  async getUserActivity(userId: string): Promise<unknown> {
    const response = await apiClient.get<unknown>(`/${userId}/activity`)
    return response.data
  }
}

export default usersApi
