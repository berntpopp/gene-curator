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

/* eslint-disable no-console -- logging layer: the only place console output is allowed */
import { sanitizeLogEntry } from '@/utils/logSanitizer'

/** Minimal view of the Pinia log store this service writes to */
export interface LogStoreLike {
  logs: LogEntry[]
  addLogEntry(entry: LogEntry, maxEntries: number): void
  trimLogs(maxEntries: number): void
  clearLogs(): void
}

export interface LogEntry {
  timestamp: string
  level: LogLevelName
  message: string
  data: unknown
  correlationId: string | null
  metadata: Record<string, unknown>
  url: string
  userAgent: string
}

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
} as const

export type LogLevelName = (typeof LogLevel)[keyof typeof LogLevel]

function isLogLevel(value: string): value is LogLevelName {
  return Object.prototype.hasOwnProperty.call(LOG_LEVEL_PRIORITY, value)
}

/**
 * Log level priority mapping for filtering
 * Used to determine if a log should be recorded based on minimum level
 */
const LOG_LEVEL_PRIORITY: Record<LogLevelName, number> = {
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
  store: LogStoreLike | null = null
  consoleEcho: boolean
  maxEntries: number
  minLogLevel: LogLevelName
  correlationId: string | null = null
  metadata: Record<string, unknown> = {}

  constructor() {
    this.consoleEcho = this.loadConsoleEchoFromStorage()
    this.maxEntries = this.loadMaxEntriesFromStorage()
    this.minLogLevel = this.loadLogLevelFromStorage()
  }

  /**
   * Initialize the log store (called after Pinia is available)
   *
   * @param store - The Pinia log store instance
   */
  initStore(store: LogStoreLike): void {
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
   * @param id - Correlation ID (typically from X-Request-ID header)
   */
  setCorrelationId(id: string): void {
    this.correlationId = id
  }

  /**
   * Clear correlation ID
   *
   * Should be called after API request completes to avoid polluting subsequent logs.
   */
  clearCorrelationId(): void {
    this.correlationId = null
  }

  /**
   * Set global metadata for all logs
   *
   * Metadata is included in every log entry. Use sparingly to avoid bloating logs.
   *
   * @param metadata - Metadata to include in all logs
   *
   * @example
   * logService.setMetadata({ userId: '123', sessionId: 'abc' })
   */
  setMetadata(metadata: Record<string, unknown>): void {
    this.metadata = { ...this.metadata, ...metadata }
  }

  /**
   * Clear global metadata
   */
  clearMetadata(): void {
    this.metadata = {}
  }

  /**
   * Core logging method
   *
   * @private
   * @param level - Log level
   * @param message - Log message
   * @param data - Optional data to log
   */
  _log(level: LogLevelName, message: string, data: unknown = null): void {
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
   * @param level - Log level
   * @param message - Log message
   * @param data - Optional data
   */
  _consoleEcho(level: LogLevelName, message: string, data: unknown): void {
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
   * @param message - Log message
   * @param data - Optional data object
   */
  debug(message: string, data: unknown = null): void {
    this._log(LogLevel.DEBUG, message, data)
  }

  /**
   * Log info message
   *
   * Use for normal application events (user actions, navigation, etc.)
   *
   * @param message - Log message
   * @param data - Optional data object
   */
  info(message: string, data: unknown = null): void {
    this._log(LogLevel.INFO, message, data)
  }

  /**
   * Log warning message
   *
   * Use for unexpected situations that don't prevent normal operation.
   *
   * @param message - Log message
   * @param data - Optional data object
   */
  warn(message: string, data: unknown = null): void {
    this._log(LogLevel.WARN, message, data)
  }

  /**
   * Log error message
   *
   * Use for errors that affect specific operations but not overall app stability.
   *
   * @param message - Log message
   * @param data - Optional data object
   */
  error(message: string, data: unknown = null): void {
    this._log(LogLevel.ERROR, message, data)
  }

  /**
   * Log critical message (highest level)
   *
   * Use for severe errors that affect app stability or data integrity.
   *
   * @param message - Log message
   * @param data - Optional data object
   */
  critical(message: string, data: unknown = null): void {
    this._log(LogLevel.CRITICAL, message, data)
  }

  /**
   * Performance tracking helper
   *
   * Logs operation duration and warns if operation is slow (> 1000ms).
   *
   * @param operation - Operation name
   * @param startTime - Start timestamp from performance.now()
   * @param data - Additional data
   *
   * @example
   * const startTime = performance.now()
   * // ... operation ...
   * logService.logPerformance('dataLoad', startTime, { rows: 100 })
   */
  logPerformance(
    operation: string,
    startTime: number,
    data: Record<string, unknown> | null = null
  ): void {
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
   * @param method - HTTP method (GET, POST, etc.)
   * @param url - API endpoint
   * @param status - Response status code
   * @param duration - Duration in milliseconds
   */
  logApiCall(method: string, url: string, status: number, duration: number): void {
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
   * @param enabled - True to enable console echo
   */
  setConsoleEcho(enabled: boolean): void {
    this.consoleEcho = enabled
    localStorage.setItem(STORAGE_KEYS.CONSOLE_ECHO, JSON.stringify(enabled))
  }

  /**
   * Set maximum number of log entries to keep
   *
   * @param maxEntries - Maximum entries (must be > 0)
   */
  setMaxEntries(maxEntries: number): void {
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
   * @param level - Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
   */
  setMinLogLevel(level: string): void {
    if (isLogLevel(level)) {
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
   * @returns Console echo enabled status
   */
  loadConsoleEchoFromStorage(): boolean {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.CONSOLE_ECHO)
      if (stored !== null) {
        return JSON.parse(stored) as boolean
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
   * @returns Maximum log entries
   */
  loadMaxEntriesFromStorage(): number {
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
   * @returns Minimum log level
   */
  loadLogLevelFromStorage(): LogLevelName {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.LOG_LEVEL)
      if (stored && isLogLevel(stored)) {
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
  clearLogs(): void {
    if (this.store) {
      this.store.clearLogs()
    }
  }

  /**
   * Export logs as JSON
   *
   * @returns Exported logs data with metadata
   */
  exportLogs(): Record<string, unknown> {
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
