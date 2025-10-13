/**
 * Pinia Store for Log Management
 *
 * FIX #5: Removed Promise.resolve() race condition - use synchronous updates
 *
 * Manages reactive log state for the Gene Curator frontend.
 * Provides centralized log storage, filtering, and UI state management.
 *
 * Features:
 * - Reactive log entries array
 * - LogViewer visibility control
 * - Filtering and search capabilities
 * - Statistics and counts
 * - Memory management with configurable limits
 * - Export functionality (JSON/CSV)
 *
 * FIX #5: All updates are synchronous - Vue batches them automatically.
 * No Promise.resolve() calls that break reactive update flow.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * Get default max entries from LocalStorage or use environment-based default
 *
 * @private
 * @returns {number} Maximum log entries to keep
 */
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

/**
 * Log Store
 *
 * Pinia store for managing frontend logs with reactive state.
 */
export const useLogStore = defineStore('log', () => {
  // ============================================================================
  // State
  // ============================================================================

  /** @type {Ref<Array>} Array of log entries */
  const logs = ref([])

  /** @type {Ref<boolean>} LogViewer visibility state */
  const isViewerVisible = ref(false)

  /** @type {Ref<number>} Maximum number of logs to keep */
  const maxEntries = ref(getDefaultMaxEntries())

  /** @type {Ref<string>} Search query for filtering logs */
  const searchQuery = ref('')

  /** @type {Ref<Array<string>>} Log levels to filter by */
  const levelFilter = ref([])

  /** @type {Ref<Object>} Statistics tracking */
  const stats = ref({
    totalLogsReceived: 0,
    totalLogsDropped: 0,
    lastLogTime: null,
    sessionStartTime: new Date().toISOString()
  })

  // ============================================================================
  // Computed Properties
  // ============================================================================

  /**
   * Total number of logs currently stored
   */
  const logCount = computed(() => logs.value.length)

  /**
   * Count of error and critical logs
   */
  const errorCount = computed(
    () => logs.value.filter(log => log.level === 'ERROR' || log.level === 'CRITICAL').length
  )

  /**
   * Count of warning logs
   */
  const warningCount = computed(() => logs.value.filter(log => log.level === 'WARN').length)

  /**
   * Count of info logs
   */
  const infoCount = computed(() => logs.value.filter(log => log.level === 'INFO').length)

  /**
   * Count of debug logs
   */
  const debugCount = computed(() => logs.value.filter(log => log.level === 'DEBUG').length)

  /**
   * Counts of logs by level
   */
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

  /**
   * Filtered logs based on search query and level filter
   */
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

  /**
   * Most recent error logs (last 5, reversed)
   */
  const recentErrors = computed(() =>
    logs.value
      .filter(log => log.level === 'ERROR' || log.level === 'CRITICAL')
      .slice(-5)
      .reverse()
  )

  /**
   * Rough memory usage estimate
   */
  const memoryUsage = computed(() => {
    // Rough estimate of memory usage (bytes)
    const jsonSize = JSON.stringify(logs.value).length
    return {
      bytes: jsonSize,
      kb: (jsonSize / 1024).toFixed(2),
      mb: (jsonSize / (1024 * 1024)).toFixed(2)
    }
  })

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Add a log entry to the store
   *
   * FIX #5: Synchronous update - Vue batches reactive updates automatically.
   * No need for Promise.resolve() which breaks reactive update flow.
   *
   * @param {Object} entry - Log entry to add
   * @param {number|null} maxEntriesOverride - Optional override for max entries
   */
  function addLogEntry(entry, maxEntriesOverride = null) {
    const max = maxEntriesOverride || maxEntries.value

    // Add timestamp if not present
    if (!entry.timestamp) {
      entry.timestamp = new Date().toISOString()
    }

    // Update statistics
    stats.value.totalLogsReceived++
    stats.value.lastLogTime = entry.timestamp

    // Add log entry - Vue will batch this update automatically
    logs.value = [...logs.value, entry]

    // Trim logs if exceeding max entries
    if (logs.value.length > max) {
      const toRemove = logs.value.length - max
      logs.value = logs.value.slice(toRemove)
      stats.value.totalLogsDropped += toRemove
    }
  }

  /**
   * Clear all logs
   *
   * @returns {number} Number of logs cleared
   */
  function clearLogs() {
    const previousCount = logs.value.length
    logs.value = []
    stats.value.totalLogsDropped += previousCount
    return previousCount
  }

  /**
   * Trim logs to new maximum
   *
   * @param {number} newMaxEntries - New maximum entries
   */
  function trimLogs(newMaxEntries) {
    if (logs.value.length > newMaxEntries) {
      const toRemove = logs.value.length - newMaxEntries
      logs.value = logs.value.slice(toRemove)
      stats.value.totalLogsDropped += toRemove
    }
    maxEntries.value = newMaxEntries
  }

  /**
   * Show log viewer UI
   */
  function showViewer() {
    isViewerVisible.value = true
  }

  /**
   * Hide log viewer UI
   */
  function hideViewer() {
    isViewerVisible.value = false
  }

  /**
   * Toggle log viewer visibility
   */
  function toggleViewer() {
    isViewerVisible.value = !isViewerVisible.value
  }

  /**
   * Set search query for filtering
   *
   * @param {string} query - Search query
   */
  function setSearchQuery(query) {
    searchQuery.value = query
  }

  /**
   * Set level filter
   *
   * @param {Array<string>} levels - Log levels to filter by
   */
  function setLevelFilter(levels) {
    levelFilter.value = levels
  }

  /**
   * Export logs
   *
   * @param {Object} options - Export options
   * @param {string} options.format - Export format ('json' or 'csv')
   * @param {boolean} options.includeMetadata - Include system metadata
   * @param {boolean} options.filtered - Export filtered logs only
   * @returns {string|Object} Exported logs data
   */
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

  /**
   * Convert logs to CSV format
   *
   * @private
   * @param {Array} logsArray - Logs to convert
   * @returns {string} CSV string
   */
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

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    // State
    logs,
    isViewerVisible,
    maxEntries,
    searchQuery,
    levelFilter,
    stats,

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
