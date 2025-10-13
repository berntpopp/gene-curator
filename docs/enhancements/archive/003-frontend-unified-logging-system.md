# Enhancement: Frontend Unified Logging System

**Priority**: High
**Complexity**: Medium
**Estimated Effort**: 5-7 hours
**Reference**: kidney-genetics-db frontend logging system

## Overview

Implement a comprehensive, production-grade logging system for Gene Curator's Vue 3 frontend. This system provides structured logging with privacy protection, log viewer UI, export capabilities, and seamless integration with backend request correlation.

**Why This Makes Development Easier:**
- **In-Browser Log Viewer**: See all frontend logs without opening browser console
- **Privacy Protection**: Automatic sanitization of sensitive genetic/medical data
- **Request Correlation**: Match frontend logs to backend logs via request_id
- **Performance Tracking**: Automatic timing for API calls and operations
- **Export Logs**: Download logs for bug reports or debugging
- **Persistent Settings**: Log level and preferences saved in LocalStorage

## Current State

- `console.log()` used inconsistently across components
- No structured logging or context
- No privacy protection for sensitive data
- No in-browser log viewer
- Difficult to debug production issues
- No request correlation with backend

## Proposed Architecture

### Component Overview

```
frontend/src/
├── services/
│   └── logService.js           # Singleton logging service
├── utils/
│   └── logSanitizer.js         # Privacy protection utility
├── stores/
│   └── logStore.js             # Pinia store for log management
├── components/
│   └── logging/
│       ├── LogViewer.vue       # Main log viewer UI
│       ├── LogEntry.vue        # Individual log entry component
│       ├── LogFilters.vue      # Filter controls
│       └── LogSettings.vue     # Settings dialog
├── plugins/
│   └── logger.js               # Vue plugin for global logger
└── composables/
    └── useLogger.js            # Composable for component logging
```

### Key Features

1. **Singleton Service**: Centralized logging with automatic sanitization
2. **Privacy Protection**: Automatic redaction of sensitive data (emails, tokens, genetic variants)
3. **Pinia Store**: Reactive log management with filtering and search
4. **Log Viewer UI**: In-browser log viewer with real-time updates
5. **Request Correlation**: Automatic correlation ID matching backend requests
6. **LocalStorage**: Persistent settings (log level, max entries, console echo)
7. **Export**: Download logs as JSON or CSV for bug reports
8. **Performance Tracking**: Automatic API call timing

## Detailed Implementation

### 1. Log Service (`frontend/src/services/logService.js`)

```javascript
/**
 * Unified Logging Service for Gene Curator
 *
 * Provides centralized logging with privacy protection for genetic/medical data
 */

import { sanitizeLogEntry } from '@/utils/logSanitizer'

/**
 * Log levels enum
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
 * - Configurable log levels
 * - LocalStorage persistence for settings
 * - Optional console echo for development
 * - Request correlation IDs
 * - Performance tracking capabilities
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
   * @param {Object} store - The Pinia log store
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
   * @param {string} id - Correlation ID
   */
  setCorrelationId(id) {
    this.correlationId = id
  }

  /**
   * Clear correlation ID
   */
  clearCorrelationId() {
    this.correlationId = null
  }

  /**
   * Set global metadata for all logs
   * @param {Object} metadata - Metadata to include in all logs
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

    // Create log entry
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

    // Echo to console if enabled (development)
    if (this.consoleEcho) {
      this._consoleEcho(level, message, data)
    }

    // Add to store if available
    if (this.store) {
      try {
        this.store.addLogEntry(entry, this.maxEntries)
      } catch (error) {
        // Fallback to console if store fails
        console.error('Failed to add log to store:', error)
      }
    }
  }

  /**
   * Echo log to console with appropriate method
   * @private
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
  debug(message, data = null) {
    this._log(LogLevel.DEBUG, message, data)
  }

  info(message, data = null) {
    this._log(LogLevel.INFO, message, data)
  }

  warn(message, data = null) {
    this._log(LogLevel.WARN, message, data)
  }

  error(message, data = null) {
    this._log(LogLevel.ERROR, message, data)
  }

  critical(message, data = null) {
    this._log(LogLevel.CRITICAL, message, data)
  }

  /**
   * Performance tracking helper
   * @param {string} operation - Operation name
   * @param {number} startTime - Start timestamp from performance.now()
   * @param {Object} data - Additional data
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
   * @param {string} method - HTTP method
   * @param {string} url - API endpoint
   * @param {number} status - Response status
   * @param {number} duration - Duration in ms
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
  setConsoleEcho(enabled) {
    this.consoleEcho = enabled
    localStorage.setItem(STORAGE_KEYS.CONSOLE_ECHO, JSON.stringify(enabled))
  }

  setMaxEntries(maxEntries) {
    this.maxEntries = maxEntries
    localStorage.setItem(STORAGE_KEYS.MAX_ENTRIES, maxEntries.toString())

    // Trim existing logs if needed
    if (this.store) {
      this.store.trimLogs(maxEntries)
    }
  }

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
  loadConsoleEchoFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.CONSOLE_ECHO)
      if (stored !== null) {
        return JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load console echo setting:', error)
    }
    // Default: false in development, true in production (for debugging)
    return import.meta.env.DEV
  }

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
   * @returns {Object} Exported logs data
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
```

