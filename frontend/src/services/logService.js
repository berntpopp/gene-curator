/**
 * Unified Logging Service for Gene Curator
 *
 * Provides centralized logging with privacy protection for genetic/medical data.
 * Singleton service that integrates with Pinia store for reactive log management.
 *
 * Features:
 * - Automatic sanitization of sensitive data
 * - Configurable log levels
 * - LocalStorage persistence for settings
 * - Optional console echo for development
 * - Request correlation IDs
 * - Performance tracking capabilities
 */

import { sanitizeLogEntry } from '@/utils/logSanitizer'

/**
 * Log levels enum
 * Higher levels indicate more severe issues
 */
export const LogLevel = {
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARN: 'WARN',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL'
}

/**
 * Log level priority mapping for filtering
 * Used to determine if a log should be recorded based on minimum level
 */
const LOG_LEVEL_PRIORITY = {
  [LogLevel.DEBUG]: 0,
  [LogLevel.INFO]: 1,
  [LogLevel.WARN]: 2,
  [LogLevel.ERROR]: 3,
  [LogLevel.CRITICAL]: 4
}

/**
 * LocalStorage keys for configuration persistence
 * All settings are prefixed to avoid conflicts
 */
const STORAGE_KEYS = {
  MAX_ENTRIES: 'gene-curator-log-max-entries',
  LOG_LEVEL: 'gene-curator-log-level',
  CONSOLE_ECHO: 'gene-curator-console-echo'
}

/**
 * LogService - Singleton service for centralized logging
 *
 * Features:
 * - Automatic sanitization of sensitive genetic/medical data
 * - Configurable log levels with filtering
 * - LocalStorage persistence for settings
 * - Optional console echo for development
 * - Request correlation IDs for API tracking
 * - Performance tracking capabilities
 * - Integration with Pinia store for reactive UI
 */
class LogService {
  constructor() {
    this.store = null
    this.consoleEcho = this.loadConsoleEchoFromStorage()
    this.maxEntries = this.loadMaxEntriesFromStorage()
    this.minLogLevel = this.loadLogLevelFromStorage()
    this.correlationId = null
    this.metadata = {}
  }

  /**
   * Initialize the log store (called after Pinia is available)
   *
   * @param {Object} store - The Pinia log store instance
   */
  initStore(store) {
    this.store = store
    this.info('LogService initialized', {
      maxEntries: this.maxEntries,
      minLogLevel: this.minLogLevel,
      consoleEcho: this.consoleEcho
    })
  }

  /**
   * Set request correlation ID for tracking related logs
   *
   * Useful for correlating frontend logs with backend logs for the same request.
   *
   * @param {string} id - Correlation ID (typically from X-Request-ID header)
   */
  setCorrelationId(id) {
    this.correlationId = id
  }

  /**
   * Clear correlation ID
   *
   * Should be called after API request completes to avoid polluting subsequent logs.
   */
  clearCorrelationId() {
    this.correlationId = null
  }

  /**
   * Set global metadata for all logs
   *
   * Metadata is included in every log entry. Use sparingly to avoid bloating logs.
   *
   * @param {Object} metadata - Metadata to include in all logs
   *
   * @example
   * logService.setMetadata({ userId: '123', sessionId: 'abc' })
   */
  setMetadata(metadata) {
    this.metadata = { ...this.metadata, ...metadata }
  }

  /**
   * Clear global metadata
   */
  clearMetadata() {
    this.metadata = {}
  }

  /**
   * Core logging method
   *
   * @private
   * @param {string} level - Log level
   * @param {string} message - Log message
   * @param {any} data - Optional data to log
   */
  _log(level, message, data = null) {
    // Check if log level meets minimum threshold
    if (LOG_LEVEL_PRIORITY[level] < LOG_LEVEL_PRIORITY[this.minLogLevel]) {
      return
    }

    // Sanitize the log entry to protect sensitive data
    const sanitized = sanitizeLogEntry(message, data)

    // Create log entry with full context
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      message: sanitized.message,
      data: sanitized.data,
      correlationId: this.correlationId,
      metadata: this.metadata,
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    // Echo to console if enabled (useful for development)
    if (this.consoleEcho) {
      this._consoleEcho(level, message, data)
    }

    // Add to store if available
    if (this.store) {
      try {
        this.store.addLogEntry(entry, this.maxEntries)
      } catch (error) {
        // Fallback to console if store fails (prevent logging from breaking app)
        console.error('Failed to add log to store:', error)
      }
    }
  }

  /**
   * Echo log to console with appropriate method
   *
   * @private
   * @param {string} level - Log level
   * @param {string} message - Log message
   * @param {any} data - Optional data
   */
  _consoleEcho(level, message, data) {
    const prefix = `[${level}]`
    const args = data ? [prefix, message, data] : [prefix, message]

    switch (level) {
      case LogLevel.DEBUG:
        console.debug(...args)
        break
      case LogLevel.INFO:
        console.info(...args)
        break
      case LogLevel.WARN:
        console.warn(...args)
        break
      case LogLevel.ERROR:
      case LogLevel.CRITICAL:
        console.error(...args)
        break
      default:
        console.log(...args)
    }
  }

  /**
   * Public logging methods
   */

  /**
   * Log debug message (lowest level)
   *
   * Use for detailed diagnostic information. Typically disabled in production.
   *
   * @param {string} message - Log message
   * @param {any} data - Optional data object
   */
  debug(message, data = null) {
    this._log(LogLevel.DEBUG, message, data)
  }

