import { defineStore } from 'pinia'
import { authAPI } from '@/api'
import { logService } from '@/services/logService'
import type { Schema } from '@/types/api'
import { toApiError } from './apiError'

interface AuthState {
  user: Schema<'UserResponse'> | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    isAuthenticated: false,
    loading: false,
    error: null
  }),

  getters: {
    isAdmin: state => state.user?.role === 'admin',
    isCurator: state => ['admin', 'curator'].includes(state.user?.role ?? ''),
    isViewer: state => ['admin', 'curator', 'viewer'].includes(state.user?.role ?? ''),
    userRole: state => state.user?.role || 'guest'
  },

  actions: {
    async initialize() {
      const token = localStorage.getItem('access_token')
      if (token) {
        try {
          this.loading = true
          const userData = await authAPI.me()
          this.user = userData
          this.isAuthenticated = true
          this.token = token
        } catch (error) {
          this.clearAuth()
        } finally {
          this.loading = false
        }
      }
    },

    async login(credentials: Schema<'UserLogin'>) {
      try {
        this.loading = true
        this.error = null

        const response = await authAPI.login(credentials)

        this.token = response.access_token
        this.refreshToken = response.refresh_token

        // Store tokens in localStorage
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)

        // Fetch user data using the new token
        const userData = await authAPI.me()
        this.user = userData
        this.isAuthenticated = true

        return response
      } catch (error) {
        this.error = toApiError(error).response?.data?.detail || 'Login failed'
        this.clearAuth() // Clear any partial state on error
        throw error
      } finally {
        this.loading = false
      }
    },

    async register(userData: Schema<'UserCreate'>) {
      try {
        this.loading = true
        this.error = null

        const response = await authAPI.register(userData)

        // Auto-login after successful registration
        if (response.user) {
          await this.login({
            email: userData.email,
            password: userData.password
          })
        }

        return response
      } catch (error) {
        this.error = toApiError(error).response?.data?.detail || 'Registration failed'
        throw error
      } finally {
        this.loading = false
      }
    },

    async logout() {
      try {
        if (this.token) {
          await authAPI.logout()
        }
      } catch (error) {
        logService.warn('Logout API call failed', {
          error: toApiError(error).message,
          stack: toApiError(error).stack
        })
      } finally {
        this.clearAuth()
      }
    },

    async refreshAccessToken(): Promise<string> {
      try {
        if (!this.refreshToken) {
          throw new Error('No refresh token available')
        }

        const response = await authAPI.refresh(this.refreshToken)

        this.token = response.access_token
        localStorage.setItem('access_token', response.access_token)

        return response.access_token
      } catch (error) {
        this.clearAuth()
        throw error
      }
    },

    clearAuth() {
      this.user = null
      this.token = null
      this.refreshToken = null
      this.isAuthenticated = false
      this.error = null

      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },

    clearError() {
      this.error = null
    },

    hasRole(requiredRole: string) {
      if (!this.user) return false

      const roleHierarchy: Record<string, string[]> = {
        viewer: ['viewer'],
        curator: ['viewer', 'curator'],
        admin: ['viewer', 'curator', 'admin']
      }

      const userRoles = roleHierarchy[this.user.role] || []
      return userRoles.includes(requiredRole)
    },

    hasAnyRole(requiredRoles: string[]) {
      return requiredRoles.some(role => this.hasRole(role))
    },

    async getUserScopes() {
      try {
        if (!this.user) return []

        // For now, return empty array until user scopes are properly implemented
        // This method can be extended when user-scope relationships are added
        return []
      } catch (error) {
        logService.warn('Failed to fetch user scopes', {
          error: toApiError(error).message,
          stack: toApiError(error).stack
        })
        return []
      }
    },

    async fetchDashboardStats() {
      // Mock dashboard stats for now
      // This can be replaced with real API calls when backend supports it
      return {
        active_assignments: 0,
        completed_curations: 0,
        pending_reviews: 0,
        active_scopes: 0
      }
    }
  }
})
