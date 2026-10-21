import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import apiClient from '../client'
import { logService } from '@/services/logService'

vi.mock('@/services/logService', () => {
  const logService = {
    correlationId: null as string | null,
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    logApiCall: vi.fn(),
    setCorrelationId: vi.fn((id: string) => {
      logService.correlationId = id
    }),
    clearCorrelationId: vi.fn(() => {
      logService.correlationId = null
    })
  }
  return { logService }
})

type Handler = (config: InternalAxiosRequestConfig) => Promise<AxiosResponse>

/** Route every request through a stub adapter so the real interceptors run */
let handler: Handler = () => Promise.reject(new Error('no handler set'))
apiClient.defaults.adapter = config => handler(config)

function ok(config: InternalAxiosRequestConfig, data: unknown): Promise<AxiosResponse> {
  return Promise.resolve({ data, status: 200, statusText: 'OK', headers: {}, config })
}

function fail(config: InternalAxiosRequestConfig, status: number): Promise<never> {
  return Promise.reject(
    new AxiosError('request failed', 'ERR_BAD_REQUEST', config, null, {
      data: { detail: 'nope' },
      status,
      statusText: '',
      headers: {},
      config
    })
  )
}

describe('api client', () => {
  let originalLocation: Location

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    originalLocation = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: 'http://localhost/current', pathname: '/assignments', search: '?tab=1' }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
  })

  it('adds the bearer token and a request id, then clears the correlation id on success', async () => {
    localStorage.setItem('access_token', 'old-token')
    let sent: InternalAxiosRequestConfig | undefined
    handler = config => {
      sent = config
      return ok(config, { items: [1] })
    }

    const response = await apiClient.get('/genes/')

    expect(response.data).toEqual({ items: [1] })
    expect(sent?.headers.Authorization).toBe('Bearer old-token')
    const requestId = sent?.headers['X-Request-ID']
    expect(requestId).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/))
    expect(logService.setCorrelationId).toHaveBeenCalledWith(requestId)
    expect(logService.logApiCall).toHaveBeenCalledWith('GET', '/genes/', 200, expect.any(Number))
    expect(logService.clearCorrelationId).toHaveBeenCalled()
  })

  it('sends no Authorization header when no token is stored', async () => {
    let sent: InternalAxiosRequestConfig | undefined
    handler = config => {
      sent = config
      return ok(config, {})
    }

    await apiClient.get('/health')

    expect(sent?.headers.Authorization).toBeUndefined()
  })

  it('refreshes an expired token and retries the original request once', async () => {
    localStorage.setItem('access_token', 'expired')
    localStorage.setItem('refresh_token', 'refresh-1')
    const refreshSpy = vi.spyOn(axios, 'post').mockResolvedValue({
      data: { access_token: 'fresh', refresh_token: 'refresh-2' }
    } as AxiosResponse)
    const seen: string[] = []
    handler = config => {
      const auth = String(config.headers.Authorization)
      seen.push(auth)
      return auth === 'Bearer fresh' ? ok(config, { value: 42 }) : fail(config, 401)
    }

    const response = await apiClient.get('/curations/')

    expect(response.data).toEqual({ value: 42 })
    expect(seen).toEqual(['Bearer expired', 'Bearer fresh'])
    expect(refreshSpy).toHaveBeenCalledTimes(1)
    expect(refreshSpy).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/auth\/refresh$/), {
      refresh_token: 'refresh-1'
    })
    expect(localStorage.getItem('access_token')).toBe('fresh')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-2')
    expect(logService.info).toHaveBeenCalledWith('Token refreshed successfully')
  })

  describe('expired access token on boot', () => {
    const jwt = (exp: number) => `h.${btoa(JSON.stringify({ exp }))}.s`
    const past = () => jwt(Math.floor(Date.now() / 1000) - 60)

    it('refreshes before sending, so the API never sees the stale token (no 401 round trip)', async () => {
      localStorage.setItem('access_token', past())
      localStorage.setItem('refresh_token', 'refresh-1')
      const refreshSpy = vi.spyOn(axios, 'post').mockResolvedValue({
        data: { access_token: 'fresh', refresh_token: 'refresh-2' }
      } as AxiosResponse)
      const seen: string[] = []
      handler = config => {
        seen.push(String(config.headers.Authorization))
        return ok(config, {})
      }

      await Promise.all([apiClient.get('/me/work'), apiClient.get('/scopes/')])

      expect(seen).toEqual(['Bearer fresh', 'Bearer fresh'])
      expect(refreshSpy).toHaveBeenCalledTimes(1)
    })

    it('does not pre-refresh login/refresh calls, valid tokens or opaque tokens', async () => {
      const refreshSpy = vi.spyOn(axios, 'post')
      handler = config => ok(config, {})
      localStorage.setItem('refresh_token', 'refresh-1')

      localStorage.setItem('access_token', past())
      await apiClient.post('/auth/login', {})
      localStorage.setItem('access_token', jwt(Math.floor(Date.now() / 1000) + 600))
      await apiClient.get('/me/work')
      localStorage.setItem('access_token', 'not-a-jwt')
      await apiClient.get('/me/work')

      expect(refreshSpy).not.toHaveBeenCalled()
    })

    it('falls through to the normal 401 handling when the pre-refresh fails', async () => {
      localStorage.setItem('access_token', past())
      localStorage.setItem('refresh_token', 'refresh-1')
      vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh down'))
      handler = config => fail(config, 401)

      await expect(apiClient.get('/me/work')).rejects.toBeDefined()
    })
  })

  it('does not refresh again when the retried request is also unauthorized', async () => {
    localStorage.setItem('access_token', 'expired')
    localStorage.setItem('refresh_token', 'refresh-1')
    const refreshSpy = vi.spyOn(axios, 'post').mockResolvedValue({
      data: { access_token: 'fresh', refresh_token: 'refresh-2' }
    } as AxiosResponse)
    handler = config => fail(config, 401)

    await expect(apiClient.get('/curations/')).rejects.toMatchObject({
      response: { status: 401 }
    })

    expect(refreshSpy).toHaveBeenCalledTimes(1)
  })

  it('rejects a 401 without attempting a refresh when no refresh token is stored', async () => {
    localStorage.setItem('access_token', 'expired')
    const refreshSpy = vi.spyOn(axios, 'post')
    handler = config => fail(config, 401)

    await expect(apiClient.get('/me')).rejects.toMatchObject({ response: { status: 401 } })

    expect(refreshSpy).not.toHaveBeenCalled()
    expect(localStorage.getItem('access_token')).toBe('expired')
    expect(window.location.href).toBe('http://localhost/current')
  })

  it('does not add a redirect when already on the login page', async () => {
    localStorage.setItem('refresh_token', 'dead-refresh')
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: 'x', pathname: '/login', search: '' }
    })
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh rejected'))
    handler = config => fail(config, 401)
    await expect(apiClient.get('/me')).rejects.toThrow()
    expect(window.location.href).toBe('x')
  })

  it('clears tokens, redirects to login and rejects when the refresh fails', async () => {
    localStorage.setItem('access_token', 'expired')
    localStorage.setItem('refresh_token', 'dead-refresh')
    const refreshError = new Error('refresh rejected')
    vi.spyOn(axios, 'post').mockRejectedValue(refreshError)
    handler = config => fail(config, 401)

    await expect(apiClient.get('/me')).rejects.toBe(refreshError)

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(window.location.href).toBe('/login?reason=expired&redirect=%2Fassignments%3Ftab%3D1')
    expect(logService.warn).toHaveBeenCalledWith('Token refresh failed, redirecting to login', {
      error: 'refresh rejected'
    })
    expect(logService.clearCorrelationId).toHaveBeenCalled()
  })

  it('logs non-401 failures as API errors and rejects with the original error', async () => {
    handler = config => fail(config, 500)

    await expect(apiClient.post('/genes', { symbol: 'X' })).rejects.toMatchObject({
      response: { status: 500 }
    })

    expect(logService.logApiCall).toHaveBeenCalledWith('POST', '/genes', 500, expect.any(Number))
    expect(logService.error).toHaveBeenCalledWith(
      'API Error',
      expect.objectContaining({ method: 'post', url: '/genes', status: 500 })
    )
    expect(logService.clearCorrelationId).toHaveBeenCalled()
  })

  it('shares one refresh between concurrent 401s and retries each request', async () => {
    localStorage.setItem('access_token', 'expired')
    localStorage.setItem('refresh_token', 'refresh-1')
    const refreshSpy = vi.spyOn(axios, 'post').mockResolvedValue({
      data: { access_token: 'fresh', refresh_token: 'refresh-2' }
    } as AxiosResponse)
    handler = config =>
      config.headers.Authorization === 'Bearer fresh' ? ok(config, {}) : fail(config, 401)

    const results = await Promise.all([
      apiClient.get('/genes/'),
      apiClient.get('/curations/'),
      apiClient.get('/scopes/')
    ])

    expect(results).toHaveLength(3)
    expect(refreshSpy).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('refresh_token')).toBe('refresh-2')
  })

  it.each(['/auth/login', '/auth/register'])(
    'surfaces a 401 from %s without refreshing or redirecting',
    async url => {
      localStorage.setItem('refresh_token', 'refresh-1')
      const refreshSpy = vi.spyOn(axios, 'post')
      handler = config => fail(config, 401)

      await expect(apiClient.post(url, {})).rejects.toMatchObject({ response: { status: 401 } })

      expect(refreshSpy).not.toHaveBeenCalled()
      expect(window.location.href).toBe('http://localhost/current')
    }
  )

  it('does not log a cancelled request as an API error', async () => {
    handler = config => Promise.reject(new axios.CanceledError('canceled', config))

    await expect(apiClient.get('/search')).rejects.toBeInstanceOf(axios.CanceledError)

    expect(logService.error).not.toHaveBeenCalled()
    expect(logService.clearCorrelationId).toHaveBeenCalled()
  })

  it('logs only the status and detail of an error, never the response body', async () => {
    handler = config =>
      Promise.reject(
        new AxiosError('bad', 'ERR_BAD_REQUEST', config, null, {
          data: { detail: [{ msg: 'field required' }], input: { email: 'ada@example.org' } },
          status: 422,
          statusText: '',
          headers: {},
          config
        })
      )

    await expect(apiClient.post('/genes/', {})).rejects.toBeDefined()

    const fields = vi.mocked(logService.error).mock.calls[0]?.[1]
    expect(fields).toMatchObject({ status: 422, detail: 'field required' })
    expect(JSON.stringify(fields)).not.toContain('ada@example.org')
  })

  it('keeps the correlation id of a newer in-flight request when an older one finishes', async () => {
    const pending: Array<() => void> = []
    handler = config =>
      new Promise(resolve => {
        pending.push(() =>
          resolve({ data: {}, status: 200, statusText: 'OK', headers: {}, config })
        )
      })

    const first = apiClient.get('/genes/')
    const second = apiClient.get('/curations/')
    await vi.waitFor(() => expect(pending).toHaveLength(2))
    pending[0]?.()
    await first
    expect(logService.clearCorrelationId).not.toHaveBeenCalled()

    pending[1]?.()
    await second
    expect(logService.clearCorrelationId).toHaveBeenCalledTimes(1)
  })
})
