import apiClient from './client.js'

export const authAPI = {
  async login(credentials) {
    const response = await apiClient.post('/auth/login', {
      email: credentials.email,
      password: credentials.password
    })
    return response.data
  },

  async register(userData) {
    const response = await apiClient.post('/auth/register', userData)
    return response.data
  },

  async refresh(refreshToken) {
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken
    })
    return response.data
  },

  async logout() {
    const response = await apiClient.post('/auth/logout')
    return response.data
  },

  async me() {
    const response = await apiClient.get('/auth/me')
    return response.data
  },

  async changePassword(passwordData) {
    const response = await apiClient.post('/auth/change-password', passwordData)
    return response.data
  }
}

// Export as both named export and default for compatibility
export const authApi = authAPI
export default authAPI
