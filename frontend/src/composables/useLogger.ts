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
 * const logger = useLogger()
 * logger.info('Component mounted')
 * logger.error('Something went wrong', { error: e })
 */

import { getCurrentInstance } from 'vue'
import { logService } from '@/services/logService'

export type LogData = Record<string, unknown>

export interface ScopedLogger {
  debug: (message: string, data?: LogData) => void
  info: (message: string, data?: LogData) => void
  warn: (message: string, data?: LogData) => void
  error: (message: string, data?: LogData) => void
  critical: (message: string, data?: LogData) => void
  logPerformance: (operation: string, startTime: number, data?: LogData) => void
}

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
 * @param componentName - Optional component name override
 * @returns Logger object with scoped methods
 *
 * @example
 * // With performance tracking
 * const logger = useLogger()
 * const startTime = performance.now()
 * // ... operation ...
 * logger.logPerformance('dataLoad', startTime, { rows: 100 })
 */
export function useLogger(componentName: string | null = null): ScopedLogger {
  const instance = getCurrentInstance()
  const name = componentName || instance?.type?.name || 'Unknown'

  // FIX #4: Don't mutate global state - return scoped logger functions
  // Each component gets its own logger functions with built-in component context
  // This prevents memory leak where component metadata pollutes global logger
  // No onUnmounted needed - pure function, no cleanup required.

  return {
    debug: (message, data) =>
      logService.debug(message, {
        ...data,
        component: name
      }),

    info: (message, data) =>
      logService.info(message, {
        ...data,
        component: name
      }),

    warn: (message, data) =>
      logService.warn(message, {
        ...data,
        component: name
      }),

    error: (message, data) =>
      logService.error(message, {
        ...data,
        component: name
      }),

    critical: (message, data) =>
      logService.critical(message, {
        ...data,
        component: name
      }),

    logPerformance: (operation, startTime, data) =>
      logService.logPerformance(operation, startTime, {
        ...data,
        component: name
      })
  }
}

/**
 * Helper to get logger for Options API components
 *
 * @deprecated Use useLogger() in Composition API or this.$logger in Options API
 * @param componentInstance - Component instance (this)
 * @returns Logger object
 */
export function getLogger(componentInstance: {
  $options?: { name?: string }
  type?: { name?: string }
}): ScopedLogger {
  const name = componentInstance?.$options?.name || componentInstance?.type?.name || 'Unknown'
  return useLogger(name)
}
