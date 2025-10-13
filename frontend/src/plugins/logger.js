/**
 * Vue Plugin for Global Logger Access
 *
 * FIX #7: Initialize store immediately during plugin install (not in mixin)
 *
 * Makes logger available as $logger in all components via Vue's global properties.
 * Integrates with Vue's error and warning handlers for automatic error logging.
 *
 * Features:
 * - Global $logger property available in all components
 * - Automatic error logging via Vue error handler
 * - Automatic warning logging in development
 * - Store initialization during plugin install (prevents race conditions)
 */

import { logService } from '@/services/logService'
import { useLogStore } from '@/stores/logStore'

/**
 * Logger Plugin for Vue 3
 *
 * Installs the logging system into the Vue application:
 * 1. Makes $logger available globally
 * 2. Initializes Pinia log store
 * 3. Sets up error/warning handlers
 *
 * @example
 * // In main.js
 * import loggerPlugin from '@/plugins/logger'
 * app.use(loggerPlugin)
 *
 * // In components
 * this.$logger.info('Message', { data: 'value' })
 */
export default {
  /**
   * Install the logger plugin
   *
   * FIX #7: Initialize log store immediately during install to prevent
   * race condition where multiple components try to initialize simultaneously.
   *
   * @param {App} app - Vue application instance
   */
  install(app) {
    // Make logger available globally as $logger
    app.config.globalProperties.$logger = logService

    // FIX #7: Initialize log store immediately during install
    // This prevents race condition where multiple components try to initialize simultaneously
    try {
      // Try to get Pinia from app config first (Vue 3.3+)
      const pinia = app.config.globalProperties.$pinia
      if (pinia) {
        const logStore = useLogStore(pinia)
        logService.initStore(logStore)
      } else {
        // Fallback: try to get store from context (older Vue 3 versions)
        try {
          const logStore = useLogStore()
          logService.initStore(logStore)
        } catch (error) {
          console.warn('Could not initialize log store during plugin install:', error)
          console.warn('Make sure Pinia is installed before the logger plugin')
        }
      }
    } catch (error) {
      console.error('Failed to initialize logger plugin:', error)
    }

    // Add global error handler for uncaught errors
    app.config.errorHandler = (err, instance, info) => {
      logService.critical('Uncaught Vue error', {
        error: err.message,
        stack: err.stack,
        component: instance?.$options?.name || instance?.type?.name || 'Unknown',
        info
      })

      // Re-throw error for dev tools in development
      if (import.meta.env.DEV) {
        console.error('Vue error:', err)
      }
    }

    // Add global warning handler (development only)
    if (import.meta.env.DEV) {
      app.config.warnHandler = (msg, instance, trace) => {
        logService.warn('Vue warning', {
          message: msg,
          component: instance?.$options?.name || instance?.type?.name || 'Unknown',
          trace
        })
      }
    }

    // Log successful installation
    logService.debug('Logger plugin installed', {
      environment: import.meta.env.MODE,
      dev: import.meta.env.DEV
    })
  }
}
