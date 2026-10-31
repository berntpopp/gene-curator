import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { logService } from '@/services/logService'
import { generateUUID } from '@/utils/uuidPolyfill'
import type { Schema } from '@/types/api'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: number }
    _retry?: boolean
    _refreshFailed?: boolean
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8051'

/** Credential endpoints: a 401 here is the real answer (wrong password), never an expired session. */
const NO_REFRESH_URL = /^\/?auth\/(login|register|refresh)\b/

/** Shared in-flight refresh so concurrent 401s trigger one /auth/refresh (tokens rotate). */
let refreshInFlight: Promise<string> | null = null

function refreshTokens(refreshToken: string): Promise<string> {
  refreshInFlight ??= axios
    .post<Schema<'Token'>>(`${API_BASE_URL}/api/v1/auth/refresh`, { refresh_token: refreshToken })
    .then(({ data }) => {
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      return data.access_token
    })
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

/** True for a JWT whose exp is in the past; opaque or malformed tokens count as unknown (false). */
export function isExpired(token: string): boolean {
  try {
    // JWT segments are base64url; atob only reads standard base64
    const payload = (token.split('.')[1] ?? '').replace(/-/g, '+').replace(/_/g, '/')
    const exp = (JSON.parse(atob(payload)) as { exp?: number }).exp
    return typeof exp === 'number' && exp * 1000 <= Date.now()
  } catch {
    return false
  }
}

/** Clear the shared correlation id only if no newer request has replaced it. */
function clearCorrelationIdFor(requestId: unknown): void {
  if (logService.correlationId === requestId) logService.clearCorrelationId()
}

/** The only fields worth logging from an error body (it may echo user input). */
function errorDetail(data: unknown): string | undefined {
  const detail = (data as { detail?: unknown } | null | undefined)?.detail
  if (typeof detail === 'string') return detail
  const first = Array.isArray(detail)
    ? (detail[0] as { msg?: unknown } | undefined)?.msg
    : undefined
  return typeof first === 'string' ? first : undefined
}

// Create axios instance
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token and logging
apiClient.interceptors.request.use(
  async config => {
    // Add auth token. An expired one is refreshed first (one shared refresh), so a full
    // reload does not fire requests the API is certain to answer with 401.
    let token = localStorage.getItem('access_token')
    const refreshToken = localStorage.getItem('refresh_token')
    if (token && refreshToken && isExpired(token) && !NO_REFRESH_URL.test(config.url ?? '')) {
      // the 401 path handles failure, without sending a refused or expired refresh again (B21)
      const fresh = isExpired(refreshToken)
        ? null
        : await refreshTokens(refreshToken).catch(() => null)
      config._refreshFailed = fresh === null
      token = fresh ?? token
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // FIX #6: Use UUID polyfill for browser compatibility
    const requestId = config.headers['X-Request-ID'] || generateUUID()
    config.headers['X-Request-ID'] = requestId

    // Set correlation ID in logger for request tracking
    logService.setCorrelationId(requestId)

    // Store start time for performance tracking
    config.metadata = { startTime: performance.now() }

    // Log request (DEBUG level for non-intrusive logging)
    logService.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
      method: config.method,
      url: config.url,
      requestId
    })

    return config
  },
  (error: AxiosError) => {
    logService.error('API Request Error', { error: error.message })
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh and logging
apiClient.interceptors.response.use(
  response => {
    // Calculate duration and log successful response
    const duration = response.config.metadata?.startTime
      ? performance.now() - response.config.metadata.startTime
      : 0

    logService.logApiCall(
      response.config.method?.toUpperCase() || 'UNKNOWN',
      response.config.url || 'unknown',
      response.status,
      duration
    )

    clearCorrelationIdFor(response.config.headers['X-Request-ID'])

    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig

    // Calculate duration for error response
    const duration = error.config?.metadata?.startTime
      ? performance.now() - error.config.metadata.startTime
      : 0

    const status = error.response?.status || 0

    // Handle 401 (Unauthorized) - attempt token refresh
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !NO_REFRESH_URL.test(originalRequest.url ?? '')
    ) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          if (originalRequest._refreshFailed) throw new Error('Refresh token refused')
          logService.debug('Attempting token refresh', { originalUrl: originalRequest.url })

          const access_token = await refreshTokens(refreshToken)

          logService.info('Token refreshed successfully')

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient(originalRequest)
        }
      } catch (refreshError: unknown) {
        // Refresh failed, redirect to login
        logService.warn('Token refresh failed, redirecting to login', {
          error: refreshError instanceof Error ? refreshError.message : undefined
        })

        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        if (window.location.pathname !== '/login') {
          const here = window.location.pathname + window.location.search
          window.location.href = `/login?reason=expired&redirect=${encodeURIComponent(here)}`
        }

        clearCorrelationIdFor(originalRequest.headers['X-Request-ID'])

        return Promise.reject(refreshError)
      }
    }

    // Log API error
    logService.logApiCall(
      error.config?.method?.toUpperCase() || 'UNKNOWN',
      error.config?.url || 'unknown',
      status,
      duration
    )

    // A request aborted on purpose (a stale palette search) is not an error; a 401 is the
    // expected answer for a signed-out visitor or a dropped session (MUI-19), so a warning
    if (!axios.isCancel(error)) {
      logService[status === 401 ? 'warn' : 'error'](
        status === 401 ? 'API unauthorized' : 'API Error',
        {
          method: error.config?.method,
          url: error.config?.url,
          status,
          error: error.message,
          detail: errorDetail(error.response?.data)
        }
      )
    }

    clearCorrelationIdFor(originalRequest?.headers?.['X-Request-ID'])

    return Promise.reject(error)
  }
)

export default apiClient