### 2. Log Sanitizer (`frontend/src/utils/logSanitizer.js`)

```javascript
/**
 * Log Sanitization Utility for Gene Curator
 *
 * Provides privacy protection for sensitive genetic and medical data in logs
 */

/**
 * Sensitive keys that should be redacted from logs
 */
const SENSITIVE_KEYS = [
  // Authentication and security
  'token',
  'accesstoken',
  'authtoken',
  'jwt',
  'password',
  'passwd',
  'pwd',
  'key',
  'apikey',
  'api_key',
  'secretkey',
  'secret_key',
  'privatekey',
  'private_key',
  'secret',
  'apisecret',
  'api_secret',
  'authorization',
  'bearer',
  'credential',
  'credentials',

  // User identifiers (if needed for privacy)
  'email',
  'emailaddress',
  'phone',
  'phonenumber',

  // Genetic data (optional - depends on privacy requirements)
  'variant',
  'variants',
  'mutation',
  'mutations',
  'hgvs',
  'hgvs_notation'
]

/**
 * Regex patterns for sensitive values
 */
const SENSITIVE_VALUE_PATTERNS = [
  // Email patterns
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,

  // Phone patterns (international formats)
  /\b(?:\+?[1-9]\d{0,2}[\s.-]?)?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b/g,

  // JWT token patterns
  /\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b/g,

  // API key patterns (common formats)
  /\b[A-Za-z0-9]{32,}\b/g,

  // HGVS notation for genetic variants (DNA)
  /\bc\.\d+[ACGT]>[ACGT]\b/g,
  /\bc\.\d+_\d+del[ACGT]*\b/g,
  /\bc\.\d+_\d+ins[ACGT]+\b/g,
  /\bc\.\d+_\d+dup[ACGT]*\b/g,

  // HGVS notation for genetic variants (Protein)
  /\bp\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}\b/g,
  /\bp\.[A-Z][a-z]{2}\d+\*/g,
  /\bp\.[A-Z][a-z]{2}\d+fs/g,

  // Genomic coordinates
  /\bchr\d{1,2}:\d+-\d+\b/g,
  /\bchrX:\d+-\d+\b/g,
  /\bchrY:\d+-\d+\b/g
]

/**
 * Sanitizes an object for logging by redacting sensitive information
 *
 * @param {any} obj - The object to sanitize
 * @param {number} maxDepth - Maximum recursion depth
 * @returns {any} - Sanitized copy of the object
 */
export function sanitizeForLogging(obj, maxDepth = 5) {
  // Handle max depth
  if (maxDepth <= 0) {
    return '[MAX_DEPTH_EXCEEDED]'
  }

  // Handle null/undefined
  if (obj === null || obj === undefined) {
    return obj
  }

  // Handle primitives
  if (typeof obj !== 'object') {
    return sanitizeValue(obj)
  }

  // Handle arrays
  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeForLogging(item, maxDepth - 1))
  }

  // Handle objects
  const sanitized = {}

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase().replace(/[_-]/g, '')

    // Check if key is sensitive
    const isSensitiveKey = SENSITIVE_KEYS.some(sensitiveKey =>
      lowerKey.includes(sensitiveKey.toLowerCase().replace(/[_-]/g, ''))
    )

    if (isSensitiveKey) {
      sanitized[key] = '[REDACTED_SENSITIVE]'
    } else if (typeof value === 'object' && value !== null) {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizeForLogging(value, maxDepth - 1)
    } else {
      // Sanitize primitive values
      sanitized[key] = sanitizeValue(value)
    }
  }

  return sanitized
}

/**
 * Sanitizes primitive values by checking against sensitive patterns
 *
 * @param {any} value - The value to sanitize
 * @returns {any} - Sanitized value
 */
function sanitizeValue(value) {
  if (typeof value !== 'string') {
    return value
  }

  let sanitized = value

  // Apply regex patterns to detect and redact sensitive values
  SENSITIVE_VALUE_PATTERNS.forEach(pattern => {
    const matches = sanitized.match(pattern)
    if (matches) {
      matches.forEach(match => {
        // Determine redaction type based on pattern
        if (match.includes('@')) {
          sanitized = sanitized.replace(match, '[REDACTED_EMAIL]')
        } else if (match.startsWith('chr')) {
          sanitized = sanitized.replace(match, '[REDACTED_COORDINATE]')
        } else if (match.startsWith('c.') || match.startsWith('p.')) {
          sanitized = sanitized.replace(match, '[REDACTED_VARIANT]')
        } else if (match.includes('.') && match.split('.').length === 3) {
          sanitized = sanitized.replace(match, '[REDACTED_TOKEN]')
        } else {
          sanitized = sanitized.replace(match, '[REDACTED]')
        }
      })
    }
  })

  return sanitized
}

/**
 * Sanitizes log entry message and data
 *
 * @param {string} message - Log message
 * @param {any} data - Optional data object
 * @returns {Object} - Sanitized message and data
 */
export function sanitizeLogEntry(message, data = null) {
  return {
    message: sanitizeValue(message || ''),
    data: data ? sanitizeForLogging(data) : null
  }
}

/**
 * Quick check to determine if a value contains potentially sensitive data
 * Used for performance optimization
 *
 * @param {any} value - Value to check
 * @returns {boolean} - True if value might contain sensitive data
 */
export function containsSensitiveData(value) {
  if (!value) return false

  const str = typeof value === 'string' ? value : JSON.stringify(value)
  const lowerStr = str.toLowerCase()

  // Quick check for common sensitive patterns
  const quickPatterns = [
    'password',
    'token',
    'email',
    'phone',
    'variant',
    'mutation',
    'hgvs'
  ]

  return (
    quickPatterns.some(pattern => lowerStr.includes(pattern)) ||
    SENSITIVE_VALUE_PATTERNS.some(pattern => pattern.test(str))
  )
}
```

