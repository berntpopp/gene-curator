/**
 * Composable for Component-Level Logging
 *
 * FIX #4: Return scoped logger functions instead of mutating global metadata
 *
 * This prevents memory leak where component metadata pollutes global logger state.
 * Each component gets its own logger functions with built-in component context.
 *
 * @example
 * // In Composition API components
 * import { useLogger } from '@/composables/useLogger'
 *
 * export default {
 *   setup() {
 *     const logger = useLogger()
 *
 *     logger.info('Component mounted')
 *     logger.error('Something went wrong', { error: e })
 *
 *     return { ... }
 *   }
 * }
 */

import { getCurrentInstance } from 'vue'
import { logService } from '@/services/logService'

/**
 * useLogger composable
 *
 * FIX #4: Returns scoped logger functions with component context.
 * Does NOT mutate global logService metadata (prevents memory leak).
 *
 * Each call to useLogger() returns a set of logger functions that automatically
 * include the component name in the log data. This approach ensures that:
 * 1. Component context is preserved in logs
 * 2. No global state pollution
 * 3. No memory leaks from unmounted components
 * 4. Pure function behavior (no side effects)
 *
 * @param {string} componentName - Optional component name override
 * @returns {Object} Logger object with scoped methods
 *
 * @example
 * // Basic usage
 * const logger = useLogger()
 * logger.info('User clicked button')
 *
 * @example
 * // With custom component name
 * const logger = useLogger('MyCustomComponent')
 * logger.debug('Processing data', { rows: 100 })
 *
 * @example
 * // With performance tracking
 * const logger = useLogger()
 * const startTime = performance.now()
 * // ... operation ...
 * logger.logPerformance('dataLoad', startTime, { rows: 100 })
 */
export function useLogger(componentName = null) {
  const instance = getCurrentInstance()
  const name = componentName || instance?.type?.name || 'Unknown'

  // FIX #4: Don't mutate global state - return scoped logger functions
  // Each component gets its own logger functions with built-in component context
  // This prevents memory leak where component metadata pollutes global logger

  return {
    /**
     * Log debug message
     *
     * @param {string} message - Log message
     * @param {Object} data - Optional data object
     */
    debug: (message, data) =>
      logService.debug(message, {
        ...data,
        component: name
      }),

    /**
     * Log info message
     *
     * @param {string} message - Log message
     * @param {Object} data - Optional data object
     */
    info: (message, data) =>
      logService.info(message, {
        ...data,
        component: name
      }),

    /**
     * Log warning message
     *
     * @param {string} message - Log message
     * @param {Object} data - Optional data object
     */
    warn: (message, data) =>
      logService.warn(message, {
        ...data,
        component: name
      }),

    /**
     * Log error message
     *
     * @param {string} message - Log message
     * @param {Object} data - Optional data object
     */
    error: (message, data) =>
      logService.error(message, {
        ...data,
        component: name
      }),

    /**
     * Log critical message
     *
     * @param {string} message - Log message
     * @param {Object} data - Optional data object
     */
    critical: (message, data) =>
      logService.critical(message, {
        ...data,
        component: name
      }),

    /**
     * Log performance metrics
     *
     * @param {string} operation - Operation name
     * @param {number} startTime - Start timestamp from performance.now()
     * @param {Object} data - Additional data
     */
    logPerformance: (operation, startTime, data) =>
      logService.logPerformance(operation, startTime, {
        ...data,
        component: name
      })
  }

  // FIX #4: No onUnmounted needed - pure function, no global mutation!
  // Unlike the buggy version that mutated global metadata and required cleanup,
  // this version is pure and requires no cleanup on unmount.
}

/**
 * Helper to get logger for Options API components
 *
 * @deprecated Use useLogger() in Composition API or this.$logger in Options API
 * @param {Object} componentInstance - Component instance (this)
 * @returns {Object} Logger object
 */
export function getLogger(componentInstance) {
  const name = componentInstance?.$options?.name || componentInstance?.type?.name || 'Unknown'
  return useLogger(name)
}