  /**
   * Log info message
   *
   * Use for normal application events (user actions, navigation, etc.)
   *
   * @param {string} message - Log message
   * @param {any} data - Optional data object
   */
  info(message, data = null) {
    this._log(LogLevel.INFO, message, data)
  }

  /**
   * Log warning message
   *
   * Use for unexpected situations that don't prevent normal operation.
   *
   * @param {string} message - Log message
   * @param {any} data - Optional data object
   */
  warn(message, data = null) {
    this._log(LogLevel.WARN, message, data)
  }

  /**
   * Log error message
   *
   * Use for errors that affect specific operations but not overall app stability.
   *
   * @param {string} message - Log message
   * @param {any} data - Optional data object
   */
  error(message, data = null) {
    this._log(LogLevel.ERROR, message, data)
  }

  /**
   * Log critical message (highest level)
   *
   * Use for severe errors that affect app stability or data integrity.
   *
   * @param {string} message - Log message
   * @param {any} data - Optional data object
   */
  critical(message, data = null) {
    this._log(LogLevel.CRITICAL, message, data)
  }

  /**
   * Performance tracking helper
   *
   * Logs operation duration and warns if operation is slow (> 1000ms).
   *
   * @param {string} operation - Operation name
   * @param {number} startTime - Start timestamp from performance.now()
   * @param {Object} data - Additional data
   *
   * @example
   * const startTime = performance.now()
   * // ... operation ...
   * logService.logPerformance('dataLoad', startTime, { rows: 100 })
   */
  logPerformance(operation, startTime, data = null) {
    const duration = window.performance.now() - startTime
    const level = duration > 1000 ? LogLevel.WARN : LogLevel.DEBUG

    this._log(level, `Performance: ${operation}`, {
      ...data,
      duration_ms: Math.round(duration),
      slow: duration > 1000
    })
  }

  /**
   * Log API call
   *
   * Automatically called by API interceptors. Logs errors for status >= 400.
   *
   * @param {string} method - HTTP method (GET, POST, etc.)
   * @param {string} url - API endpoint
   * @param {number} status - Response status code
   * @param {number} duration - Duration in milliseconds
   */
  logApiCall(method, url, status, duration) {
    const level = status >= 400 ? LogLevel.ERROR : LogLevel.DEBUG
    this._log(level, `API ${method} ${url}`, {
      status,
      duration_ms: duration,
      success: status < 400
    })
  }

  /**
   * Configuration methods
   */

  /**
   * Enable or disable console echo
   *
   * @param {boolean} enabled - True to enable console echo
   */
  setConsoleEcho(enabled) {
    this.consoleEcho = enabled
    localStorage.setItem(STORAGE_KEYS.CONSOLE_ECHO, JSON.stringify(enabled))
  }

  /**
   * Set maximum number of log entries to keep
   *
   * @param {number} maxEntries - Maximum entries (must be > 0)
   */
  setMaxEntries(maxEntries) {
    this.maxEntries = maxEntries
    localStorage.setItem(STORAGE_KEYS.MAX_ENTRIES, maxEntries.toString())

    // Trim existing logs if needed
    if (this.store) {
      this.store.trimLogs(maxEntries)
    }
  }

  /**
   * Set minimum log level
   *
   * Logs below this level will be ignored.
   *
   * @param {string} level - Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
   */
  setMinLogLevel(level) {
    if (LOG_LEVEL_PRIORITY[level] !== undefined) {
      this.minLogLevel = level
      localStorage.setItem(STORAGE_KEYS.LOG_LEVEL, level)
    }
  }

  /**
   * Storage loading methods
   * @private
   */

  /**
   * Load console echo setting from LocalStorage
   *
   * @private
   * @returns {boolean} Console echo enabled status
   */
  loadConsoleEchoFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.CONSOLE_ECHO)
      if (stored !== null) {
        return JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load console echo setting:', error)
    }
    // Default: console echo disabled - all logs only appear in UI Log Viewer
    return false
  }

  /**
   * Load max entries setting from LocalStorage
   *
   * @private
   * @returns {number} Maximum log entries
   */
  loadMaxEntriesFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.MAX_ENTRIES)
      if (stored !== null) {
        const parsed = parseInt(stored, 10)
        if (!isNaN(parsed) && parsed > 0) {
          return parsed
        }
      }
    } catch (error) {
      console.error('Failed to load max entries setting:', error)
    }
    // Default: 100 in development, 50 in production
    return import.meta.env.DEV ? 100 : 50
  }

  /**
   * Load log level setting from LocalStorage
   *
   * @private
   * @returns {string} Minimum log level
   */
  loadLogLevelFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.LOG_LEVEL)
      if (stored && LOG_LEVEL_PRIORITY[stored] !== undefined) {
        return stored
      }
    } catch (error) {
      console.error('Failed to load log level setting:', error)
    }
    // Default: DEBUG in development, INFO in production
    return import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO
  }

  /**
   * Clear all logs
   */
  clearLogs() {
    if (this.store) {
      this.store.clearLogs()
    }
  }

  /**
   * Export logs as JSON
   *
   * @returns {Object} Exported logs data with metadata
   */
  exportLogs() {
    if (!this.store) {
      return { logs: [], exportedAt: new Date().toISOString() }
    }

    return {
      exportedAt: new Date().toISOString(),
      environment: import.meta.env.MODE,
      url: window.location.href,
      userAgent: navigator.userAgent,
      configuration: {
        maxEntries: this.maxEntries,
        minLogLevel: this.minLogLevel,
        consoleEcho: this.consoleEcho
      },
      logs: this.store.logs
    }
  }
}

// Create and export singleton instance
export const logService = new LogService()

// Also export as default for convenience
export default logService
