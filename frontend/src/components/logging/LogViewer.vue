<template>
  <v-navigation-drawer
    v-model="drawerVisible"
    location="right"
    temporary
    width="600"
    class="log-viewer"
    @keydown.escape="closeDrawer"
  >
    <div class="drawer-container">
      <!-- Toolbar -->
      <v-toolbar color="primary" dark density="compact" class="drawer-header">
        <v-toolbar-title class="text-subtitle-1">
          <v-icon start>mdi-text-box-search-outline</v-icon>
          Application Logs
          <v-chip
            v-if="logStore.logCount > 0"
            size="x-small"
            color="white"
            text-color="primary"
            class="ml-2"
          >
            {{ logStore.logCount }}
          </v-chip>
        </v-toolbar-title>

        <v-spacer></v-spacer>

        <!-- Toolbar Actions -->
        <v-btn
          icon="mdi-download"
          size="small"
          variant="text"
          :disabled="logStore.logCount === 0"
          title="Download logs as JSON"
          @click="downloadLogs"
        ></v-btn>

        <v-btn
          icon="mdi-delete-sweep"
          size="small"
          variant="text"
          :disabled="logStore.logCount === 0"
          title="Clear all logs"
          @click="clearLogs"
        ></v-btn>

        <v-btn
          icon="mdi-close"
          size="small"
          variant="text"
          title="Close log viewer"
          @click="closeDrawer"
        ></v-btn>
      </v-toolbar>

      <!-- Scrollable content area -->
      <div class="drawer-content">
        <!-- Filter Controls -->
        <v-container class="py-2" fluid>
          <v-row dense>
            <!-- Search Filter -->
            <v-col cols="12" md="6">
              <v-text-field
                v-model="searchQuery"
                label="Search logs..."
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                density="compact"
                clearable
                hide-details
                @update:model-value="updateSearch"
              ></v-text-field>
            </v-col>

            <!-- Level Filter -->
            <v-col cols="12" md="6">
              <v-select
                v-model="selectedLevels"
                :items="logLevelOptions"
                label="Filter by level"
                prepend-inner-icon="mdi-filter"
                variant="outlined"
                density="compact"
                multiple
                chips
                closable-chips
                hide-details
                @update:model-value="updateLevelFilter"
              ></v-select>
            </v-col>
          </v-row>

          <!-- Log Configuration -->
          <v-row dense class="mt-2">
            <v-col cols="12" md="6">
              <v-select
                v-model="maxEntries"
                :items="maxEntriesOptions"
                label="Max log entries"
                prepend-inner-icon="mdi-cog"
                variant="outlined"
                density="compact"
                hide-details
                @update:model-value="updateMaxEntries"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6" class="d-flex align-center">
              <v-chip color="primary" size="x-small" variant="outlined" class="mr-2">
                Memory: {{ logStore.memoryUsage.kb }}KB
              </v-chip>
              <v-chip
                :color="logStore.logCount >= maxEntries * 0.8 ? 'warning' : 'success'"
                size="x-small"
                variant="outlined"
              >
                Usage: {{ logStore.logCount }}/{{ maxEntries }}
              </v-chip>
            </v-col>
          </v-row>

          <!-- Log Statistics -->
          <v-row v-if="logStore.logCount > 0" dense class="mt-2">
            <v-col cols="12">
              <div class="d-flex gap-2 flex-wrap">
                <template v-for="(count, level) in logStore.logsByLevel" :key="level">
                  <v-chip
                    v-if="count > 0"
                    :color="getLogColor(level)"
                    size="x-small"
                    variant="outlined"
                  >
                    {{ level }}: {{ count }}
                  </v-chip>
                </template>
              </div>
            </v-col>
          </v-row>
        </v-container>

        <v-divider></v-divider>

        <!-- Log Entries -->
        <v-container class="log-entries pa-2" fluid>
          <div v-if="filteredLogs.length === 0" class="text-center py-8 text-grey">
            <v-icon size="48" class="mb-2">mdi-text-box-remove-outline</v-icon>
            <p>
              {{ logStore.logCount === 0 ? 'No logs available' : 'No logs match your filters' }}
            </p>
          </div>

          <v-card
            v-for="(log, index) in filteredLogs"
            :key="`${log.timestamp}-${index}`"
            class="mb-2 log-entry"
            variant="outlined"
            :color="getLogColor(log.level)"
            density="compact"
          >
            <v-card-text class="py-2">
              <!-- Log Header -->
              <div class="d-flex align-center justify-space-between mb-1">
                <div class="d-flex align-center gap-2">
                  <v-chip :color="getLogColor(log.level)" size="x-small" variant="flat">
                    {{ log.level }}
                  </v-chip>
                  <span class="text-caption text-grey">
                    {{ formatTimestamp(log.timestamp) }}
                  </span>
                  <v-chip v-if="log.correlationId" size="x-small" variant="outlined" color="grey">
                    {{ log.correlationId.substring(0, 8) }}
                  </v-chip>
                </div>

                <!-- Copy button -->
                <v-btn
                  icon="mdi-content-copy"
                  size="x-small"
                  variant="text"
                  title="Copy log entry"
                  @click="copyLogEntry(log)"
                ></v-btn>
              </div>

              <!-- Log Message -->
              <div class="log-message text-body-2 mb-1">
                {{ log.message }}
              </div>

              <!-- Log Data (if present) -->
              <v-expansion-panels v-if="log.data" variant="accordion" class="log-data">
                <v-expansion-panel>
                  <v-expansion-panel-title class="text-caption py-1">
                    <v-icon start size="small">mdi-code-json</v-icon>
                    Additional Data
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <pre class="log-data-content">{{ formatLogData(log.data) }}</pre>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card-text>
          </v-card>
        </v-container>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup>
  import { ref, computed, watch } from 'vue'
  import { useLogStore } from '@/stores/logStore'
  import { LogLevel } from '@/services/logService'
  import { useDrawerState } from '@/composables/useDrawerState'

  // Store access
  const logStore = useLogStore()

  // Use drawer state for single-open-drawer pattern
  const { isOpen: drawerIsOpen, close: closeDrawer } = useDrawerState('log-viewer')

  // Computed property to sync drawer state with logStore
  const drawerVisible = computed({
    get: () => drawerIsOpen.value,
    set: value => {
      if (value) {
        drawerIsOpen.value = true
        // Also update logStore for compatibility
        if (!logStore.isViewerVisible) {
          logStore.isViewerVisible = true
        }
      } else {
        drawerIsOpen.value = false
        if (logStore.isViewerVisible) {
          logStore.isViewerVisible = false
        }
      }
    }
  })

  // Watch logStore.isViewerVisible to sync with drawer state (for keyboard shortcut support)
  watch(
    () => logStore.isViewerVisible,
    newValue => {
      if (newValue && !drawerIsOpen.value) {
        drawerIsOpen.value = true
      } else if (!newValue && drawerIsOpen.value) {
        drawerIsOpen.value = false
      }
    }
  )

  // Watch drawerIsOpen to sync back to logStore
  watch(
    () => drawerIsOpen.value,
    newValue => {
      if (newValue !== logStore.isViewerVisible) {
        logStore.isViewerVisible = newValue
      }
    }
  )

  // Local reactive state
  const searchQuery = ref('')
  const selectedLevels = ref([
    LogLevel.DEBUG,
    LogLevel.INFO,
    LogLevel.WARN,
    LogLevel.ERROR,
    LogLevel.CRITICAL
  ])
  const maxEntries = ref(logStore.maxEntries)

  // Options for max entries dropdown
  const maxEntriesOptions = [
    { title: '20 entries', value: 20 },
    { title: '50 entries (default)', value: 50 },
    { title: '100 entries', value: 100 },
    { title: '200 entries', value: 200 },
    { title: '500 entries', value: 500 }
  ]

  // Log level options for the filter select
  const logLevelOptions = [
    { title: 'Debug', value: LogLevel.DEBUG },
    { title: 'Info', value: LogLevel.INFO },
    { title: 'Warning', value: LogLevel.WARN },
    { title: 'Error', value: LogLevel.ERROR },
    { title: 'Critical', value: LogLevel.CRITICAL }
  ]

  // Computed properties
  const filteredLogs = computed(() => {
    let filtered = [...logStore.logs]

    // Apply level filter
    if (selectedLevels.value.length > 0 && selectedLevels.value.length < 5) {
      filtered = filtered.filter(log => selectedLevels.value.includes(log.level))
    }

    // Apply search query
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(
        log =>
          log.message.toLowerCase().includes(query) ||
          log.level.toLowerCase().includes(query) ||
          (log.data && JSON.stringify(log.data).toLowerCase().includes(query))
      )
    }

    // Return in reverse chronological order (newest first)
    return filtered.reverse()
  })

  // Methods
  function getLogColor(level) {
    switch (level) {
      case LogLevel.DEBUG:
        return 'grey'
      case LogLevel.INFO:
        return 'info'
      case LogLevel.WARN:
        return 'warning'
      case LogLevel.ERROR:
        return 'error'
      case LogLevel.CRITICAL:
        return 'error'
      default:
        return 'grey'
    }
  }

  function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    })
  }

  function formatLogData(data) {
    try {
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }

  function downloadLogs() {
    try {
      const exportData = logStore.exportLogs({
        format: 'json',
        includeMetadata: true,
        filtered: false
      })

      const blob = new Blob([exportData], { type: 'application/json' })
      const url = URL.createObjectURL(blob)

      // Create temporary link and trigger download
      const link = document.createElement('a')
      link.href = url
      link.download = `gene-curator-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // Clean up
      URL.revokeObjectURL(url)

      // Log success (using global logService to avoid circular dependency)
      window.logService?.info('Logs exported successfully')
    } catch (error) {
      window.logService?.error('Failed to download logs', { error: error.message })
    }
  }

  function clearLogs() {
    if (confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
      const count = logStore.clearLogs()
      window.logService?.info(`Cleared ${count} log entries`)
    }
  }

  function copyLogEntry(log) {
    try {
      const logText = `[${log.timestamp}] ${log.level}: ${log.message}${
        log.data ? `\nData: ${JSON.stringify(log.data, null, 2)}` : ''
      }`

      navigator.clipboard
        .writeText(logText)
        .then(() => {
          window.logService?.debug('Log entry copied to clipboard')
        })
        .catch(error => {
          window.logService?.error('Failed to copy log entry', { error: error.message })
        })
    } catch (error) {
      window.logService?.error('Failed to copy log entry', { error: error.message })
    }
  }

  function updateMaxEntries(newValue) {
    try {
      logStore.trimLogs(newValue)
      maxEntries.value = newValue
      window.logService?.info(`Log retention limit updated to ${newValue} entries`)
    } catch (error) {
      window.logService?.error('Failed to update max entries', { error: error.message })
    }
  }

  function updateSearch(value) {
    logStore.setSearchQuery(value || '')
  }

  function updateLevelFilter(value) {
    logStore.setLevelFilter(value)
  }

  // Watch for store changes
  watch(
    () => logStore.maxEntries,
    newValue => {
      maxEntries.value = newValue
    }
  )
</script>

<style scoped>
  .log-viewer {
    z-index: 1000;
    /* Ensure drawer doesn't overlap with page footer or header */
    top: 64px !important; /* Below app header */
    bottom: 77px !important; /* Above page footer */
    height: calc(100vh - 64px - 77px) !important; /* Viewport minus header and footer */
  }

  /* Flex container for full-height drawer layout */
  .drawer-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  /* Fixed header */
  .drawer-header {
    flex-shrink: 0;
  }

  /* Scrollable content area */
  .drawer-content {
    flex: 1;
    overflow-y: auto;
  }

  .log-entries {
    /* No longer needs max-height, contained by flex layout */
  }

  .log-entry {
    transition: all 0.2s ease;
  }

  .log-entry:hover {
    transform: translateX(-2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .log-message {
    font-family: 'Roboto Mono', 'Monaco', 'Menlo', monospace;
    line-height: 1.4;
    word-break: break-word;
  }

  .log-data-content {
    font-size: 0.75rem;
    line-height: 1.3;
    max-height: 200px;
    overflow-y: auto;
    background: rgba(0, 0, 0, 0.02);
    border-radius: 4px;
    padding: 8px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .log-data .v-expansion-panel {
    background: transparent;
  }

  .log-data .v-expansion-panel-title {
    min-height: 32px;
    padding: 4px 8px;
  }

  .gap-2 {
    gap: 8px;
  }
</style>
