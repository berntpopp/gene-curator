import axios from 'axios'
import { logService } from '@/services/logService'
import { generateUUID } from '@/utils/uuidPolyfill'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

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
  config => {
    // Add auth token
    const token = localStorage.getItem('access_token')
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
  error => {
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

    // Clear correlation ID after successful response
    logService.clearCorrelationId()

    return response
  },
  async error => {
    const originalRequest = error.config

    // Calculate duration for error response
    const duration = error.config?.metadata?.startTime
      ? performance.now() - error.config.metadata.startTime
      : 0

    const status = error.response?.status || 0

    // Handle 401 (Unauthorized) - attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          logService.debug('Attempting token refresh', { originalUrl: originalRequest.url })

          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          })

          const { access_token } = response.data
          localStorage.setItem('access_token', access_token)

          logService.info('Token refreshed successfully')

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        logService.warn('Token refresh failed, redirecting to login', {
          error: refreshError.message
        })

        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'

        // Clear correlation ID before rejecting
        logService.clearCorrelationId()

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

    // Log detailed error information
    logService.error('API Error', {
      method: error.config?.method,
      url: error.config?.url,
      status,
      error: error.message,
      response: error.response?.data
    })

    // Clear correlation ID after error
    logService.clearCorrelationId()

    return Promise.reject(error)
  }
)

export default apiClient
