import { defineStore } from 'pinia'
import { authAPI } from '@/api'
import { logService } from '@/services/logService'
import type { Schema } from '@/types/api'
import { errorMessage, toApiError } from './apiError'
import { clearFormRecoveryDrafts } from '@/utils/formRecoveryStorage'

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
        this.clearAuth() // Clear any partial state on error (also resets error)
        this.error = errorMessage(error, 'Login failed')
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
        if (response.id) {
          await this.login({
            email: userData.email,
            password: userData.password
          })
        }

        return response
      } catch (error) {
        this.error = errorMessage(error, 'Registration failed')
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

    clearAuth() {
      this.user = null
      this.token = null
      this.refreshToken = null
      this.isAuthenticated = false
      this.error = null

      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      clearFormRecoveryDrafts()
    },

    clearError() {
      this.error = null
    },

    hasRole(requiredRole: string) {
      if (!this.user) return false

      const roleHierarchy: Record<string, string[]> = {
        user: ['user'],
        admin: ['user', 'admin']
      }

      const userRoles = roleHierarchy[this.user.role] || []
      return userRoles.includes(requiredRole)
    },

    hasAnyRole(requiredRoles: string[]) {
      return requiredRoles.some(role => this.hasRole(role))
    }
  }
})
