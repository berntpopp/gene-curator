import apiClient from './client'
import type { Schema } from '@/types/api'
import type { MessageResponse } from './responses'

export const authAPI = {
  async login(credentials: Schema<'UserLogin'>): Promise<Schema<'Token'>> {
    const response = await apiClient.post<Schema<'Token'>>('/auth/login', {
      email: credentials.email,
      password: credentials.password
    })
    return response.data
  },

  async register(userData: Schema<'UserCreate'>): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.post<Schema<'UserResponse'>>('/auth/register', userData)
    return response.data
  },

  async refresh(refreshToken: string): Promise<Schema<'Token'>> {
    const response = await apiClient.post<Schema<'Token'>>('/auth/refresh', {
      refresh_token: refreshToken
    })
    return response.data
  },

  async logout(): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/logout')
    return response.data
  },

  async me(): Promise<Schema<'UserResponse'>> {
    const response = await apiClient.get<Schema<'UserResponse'>>('/auth/me')
    return response.data
  },

  async changePassword(passwordData: Schema<'PasswordChange'>): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/change-password', passwordData)
    return response.data
  }
}

// Export as both named export and default for compatibility
export const authApi = authAPI
export default authAPI
