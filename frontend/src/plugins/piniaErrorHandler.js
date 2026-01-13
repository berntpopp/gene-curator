/**
 * Pinia Error Handler Plugin
 *
 * Provides centralized error handling for all Pinia store actions.
 * Implements consistent error logging and notification patterns.
 *
 * Features:
 * - Automatic error logging with structured context
 * - User-friendly error notifications
 * - Error categorization (network, validation, auth, unknown)
 * - Non-blocking error handling (doesn't swallow errors)
 *
 * @module plugins/piniaErrorHandler
 * @see plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */

import { logService } from '@/services/logService'

/**
 * Error categories for consistent handling
 */
const ERROR_CATEGORIES = {
  NETWORK: 'network',
  VALIDATION: 'validation',
  AUTH: 'auth',
  NOT_FOUND: 'not_found',
  UNKNOWN: 'unknown'
}

/**
 * Categorize an error based on its properties
 *
 * @param {Error} error - The error to categorize
 * @returns {string} Error category
 */
function categorizeError(error) {
  // Network errors
  if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
    return ERROR_CATEGORIES.NETWORK
  }

  // HTTP status-based categorization
  const status = error.response?.status
  if (status) {
    if (status === 401 || status === 403) return ERROR_CATEGORIES.AUTH
    if (status === 404) return ERROR_CATEGORIES.NOT_FOUND
    if (status >= 400 && status < 500) return ERROR_CATEGORIES.VALIDATION
  }

  // Validation errors (from API)
  if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
    return ERROR_CATEGORIES.VALIDATION
  }

  return ERROR_CATEGORIES.UNKNOWN
}

/**
 * Get user-friendly message for an error category
 *
 * @param {string} category - Error category
 * @param {Error} error - Original error
 * @returns {string} User-friendly message
 */
function getUserMessage(category, error) {
  const messages = {
    [ERROR_CATEGORIES.NETWORK]: 'Unable to connect to the server. Please check your connection.',
    [ERROR_CATEGORIES.AUTH]: 'You are not authorized to perform this action.',
    [ERROR_CATEGORIES.NOT_FOUND]: 'The requested resource was not found.',
    [ERROR_CATEGORIES.VALIDATION]:
      error.response?.data?.detail?.[0]?.msg ||
      error.response?.data?.message ||
      'Please check your input and try again.',
    [ERROR_CATEGORIES.UNKNOWN]: 'An unexpected error occurred. Please try again.'
  }

  return messages[category] || messages[ERROR_CATEGORIES.UNKNOWN]
}

/**
 * Pinia plugin that adds error handling to all store actions
 *
 * @param {Object} context - Pinia plugin context
 * @param {Object} context.store - The store instance
 *
 * @example
 * // In main.js or store setup
 * import { createPinia } from 'pinia'
 * import { piniaErrorHandlerPlugin } from '@/plugins/piniaErrorHandler'
 *
 * const pinia = createPinia()
 * pinia.use(piniaErrorHandlerPlugin)
 */
export function piniaErrorHandlerPlugin({ store }) {
  // Subscribe to all store actions
  store.$onAction(({ name, store: actionStore, args, after, onError }) => {
    const startTime = Date.now()

    // After successful action
    after(result => {
      const duration = Date.now() - startTime

      // Log slow actions (> 2s) as warnings
      if (duration > 2000) {
        logService.warn(`Slow action: ${actionStore.$id}.${name}`, {
          store: actionStore.$id,
          action: name,
          duration_ms: duration
        })
      }

      return result
    })

    // On action error
    onError(error => {
      const duration = Date.now() - startTime
      const category = categorizeError(error)
      const userMessage = getUserMessage(category, error)

      // Log the error with context
      logService.error(`Store action failed: ${actionStore.$id}.${name}`, {
        store: actionStore.$id,
        action: name,
        category,
        error_message: error.message,
        status: error.response?.status,
        duration_ms: duration,
        args_count: args.length
      })

      // Attach metadata to error for downstream handling
      error._piniaContext = {
        store: actionStore.$id,
        action: name,
        category,
        userMessage,
        duration
      }

      // Don't swallow the error - let it propagate
      // Components can use error._piniaContext for display
    })
  })
}

/**
 * Helper to extract user-friendly message from error
 *
 * @param {Error} error - Error with optional _piniaContext
 * @returns {string} User-friendly message
 *
 * @example
 * try {
 *   await schemasStore.fetchSchemas()
 * } catch (error) {
 *   showError(getErrorMessage(error))
 * }
 */
export function getErrorMessage(error) {
  if (error._piniaContext?.userMessage) {
    return error._piniaContext.userMessage
  }

  // Fallback: extract from error directly
  if (error.response?.data?.message) {
    return error.response.data.message
  }

  if (error.response?.data?.detail && typeof error.response.data.detail === 'string') {
    return error.response.data.detail
  }

  return error.message || 'An unexpected error occurred'
}

/**
 * Check if error is of a specific category
 *
 * @param {Error} error - Error to check
 * @param {string} category - Category to check against
 * @returns {boolean}
 */
export function isErrorCategory(error, category) {
  return error._piniaContext?.category === category
}

export { ERROR_CATEGORIES }

export default {
  piniaErrorHandlerPlugin,
  getErrorMessage,
  isErrorCategory,
  ERROR_CATEGORIES
}