### 3. Pinia Store (`frontend/src/stores/logStore.js`)

```javascript
/**
 * Pinia Store for Log Management
 *
 * Manages reactive log state for the Gene Curator frontend
 * Provides centralized log storage, filtering, and UI state management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * Log Store
 *
 * Features:
 * - Reactive log entries array
 * - LogViewer visibility control
 * - Filtering and search capabilities
 * - Statistics and counts
 * - Memory management with configurable limits
 * - Export functionality
 */
export const useLogStore = defineStore('log', () => {
  // State
  const logs = ref([])
  const isViewerVisible = ref(false)
  const maxEntries = ref(getDefaultMaxEntries())
  const searchQuery = ref('')
  const levelFilter = ref([])

  // Statistics tracking
  const stats = ref({
    totalLogsReceived: 0,
    totalLogsDropped: 0,
    lastLogTime: null,
    sessionStartTime: new Date().toISOString()
  })

  // Computed properties
  const logCount = computed(() => logs.value.length)

  const errorCount = computed(
    () => logs.value.filter(log => log.level === 'ERROR' || log.level === 'CRITICAL').length
  )

  const warningCount = computed(() => logs.value.filter(log => log.level === 'WARN').length)

  const infoCount = computed(() => logs.value.filter(log => log.level === 'INFO').length)

  const debugCount = computed(() => logs.value.filter(log => log.level === 'DEBUG').length)

  const logsByLevel = computed(() => {
    const counts = {
      DEBUG: 0,
      INFO: 0,
      WARN: 0,
      ERROR: 0,
      CRITICAL: 0
    }

    logs.value.forEach(log => {
      if (counts[log.level] !== undefined) {
        counts[log.level]++
      }
    })

    return counts
  })

  const filteredLogs = computed(() => {
    let filtered = [...logs.value]

    // Apply level filter
    if (levelFilter.value.length > 0) {
      filtered = filtered.filter(log => levelFilter.value.includes(log.level))
    }

    // Apply search query
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(
        log =>
          log.message.toLowerCase().includes(query) ||
          log.level.toLowerCase().includes(query) ||
          (log.data && JSON.stringify(log.data).toLowerCase().includes(query)) ||
          (log.correlationId && log.correlationId.toLowerCase().includes(query))
      )
    }

    return filtered
  })

  const recentErrors = computed(() =>
    logs.value
      .filter(log => log.level === 'ERROR' || log.level === 'CRITICAL')
      .slice(-5)
      .reverse()
  )

  const memoryUsage = computed(() => {
    // Rough estimate of memory usage (bytes)
    const jsonSize = JSON.stringify(logs.value).length
    return {
      bytes: jsonSize,
      kb: (jsonSize / 1024).toFixed(2),
      mb: (jsonSize / (1024 * 1024)).toFixed(2)
    }
  })

  // Actions
  function addLogEntry(entry, maxEntriesOverride = null) {
    // Defer to next tick to avoid slot warning during render
    Promise.resolve().then(() => {
      const max = maxEntriesOverride || maxEntries.value

      // Add timestamp if not present
      if (!entry.timestamp) {
        entry.timestamp = new Date().toISOString()
      }

      // Update statistics
      stats.value.totalLogsReceived++
      stats.value.lastLogTime = entry.timestamp

      // Add log entry
      const newLogs = [...logs.value, entry]

      // Trim logs if exceeding max entries
      if (newLogs.length > max) {
        const toRemove = newLogs.length - max
        logs.value = newLogs.slice(toRemove)
        stats.value.totalLogsDropped += toRemove
      } else {
        logs.value = newLogs
      }
    })
  }

  function clearLogs() {
    const previousCount = logs.value.length
    logs.value = []
    stats.value.totalLogsDropped += previousCount
    return previousCount
  }

  function trimLogs(newMaxEntries) {
    if (logs.value.length > newMaxEntries) {
      const toRemove = logs.value.length - newMaxEntries
      logs.value = logs.value.slice(toRemove)
      stats.value.totalLogsDropped += toRemove
    }
    maxEntries.value = newMaxEntries
  }

  function showViewer() {
    isViewerVisible.value = true
  }

  function hideViewer() {
    isViewerVisible.value = false
  }

  function toggleViewer() {
    isViewerVisible.value = !isViewerVisible.value
  }

  function setSearchQuery(query) {
    searchQuery.value = query
  }

  function setLevelFilter(levels) {
    levelFilter.value = levels
  }

  function exportLogs(options = {}) {
    const { format = 'json', includeMetadata = true, filtered = false } = options

    const logsToExport = filtered ? filteredLogs.value : logs.value

    const exportData = {
      exportedAt: new Date().toISOString(),
      application: 'Gene Curator',
      environment: import.meta.env.MODE,
      sessionStartTime: stats.value.sessionStartTime,
      statistics: {
        totalExported: logsToExport.length,
        totalReceived: stats.value.totalLogsReceived,
        totalDropped: stats.value.totalLogsDropped,
        ...logsByLevel.value
      }
    }

    if (includeMetadata) {
      exportData.metadata = {
        url: window.location.href,
        userAgent: navigator.userAgent,
        screenResolution: `${window.screen.width}x${window.screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`
      }
    }

    exportData.logs = logsToExport

    if (format === 'json') {
      return JSON.stringify(exportData, null, 2)
    } else if (format === 'csv') {
      return convertToCSV(logsToExport)
    }

    return exportData
  }

  function convertToCSV(logsArray) {
    if (logsArray.length === 0) return ''

    const headers = ['Timestamp', 'Level', 'Message', 'Data', 'Correlation ID', 'URL']
    const rows = logsArray.map(log => [
      log.timestamp,
      log.level,
      log.message,
      log.data ? JSON.stringify(log.data) : '',
      log.correlationId || '',
      log.url || ''
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    return csvContent
  }

  function getDefaultMaxEntries() {
    try {
      const stored = localStorage.getItem('gene-curator-log-max-entries')
      if (stored) {
        const parsed = parseInt(stored, 10)
        if (!isNaN(parsed) && parsed > 0) {
          return parsed
        }
      }
    } catch (error) {
      console.error('Failed to load max entries from storage:', error)
    }
    return import.meta.env.DEV ? 100 : 50
  }

  // Return public API
  return {
    // State
    logs,
    isViewerVisible,
    maxEntries,
    searchQuery,
    levelFilter,

    // Computed
    logCount,
    errorCount,
    warningCount,
    infoCount,
    debugCount,
    logsByLevel,
    filteredLogs,
    recentErrors,
    memoryUsage,

    // Actions
    addLogEntry,
    clearLogs,
    trimLogs,
    showViewer,
    hideViewer,
    toggleViewer,
    setSearchQuery,
    setLevelFilter,
    exportLogs
  }
})
```

### 4. Vue Plugin (`frontend/src/plugins/logger.js`)

```javascript
/**
 * Vue Plugin for Global Logger Access
 *
 * Makes logger available as $logger in all components
 */

import { logService } from '@/services/logService'
import { useLogStore } from '@/stores/logStore'

export default {
  install(app) {
    // Make logger available globally as $logger
    app.config.globalProperties.$logger = logService

    // Initialize log store after Pinia is available
    app.mixin({
      mounted() {
        if (!logService.store) {
          const logStore = useLogStore()
          logService.initStore(logStore)
        }
      }
    })

    // Add global error handler
    app.config.errorHandler = (err, instance, info) => {
      logService.critical('Uncaught Vue error', {
        error: err.message,
        stack: err.stack,
        component: instance?.$options?.name || 'Unknown',
        info
      })

      // Re-throw error for dev tools
      if (import.meta.env.DEV) {
        console.error('Vue error:', err)
      }
    }

    // Add global warning handler (dev only)
    if (import.meta.env.DEV) {
      app.config.warnHandler = (msg, instance, trace) => {
        logService.warn('Vue warning', {
          message: msg,
          component: instance?.$options?.name || 'Unknown',
          trace
        })
      }
    }
  }
}
```

### 5. Composable (`frontend/src/composables/useLogger.js`)

```javascript
/**
 * Composable for Component-Level Logging
 *
 * Provides logger with automatic component context binding
 */

import { getCurrentInstance, onMounted, onUnmounted } from 'vue'
import { logService } from '@/services/logService'

export function useLogger(componentName = null) {
  const instance = getCurrentInstance()
  const name = componentName || instance?.type?.name || 'Unknown'

  // Bind component context
  logService.setMetadata({ component: name })

  onUnmounted(() => {
    // Clear component context
    logService.clearMetadata()
  })

  return {
    debug: (message, data) => logService.debug(message, { ...data, component: name }),
    info: (message, data) => logService.info(message, { ...data, component: name }),
    warn: (message, data) => logService.warn(message, { ...data, component: name }),
    error: (message, data) => logService.error(message, { ...data, component: name }),
    critical: (message, data) => logService.critical(message, { ...data, component: name }),
    logPerformance: (operation, startTime, data) =>
      logService.logPerformance(operation, startTime, { ...data, component: name })
  }
}
```

### 6. API Integration (`frontend/src/api/index.js`)

```javascript
// Add request/response interceptors for logging

import { logService } from '@/services/logService'

// Request interceptor
apiClient.interceptors.request.use(
  config => {
    // Extract or generate request ID
    const requestId = config.headers['X-Request-ID'] || crypto.randomUUID()
    config.headers['X-Request-ID'] = requestId

    // Set correlation ID in logger
    logService.setCorrelationId(requestId)

    // Store start time for performance tracking
    config.metadata = { startTime: performance.now() }

    logService.debug(`API Request: ${config.method.toUpperCase()} ${config.url}`, {
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

// Response interceptor
apiClient.interceptors.response.use(
  response => {
    const duration = performance.now() - response.config.metadata.startTime

    logService.logApiCall(
      response.config.method.toUpperCase(),
      response.config.url,
      response.status,
      duration
    )

    // Clear correlation ID after response
    logService.clearCorrelationId()

    return response
  },
  error => {
    const duration = error.config?.metadata?.startTime
      ? performance.now() - error.config.metadata.startTime
      : 0

    const status = error.response?.status || 0

    logService.logApiCall(
      error.config?.method?.toUpperCase() || 'UNKNOWN',
      error.config?.url || 'unknown',
      status,
      duration
    )

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
```

## Implementation Steps

1. **Phase 1: Core Infrastructure** (2 hours)
   - [ ] Create `services/logService.js`
   - [ ] Create `utils/logSanitizer.js`
   - [ ] Create `stores/logStore.js`
   - [ ] Create `plugins/logger.js`
   - [ ] Create `composables/useLogger.js`

2. **Phase 2: API Integration** (1 hour)
   - [ ] Add axios interceptors for logging
   - [ ] Implement request correlation ID
   - [ ] Test API call logging

3. **Phase 3: Log Viewer UI** (2-3 hours)
   - [ ] Create `LogViewer.vue` component
   - [ ] Create `LogEntry.vue` component
   - [ ] Create `LogFilters.vue` component
   - [ ] Create `LogSettings.vue` dialog
   - [ ] Add keyboard shortcut (Ctrl+L or Cmd+L) to toggle viewer

4. **Phase 4: Integration** (1 hour)
   - [ ] Install logger plugin in `main.js`
   - [ ] Replace `console.log()` in 10+ components
   - [ ] Test logging in development
   - [ ] Test log viewer UI

5. **Phase 5: Testing & Documentation** (1 hour)
   - [ ] Test privacy sanitization
   - [ ] Test export functionality
   - [ ] Test request correlation
   - [ ] Update CLAUDE.md with logging guidelines

## Usage Examples

### In Components (Options API)

```javascript
export default {
  name: 'CurationEditor',
  mounted() {
    this.$logger.info('Curation editor mounted', {
      curationId: this.curationId
    })
  },
  methods: {
    async saveCuration() {
      const startTime = performance.now()

      try {
        this.$logger.info('Saving curation', { curationId: this.curationId })

        const response = await this.api.saveCuration(this.curationData)

        this.$logger.logPerformance('save_curation', startTime, {
          curationId: response.id,
          success: true
        })

        return response
      } catch (error) {
        this.$logger.error('Failed to save curation', {
          error: error.message,
          curationId: this.curationId
        })
        throw error
      }
    }
  }
}
```

### In Components (Composition API)

```javascript
import { useLogger } from '@/composables/useLogger'

export default {
  setup() {
    const logger = useLogger('CurationEditor')

    onMounted(() => {
      logger.info('Component mounted')
    })

    const saveCuration = async () => {
      const startTime = performance.now()

      try {
        logger.info('Saving curation')
        const response = await api.saveCuration(data)

        logger.logPerformance('save_curation', startTime, { success: true })

        return response
      } catch (error) {
        logger.error('Failed to save curation', { error: error.message })
        throw error
      }
    }

    return { saveCuration }
  }
}
```

### In Stores

```javascript
import { logService } from '@/services/logService'

export const useCurationStore = defineStore('curation', () => {
  const createCuration = async (data) => {
    logService.info('Creating curation', { scopeId: data.scope_id })

    try {
      const response = await api.post('/curations', data)
      logService.info('Curation created', { curationId: response.id })
      return response
    } catch (error) {
      logService.error('Failed to create curation', {
        error: error.message,
        scopeId: data.scope_id
      })
      throw error
    }
  }

  return { createCuration }
})
```

## Log Viewer UI

The log viewer will be a floating panel (similar to Vue DevTools) with:

- **Header**: Title, search box, filters, settings, export, close buttons
- **Toolbar**: Log level chips (DEBUG, INFO, WARN, ERROR, CRITICAL) with counts
- **Log List**: Virtual scrolling for performance with large log lists
- **Log Entry**: Expandable entries showing message, data, timestamp, correlation ID
- **Footer**: Statistics (total logs, errors, warnings, memory usage)

**Keyboard Shortcuts**:
- `Ctrl+L` / `Cmd+L`: Toggle log viewer
- `Ctrl+K` / `Cmd+K`: Clear logs
- `Escape`: Close log viewer

## Benefits Summary

### For Development
- **In-Browser Log Viewer**: No need to open browser console
- **Privacy Protection**: Automatic sanitization of sensitive data
- **Request Correlation**: Match frontend logs to backend logs
- **Performance Tracking**: Automatic timing for API calls
- **Export Logs**: Download logs for bug reports

### For Debugging
- **Search & Filter**: Find specific logs quickly
- **Component Context**: Know which component logged each message
- **Correlation IDs**: Trace requests through frontend and backend
- **Error Grouping**: See all errors at a glance

### For Production
- **Privacy**: Sensitive data automatically redacted
- **User Reports**: Export logs for bug reports
- **Performance Analysis**: Identify slow API calls
- **Error Tracking**: Complete error context

## Configuration

```javascript
// main.js - Configure logging on app startup

import { logService, LogLevel } from '@/services/logService'

// Configure based on environment
if (import.meta.env.PROD) {
  logService.setMinLogLevel(LogLevel.INFO)  // Less verbose in production
  logService.setConsoleEcho(false)  // UI logs only
  logService.setMaxEntries(50)  // Limit memory usage
} else {
  logService.setMinLogLevel(LogLevel.DEBUG)  // Verbose in development
  logService.setConsoleEcho(true)  // Also echo to console
  logService.setMaxEntries(100)  // More logs for debugging
}
```

## Dependencies

- **No New Dependencies Required**
- Uses existing Pinia, Vue 3, and Vuetify

## Acceptance Criteria

- [ ] LogService implemented with sanitization
- [ ] Log sanitizer tested with sensitive data
- [ ] Pinia store implemented and tested
- [ ] Vue plugin installed and working
- [ ] Composable tested in multiple components
- [ ] API interceptors logging requests/responses
- [ ] Log viewer UI implemented
- [ ] Request correlation working
- [ ] Export functionality tested (JSON and CSV)
- [ ] Keyboard shortcuts working
- [ ] At least 20 `console.log()` calls replaced
- [ ] CLAUDE.md updated with logging guidelines

## CLAUDE.md Update

```markdown
## Frontend Logging System (MUST ALWAYS USE)

Gene Curator uses a unified logging system with privacy protection and log viewer UI.

### Basic Usage

```javascript
// In components (Options API)
this.$logger.info('Message', { key: 'value' })
this.$logger.error('Error occurred', { error: error.message })

// In components (Composition API)
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()
logger.info('Message', { key: 'value' })

// In stores
import { logService } from '@/services/logService'
logService.info('Message', { key: 'value' })
```

### NEVER Use These
- ❌ `console.log()` - Use logger instead
- ❌ `console.error()` - Use logger.error() instead
- ❌ `alert()` - Use proper UI notifications + logging

### Privacy Protection
- Automatic sanitization of sensitive data (tokens, emails, genetic variants)
- Safe to log objects without manual redaction

### Log Viewer
- **Keyboard Shortcut**: `Ctrl+L` or `Cmd+L` to toggle log viewer
- **Search**: Filter logs by message, level, or correlation ID
- **Export**: Download logs as JSON or CSV for bug reports

### Request Correlation
- All API calls automatically include correlation ID
- Frontend logs match backend logs via same correlation ID
- Query backend: `SELECT * FROM system_logs WHERE request_id = 'correlation-id'`

### Performance Tracking
```javascript
const startTime = performance.now()
// ... operation ...
logger.logPerformance('operation_name', startTime, { data: 'value' })
```

### When to Log
- **INFO**: User actions, navigation, state changes
- **WARN**: Deprecated usage, slow operations
- **ERROR**: Failed operations, API errors
- **DEBUG**: Detailed operation flow (dev only)
```

---

**Implementation Note**: This is a production-ready frontend logging system with privacy protection, log viewer UI, and seamless integration with the backend unified logging system for complete request tracing.
