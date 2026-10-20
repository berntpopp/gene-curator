import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'

const auth = vi.hoisted(() => ({
  token: 'jwt' as string | null,
  logout: vi.fn(),
  refreshAccessToken: vi.fn()
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => auth
}))

vi.mock('../useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import { useSessionTimeout, type UseSessionTimeoutReturn } from '../useSessionTimeout'

const MINUTE = 60_000
const NOW = new Date('2026-06-01T12:00:00Z').getTime()

function jwtExpiring(ms: number): string {
  const body = btoa(JSON.stringify({ exp: Math.floor(ms / 1000) }))
  return `h.${body}.s`
}

function mountSession(): { api: UseSessionTimeoutReturn; unmount: () => void } {
  let api: UseSessionTimeoutReturn | undefined
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useSessionTimeout()
        return () => h('div')
      }
    })
  )
  if (!api) throw new Error('composable not initialised')
  return { api, unmount: () => wrapper.unmount() }
}

describe('useSessionTimeout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
    auth.token = 'jwt'
    auth.token = jwtExpiring(NOW + 60 * MINUTE)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does nothing when the token has no readable exp claim', () => {
    auth.token = 'opaque'
    const { api, unmount } = mountSession()

    expect(api.timeRemaining.value).toBe(0)
    expect(auth.logout).not.toHaveBeenCalled()
    unmount()
  })

  it('does nothing when not authenticated', () => {
    auth.token = null
    const { api, unmount } = mountSession()

    expect(api.showWarning.value).toBe(false)
    expect(api.timeRemaining.value).toBe(0)
    expect(auth.logout).not.toHaveBeenCalled()
    unmount()
  })

  it('reports time remaining in seconds while the token is healthy', () => {
    const { api, unmount } = mountSession()

    expect(api.timeRemaining.value).toBe(3600)
    expect(api.showWarning.value).toBe(false)
    unmount()
  })

  it('shows the warning once the token is within 5 minutes of expiry', () => {
    auth.token = jwtExpiring(NOW + 4 * MINUTE)
    const { api, unmount } = mountSession()

    expect(api.showWarning.value).toBe(true)
    expect(api.timeRemaining.value).toBe(240)
    unmount()
  })

  it('logs out when the token has expired', () => {
    auth.token = jwtExpiring(NOW - 1000)
    const { api, unmount } = mountSession()

    expect(auth.logout).toHaveBeenCalled()
    expect(api.showWarning.value).toBe(false)
    expect(api.timeRemaining.value).toBe(0)
    unmount()
  })

  it('re-checks every minute and hides the warning after a session extension', () => {
    auth.token = jwtExpiring(NOW + 4 * MINUTE)
    const { api, unmount } = mountSession()
    expect(api.showWarning.value).toBe(true)

    auth.token = jwtExpiring(NOW + 30 * MINUTE)
    vi.advanceTimersByTime(MINUTE)

    expect(api.showWarning.value).toBe(false)
    unmount()
  })

  it('extendSession refreshes the token and clears the warning', async () => {
    auth.token = jwtExpiring(NOW + 4 * MINUTE)
    auth.refreshAccessToken.mockResolvedValue(jwtExpiring(NOW + 60 * MINUTE))
    const { api, unmount } = mountSession()

    await api.extendSession()

    expect(auth.refreshAccessToken).toHaveBeenCalled()
    expect(api.showWarning.value).toBe(false)
    expect(api.timeRemaining.value).toBe(0)
    unmount()
  })

  it('extendSession rethrows refresh failures', async () => {
    auth.refreshAccessToken.mockRejectedValue(new Error('refresh denied'))
    const { api, unmount } = mountSession()

    await expect(api.extendSession()).rejects.toThrow('refresh denied')
    unmount()
  })

  it('dismissWarning hides the warning without touching the session', () => {
    auth.token = jwtExpiring(NOW + 4 * MINUTE)
    const { api, unmount } = mountSession()

    api.dismissWarning()

    expect(api.showWarning.value).toBe(false)
    expect(auth.logout).not.toHaveBeenCalled()
    unmount()
  })

  it('stops monitoring on unmount', () => {
    const { unmount } = mountSession()
    unmount()
    auth.token = jwtExpiring(NOW - 1000)

    vi.advanceTimersByTime(5 * MINUTE)

    expect(auth.logout).not.toHaveBeenCalled()
  })
})
