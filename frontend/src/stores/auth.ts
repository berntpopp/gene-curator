import { defineStore } from 'pinia'
import { useScopesStore } from './scopes'
import { authAPI } from '@/api'
import { isExpired } from '@/api/client'
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

let initPromise: Promise<void> | null = null

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
    // Concurrent callers (router guard, components) share one in-flight /me request
    initialize() {
      initPromise ??= this.loadStoredSession().finally(() => {
        initPromise = null
      })
      return initPromise
    },

    async loadStoredSession() {
      const token = localStorage.getItem('access_token')
      const refresh = localStorage.getItem('refresh_token')
      // B21: an expired session that cannot refresh is dropped without a sure-401 round trip
      if (token && isExpired(token) && (!refresh || isExpired(refresh))) return this.clearAuth()
      // MUI-19: no access token is no session; a leftover refresh token alone is dropped
      if (!token) return refresh ? this.clearAuth() : undefined
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
      useScopesStore().reset() // menus and the Setup guard read scope roles from it
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
