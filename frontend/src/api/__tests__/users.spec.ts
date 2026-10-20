import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'

type Handler = (config: InternalAxiosRequestConfig) => Promise<AxiosResponse>

let handler: Handler = () => Promise.reject(new Error('no handler set'))

// users.ts creates its own axios instance from the global defaults, so the stub
// adapter must be installed before the module is imported
axios.defaults.adapter = config => handler(config)
const { usersApi } = await import('../users')

function ok(config: InternalAxiosRequestConfig, data: unknown): Promise<AxiosResponse> {
  return Promise.resolve({ data, status: 200, statusText: 'OK', headers: {}, config })
}

function fail(config: InternalAxiosRequestConfig, status: number): Promise<never> {
  return Promise.reject(
    new AxiosError('request failed', 'ERR_BAD_REQUEST', config, null, {
      data: {},
      status,
      statusText: '',
      headers: {},
      config
    })
  )
}

describe('usersApi', () => {
  let originalLocation: Location

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    originalLocation = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: 'http://localhost/admin/users' }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
  })

  it('sends the stored bearer token and returns the list payload', async () => {
    localStorage.setItem('access_token', 'tok')
    let sent: InternalAxiosRequestConfig | undefined
    handler = config => {
      sent = config
      return ok(config, [{ id: 'u1' }])
    }

    await expect(usersApi.getUsers({ skip: 0 })).resolves.toEqual([{ id: 'u1' }])

    expect(sent?.headers.Authorization).toBe('Bearer tok')
    expect(sent?.url).toBe('/')
    expect(sent?.params).toEqual({ skip: 0 })
  })

  it('searchUsers sends the query as q alongside extra params', async () => {
    let sent: InternalAxiosRequestConfig | undefined
    handler = config => {
      sent = config
      return ok(config, [])
    }

    await usersApi.searchUsers('ada', { limit: 3 })

    expect(sent?.url).toBe('/search')
    expect(sent?.params).toEqual({ q: 'ada', limit: 3 })
  })

  it('sends the update body for activate-style and password endpoints', async () => {
    const seen: { url?: string; data?: unknown; method?: string }[] = []
    handler = config => {
      seen.push({ url: config.url, data: config.data, method: config.method })
      return ok(config, {})
    }

    await usersApi.updateUserPassword('u1', 'secret')
    await usersApi.activateUser('u1')

    expect(seen[0]).toMatchObject({ url: '/u1/password', method: 'put' })
    expect(JSON.parse(String(seen[0]?.data))).toEqual({ new_password: 'secret' })
    expect(seen[1]).toMatchObject({ url: '/u1/activate', method: 'put' })
  })

  it('covers the remaining user endpoints with the right verbs and paths', async () => {
    const seen: string[] = []
    handler = config => {
      seen.push(`${String(config.method)} ${String(config.url)}`)
      return ok(config, {})
    }

    await usersApi.getUserStatistics()
    await usersApi.createUser({ email: 'a@b.c' } as never)
    await usersApi.updateUser('u5', { name: 'Ada' } as never)
    await usersApi.deactivateUser('u5')

    expect(seen).toEqual(['get /statistics', 'post /', 'put /u5', 'put /u5/deactivate'])
  })

  it('refreshes an expired token and retries the failed request', async () => {
    localStorage.setItem('access_token', 'expired')
    localStorage.setItem('refresh_token', 'r1')
    const refreshSpy = vi
      .spyOn(axios, 'post')
      .mockResolvedValue({ data: { access_token: 'fresh' } } as AxiosResponse)
    handler = config =>
      config.headers.Authorization === 'Bearer fresh' ? ok(config, { id: 'u2' }) : fail(config, 401)

    await expect(usersApi.getUser('u2')).resolves.toEqual({ id: 'u2' })

    expect(refreshSpy).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/auth\/refresh$/), {
      refresh_token: 'r1'
    })
    expect(localStorage.getItem('access_token')).toBe('fresh')
  })

  it('clears tokens and redirects to login when the refresh fails', async () => {
    localStorage.setItem('access_token', 'expired')
    localStorage.setItem('refresh_token', 'dead')
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh failed'))
    handler = config => fail(config, 401)

    await expect(usersApi.deleteUser('u3')).rejects.toMatchObject({ response: { status: 401 } })

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('leaves a 401 untouched when there is no refresh token', async () => {
    const refreshSpy = vi.spyOn(axios, 'post')
    handler = config => fail(config, 401)

    await expect(usersApi.getUserActivity('u4')).rejects.toMatchObject({
      response: { status: 401 }
    })

    expect(refreshSpy).not.toHaveBeenCalled()
    expect(window.location.href).toBe('http://localhost/admin/users')
  })
})
