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

const makeToken = (access = 'a', refresh = 'r'): Schema<'Token'> => ({
  access_token: access,
  refresh_token: refresh,
  token_type: 'bearer',
  expires_in: 1800
})

const makeUser = (role: string) =>
  ({ id: 'u1', email: 'a@b.c', name: 'Ada', role }) as Schema<'UserResponse'>

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters and role checks', () => {
    it('derives admin from the application role only', () => {
      const store = useAuthStore()
      expect(store.userRole).toBe('guest')
      expect(store.isAdmin).toBe(false)

      store.user = makeUser('admin')
      expect(store.isAdmin).toBe(true)
      expect(store.userRole).toBe('admin')
    })

    it('checks the two application roles in hasRole / hasAnyRole', () => {
      const store = useAuthStore()
      expect(store.hasRole('user')).toBe(false)

      store.user = makeUser('user')
      expect(store.hasRole('user')).toBe(true)
      expect(store.hasRole('admin')).toBe(false)
      expect(store.hasAnyRole(['admin', 'user'])).toBe(true)
      expect(store.hasAnyRole(['admin'])).toBe(false)

      store.user = makeUser('admin')
      expect(store.hasRole('user')).toBe(true)
      expect(store.hasRole('admin')).toBe(true)

      // scope roles are not application roles
      store.user = makeUser('curator')
      expect(store.hasRole('curator')).toBe(false)
    })
  })

  describe('initialize', () => {
    it('does nothing without a stored token', async () => {
      const store = useAuthStore()
      await store.initialize()
      expect(api.me).not.toHaveBeenCalled()
      expect(store.isAuthenticated).toBe(false)
    })

    it('makes no auth call for a leftover refresh token alone, and drops it (MUI-19)', async () => {
      localStorage.setItem('refresh_token', 'refresh-1')
      const store = useAuthStore()
      await store.initialize()
      expect(api.me).not.toHaveBeenCalled()
      expect(api.refresh).not.toHaveBeenCalled()
      expect(localStorage.getItem('refresh_token')).toBeNull()
    })

    it('loads the current user when a token is stored', async () => {
      localStorage.setItem('access_token', 'tok')
      api.me.mockResolvedValue(makeUser('user'))
      setActivePinia(createPinia())
      const store = useAuthStore()

      await store.initialize()

      expect(store.user?.role).toBe('user')
      expect(store.isAuthenticated).toBe(true)
      expect(store.token).toBe('tok')
      expect(store.loading).toBe(false)
    })

    it('shares one /me request between concurrent calls', async () => {
      localStorage.setItem('access_token', 'tok')
      api.me.mockResolvedValue(makeUser('user'))
      setActivePinia(createPinia())
      const store = useAuthStore()

      await Promise.all([store.initialize(), store.initialize()])

      expect(api.me).toHaveBeenCalledTimes(1)
    })

    it('drops a stale session without calling the API (B21)', async () => {
      const past = `h.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 60 }))}.s`
      localStorage.setItem('access_token', past)
      localStorage.setItem('refresh_token', past)
      setActivePinia(createPinia())
      const store = useAuthStore()

      await store.initialize()

      expect(api.me).not.toHaveBeenCalled()
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(store.isAuthenticated).toBe(false)
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
      api.login.mockResolvedValue(makeToken())
      api.me.mockResolvedValue(makeUser('user'))
      const store = useAuthStore()

      const result = await store.login({ email: 'a@b.c', password: 'pw' })

      expect(api.login).toHaveBeenCalledWith({ email: 'a@b.c', password: 'pw' })
      expect(result).toEqual(makeToken())
      expect(store.token).toBe('a')
      expect(store.refreshToken).toBe('r')
      expect(localStorage.getItem('access_token')).toBe('a')
      expect(localStorage.getItem('refresh_token')).toBe('r')
      expect(store.user?.email).toBe('a@b.c')
      expect(store.isAuthenticated).toBe(true)
      expect(store.error).toBeNull()
    })

    it('keeps the failure message after clearing auth state', async () => {
      const failure = Object.assign(new Error('bad'), {
        response: { data: { detail: 'Invalid credentials' } }
      })
      api.login.mockRejectedValue(failure)
      const store = useAuthStore()

      await expect(store.login({ email: 'x', password: 'y' })).rejects.toBe(failure)

      expect(store.isAuthenticated).toBe(false)
      expect(store.token).toBeNull()
      expect(store.error).toBe('Invalid credentials')
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
      api.register.mockResolvedValue(makeUser('user'))
      api.login.mockResolvedValue(makeToken())
      api.me.mockResolvedValue(makeUser('user'))
      const store = useAuthStore()

      const result = await store.register({
        email: 'new@b.c',
        password: 'pw',
        name: 'New'
      } as Schema<'UserCreate'>)

      expect(result).toEqual(makeUser('user'))
      expect(api.login).toHaveBeenCalledWith({ email: 'new@b.c', password: 'pw' })
      expect(store.isAuthenticated).toBe(true)
    })

    it('skips auto-login when the response has no id', async () => {
      api.register.mockResolvedValue({} as Schema<'UserResponse'>)
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
      expect(store.error).toBe('boom')
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
  })
})

describe('auth store logout clears scope roles (review #608)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("forgets the previous user's scopes so menus and guards never reuse them", async () => {
    const { useScopesStore } = await import('@/stores/scopes')
    const scopes = useScopesStore()
    scopes.scopes = [{ id: 's1', user_role: 'admin' }] as never
    scopes.currentScope = { id: 's1' } as never
    useAuthStore().clearAuth()
    expect(scopes.scopes).toEqual([])
    expect(scopes.currentScope).toBeNull()
  })
})
