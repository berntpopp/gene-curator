import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { authAPI } from '@/api'
import { logService } from '@/services/logService'
import type { Schema } from '@/types/api'

vi.mock('@/api', () => ({
  authAPI: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(authAPI)

const makeUser = (role: string) =>
  ({ id: 'u1', email: 'a@b.c', name: 'Ada', role }) as Schema<'UserResponse'>

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters and role checks', () => {
    it('derives role getters from the user role', () => {
      const store = useAuthStore()
      expect(store.userRole).toBe('guest')
      expect(store.isAdmin).toBe(false)

      store.user = makeUser('admin')
      expect(store.isAdmin).toBe(true)
      expect(store.isCurator).toBe(true)
      expect(store.isViewer).toBe(true)
      expect(store.userRole).toBe('admin')
    })

    it('restricts curators and viewers', () => {
      const store = useAuthStore()
      store.user = makeUser('viewer')
      expect(store.isCurator).toBe(false)
      expect(store.isViewer).toBe(true)
    })

    it('checks role hierarchy in hasRole / hasAnyRole', () => {
      const store = useAuthStore()
      expect(store.hasRole('viewer')).toBe(false)

      store.user = makeUser('curator')
      expect(store.hasRole('viewer')).toBe(true)
      expect(store.hasRole('curator')).toBe(true)
      expect(store.hasRole('admin')).toBe(false)
      expect(store.hasAnyRole(['admin', 'curator'])).toBe(true)
      expect(store.hasAnyRole(['admin'])).toBe(false)

      store.user = makeUser('unknown-role')
      expect(store.hasRole('viewer')).toBe(false)
    })
  })

  describe('initialize', () => {
    it('does nothing without a stored token', async () => {
      const store = useAuthStore()
      await store.initialize()
      expect(api.me).not.toHaveBeenCalled()
      expect(store.isAuthenticated).toBe(false)
    })

    it('loads the current user when a token is stored', async () => {
      localStorage.setItem('access_token', 'tok')
      api.me.mockResolvedValue(makeUser('curator'))
      setActivePinia(createPinia())
      const store = useAuthStore()

      await store.initialize()

      expect(store.user?.role).toBe('curator')
      expect(store.isAuthenticated).toBe(true)
      expect(store.token).toBe('tok')
      expect(store.loading).toBe(false)
    })

    it('clears auth when the stored token is rejected', async () => {
      localStorage.setItem('access_token', 'expired')
      api.me.mockRejectedValue(new Error('401'))
      setActivePinia(createPinia())
      const store = useAuthStore()

      await store.initialize()

      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('login', () => {
    it('stores tokens, fetches the user and returns the response', async () => {
      api.login.mockResolvedValue({ access_token: 'a', refresh_token: 'r' })
      api.me.mockResolvedValue(makeUser('user'))
      const store = useAuthStore()

      const result = await store.login({ email: 'a@b.c', password: 'pw' })

      expect(api.login).toHaveBeenCalledWith({ email: 'a@b.c', password: 'pw' })
      expect(result).toEqual({ access_token: 'a', refresh_token: 'r' })
      expect(store.token).toBe('a')
      expect(store.refreshToken).toBe('r')
      expect(localStorage.getItem('access_token')).toBe('a')
      expect(localStorage.getItem('refresh_token')).toBe('r')
      expect(store.user?.email).toBe('a@b.c')
      expect(store.isAuthenticated).toBe(true)
      expect(store.error).toBeNull()
    })

    it('clears auth and rethrows on failure (error text is reset by clearAuth, see report)', async () => {
      const failure = Object.assign(new Error('bad'), {
        response: { data: { detail: 'Invalid credentials' } }
      })
      api.login.mockRejectedValue(failure)
      const store = useAuthStore()

      await expect(store.login({ email: 'x', password: 'y' })).rejects.toBe(failure)

      expect(store.isAuthenticated).toBe(false)
      expect(store.token).toBeNull()
      expect(store.loading).toBe(false)
    })

    it('rethrows non-API failures without authenticating', async () => {
      api.login.mockRejectedValue(new Error('network'))
      const store = useAuthStore()

      await expect(store.login({ email: 'x', password: 'y' })).rejects.toThrow('network')
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('register', () => {
    it('auto-logs in when the API returns a user', async () => {
      api.register.mockResolvedValue({ user: makeUser('user') })
      api.login.mockResolvedValue({ access_token: 'a', refresh_token: 'r' })
      api.me.mockResolvedValue(makeUser('user'))
      const store = useAuthStore()

      const result = await store.register({
        email: 'new@b.c',
        password: 'pw',
        name: 'New'
      } as Schema<'UserCreate'>)

      expect(result).toEqual({ user: makeUser('user') })
      expect(api.login).toHaveBeenCalledWith({ email: 'new@b.c', password: 'pw' })
      expect(store.isAuthenticated).toBe(true)
    })

    it('skips auto-login when the response has no user', async () => {
      api.register.mockResolvedValue({ message: 'check your email' })
      const store = useAuthStore()

      await store.register({ email: 'x@y.z', password: 'pw' } as Schema<'UserCreate'>)

      expect(api.login).not.toHaveBeenCalled()
      expect(store.isAuthenticated).toBe(false)
    })

    it('sets the detail message and rethrows on failure', async () => {
      const failure = Object.assign(new Error('dup'), {
        response: { data: { detail: 'Email taken' } }
      })
      api.register.mockRejectedValue(failure)
      const store = useAuthStore()

      await expect(store.register({} as Schema<'UserCreate'>)).rejects.toBe(failure)
      expect(store.error).toBe('Email taken')
      expect(store.loading).toBe(false)
    })

    it('uses the generic message when registration fails without detail', async () => {
      api.register.mockRejectedValue(new Error('boom'))
      const store = useAuthStore()

      await expect(store.register({} as Schema<'UserCreate'>)).rejects.toThrow('boom')
      expect(store.error).toBe('Registration failed')
    })
  })

  describe('logout', () => {
    it('calls the API when a token exists and clears auth', async () => {
      api.logout.mockResolvedValue({} as never)
      const store = useAuthStore()
      store.token = 'tok'
      store.user = makeUser('user')

      await store.logout()

      expect(api.logout).toHaveBeenCalledTimes(1)
      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
    })

    it('skips the API call without a token', async () => {
      const store = useAuthStore()
      store.token = null

      await store.logout()

      expect(api.logout).not.toHaveBeenCalled()
    })

    it('still clears auth and logs a warning when the API call fails', async () => {
      api.logout.mockRejectedValue(new Error('offline'))
      const store = useAuthStore()
      store.token = 'tok'
      store.user = makeUser('user')

      await store.logout()

      expect(logService.warn).toHaveBeenCalledWith(
        'Logout API call failed',
        expect.objectContaining({ error: 'offline' })
      )
      expect(store.user).toBeNull()
    })
  })

  describe('refreshAccessToken', () => {
    it('stores and returns the new access token', async () => {
      api.refresh.mockResolvedValue({ access_token: 'new' })
      const store = useAuthStore()
      store.refreshToken = 'r'

      await expect(store.refreshAccessToken()).resolves.toBe('new')

      expect(api.refresh).toHaveBeenCalledWith('r')
      expect(store.token).toBe('new')
      expect(localStorage.getItem('access_token')).toBe('new')
    })

    it('clears auth and throws when no refresh token is available', async () => {
      const store = useAuthStore()
      store.refreshToken = null
      store.user = makeUser('user')

      await expect(store.refreshAccessToken()).rejects.toThrow('No refresh token available')
      expect(store.user).toBeNull()
    })

    it('clears auth and rethrows when the refresh request fails', async () => {
      api.refresh.mockRejectedValue(new Error('expired'))
      const store = useAuthStore()
      store.refreshToken = 'r'

      await expect(store.refreshAccessToken()).rejects.toThrow('expired')
      expect(store.refreshToken).toBeNull()
    })
  })

  describe('misc actions', () => {
    it('clearAuth resets state and storage', () => {
      localStorage.setItem('access_token', 'a')
      localStorage.setItem('refresh_token', 'r')
      const store = useAuthStore()
      store.user = makeUser('user')
      store.error = 'x'

      store.clearAuth()

      expect(store.user).toBeNull()
      expect(store.error).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
    })

    it('clearError resets only the error', () => {
      const store = useAuthStore()
      store.error = 'boom'
      store.clearError()
      expect(store.error).toBeNull()
    })

    it('getUserScopes returns an empty list', async () => {
      const store = useAuthStore()
      store.user = makeUser('user')
      await expect(store.getUserScopes()).resolves.toEqual([])
    })

    it('fetchDashboardStats returns zeroed placeholder stats', async () => {
      const store = useAuthStore()
      await expect(store.fetchDashboardStats()).resolves.toEqual({
        active_assignments: 0,
        completed_curations: 0,
        pending_reviews: 0,
        active_scopes: 0
      })
    })
  })
})
