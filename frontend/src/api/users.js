/**
 * User management API client for admin operations
 */

import axios from 'axios'

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
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          })

          const { access_token } = response.data
          localStorage.setItem('access_token', access_token)

          // Retry the original request
          error.config.headers.Authorization = `Bearer ${access_token}`
          return apiClient.request(error.config)
        } catch (refreshError) {
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
  async getUsers(params = {}) {
    const response = await apiClient.get('/', { params })
    return response.data
  },

  /**
   * Search users by name or email
   */
  async searchUsers(query, params = {}) {
    const response = await apiClient.get('/search', {
      params: { q: query, ...params }
    })
    return response.data
  },

  /**
   * Get user statistics
   */
  async getUserStatistics() {
    const response = await apiClient.get('/statistics')
    return response.data
  },

  /**
   * Get a specific user by ID
   */
  async getUser(userId) {
    const response = await apiClient.get(`/${userId}`)
    return response.data
  },

  /**
   * Create a new user
   */
  async createUser(userData) {
    const response = await apiClient.post('/', userData)
    return response.data
  },

  /**
   * Update user information
   */
  async updateUser(userId, userData) {
    const response = await apiClient.put(`/${userId}`, userData)
    return response.data
  },

  /**
   * Update user password (admin only)
   */
  async updateUserPassword(userId, newPassword) {
    const response = await apiClient.put(`/${userId}/password`, { new_password: newPassword })
    return response.data
  },

  /**
   * Activate user account
   */
  async activateUser(userId) {
    const response = await apiClient.put(`/${userId}/activate`)
    return response.data
  },

  /**
   * Deactivate user account
   */
  async deactivateUser(userId) {
    const response = await apiClient.put(`/${userId}/deactivate`)
    return response.data
  },

  /**
   * Delete a user
   */
  async deleteUser(userId) {
    const response = await apiClient.delete(`/${userId}`)
    return response.data
  },

  /**
   * Get user activity summary
   */
  async getUserActivity(userId) {
    const response = await apiClient.get(`/${userId}/activity`)
    return response.data
  }
}

export default usersApi
