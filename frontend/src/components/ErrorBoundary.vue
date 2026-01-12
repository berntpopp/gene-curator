<template>
  <div v-if="error" class="error-boundary">
    <v-alert type="error" variant="tonal" border="start" closable prominent @click:close="reset">
      <v-alert-title class="d-flex align-center">
        <v-icon start size="large">mdi-alert-circle</v-icon>
        Something went wrong
      </v-alert-title>

      <div class="text-body-2 mt-2">
        {{ error.message || 'An unexpected error occurred' }}
      </div>

      <!-- Show stack trace in development -->
      <v-expansion-panels v-if="isDevelopment && error.stack" class="mt-4" variant="accordion">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-code-tags</v-icon>
            Error Details (Development Only)
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <pre class="error-stack">{{ error.stack }}</pre>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <template #append>
        <v-btn variant="outlined" prepend-icon="mdi-refresh" @click="reset"> Try Again </v-btn>
      </template>
    </v-alert>

    <!-- Additional actions -->
    <div class="mt-4 d-flex gap-2">
      <v-btn variant="text" prepend-icon="mdi-home" @click="goHome"> Go to Dashboard </v-btn>
      <v-btn variant="text" prepend-icon="mdi-bug-outline" @click="reportError">
        Report Issue
      </v-btn>
    </div>
  </div>
  <slot v-else />
</template>

<script setup>
  /**
   * Error Boundary Component
   *
   * Catches and handles component errors gracefully.
   * Prevents entire app crash from component failures.
   *
   * Design principles:
   * - Graceful degradation: Show error UI instead of blank page
   * - User-friendly: Clear error message and recovery options
   * - Developer-friendly: Stack trace in development mode
   * - Follows Vue 3 error handling patterns
   *
   * @example
   * <error-boundary>
   *   <precuration-form />
   * </error-boundary>
   */

  import { ref, onErrorCaptured } from 'vue'
  import { useRouter } from 'vue-router'
  import { useLogger } from '@/composables/useLogger'

  const router = useRouter()
  const logger = useLogger()

  const error = ref(null)
  const errorInfo = ref(null)

  // Check if running in development mode
  const isDevelopment = import.meta.env.DEV

  /**
   * Capture errors from child components
   * Vue's onErrorCaptured hook
   */
  onErrorCaptured((err, instance, info) => {
    error.value = err
    errorInfo.value = info

    logger.error('Component error boundary caught error', {
      error: err.message,
      stack: err.stack,
      info,
      component: instance?.$options?.name || 'Unknown'
    })

    // Prevent error propagation
    return false
  })

  /**
   * Reset error state and try rendering again
   * Useful for transient errors
   */
  function reset() {
    error.value = null
    errorInfo.value = null
    logger.info('Error boundary reset')
  }

  /**
   * Navigate to home/dashboard
   * Safe fallback when component is broken
   */
  function goHome() {
    error.value = null
    errorInfo.value = null
    router.push('/dashboard')
    logger.info('Error boundary - navigated to dashboard')
  }

  /**
   * Open issue reporting (GitHub issues or support)
   * Placeholder for actual reporting mechanism
   */
  function reportError() {
    const errorDetails = {
      message: error.value?.message,
      stack: error.value?.stack,
      info: errorInfo.value,
      url: window.location.href,
      timestamp: new Date().toISOString()
    }

    logger.info('Error report initiated', errorDetails)

    // In production, this would open GitHub issues or support form
    // For now, log to console
    console.error('Error Report:', errorDetails)

    // TODO: Implement actual error reporting
    // window.open(`https://github.com/yourrepo/issues/new?body=${encodeURIComponent(JSON.stringify(errorDetails))}`)
  }
</script>

<style scoped>
  .error-boundary {
    padding: 16px;
  }

  .error-stack {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.75rem;
    background-color: rgba(0, 0, 0, 0.05);
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
  }

  .v-theme--dark .error-stack {
    background-color: rgba(255, 255, 255, 0.05);
  }

  /* Ensure proper spacing for action buttons */
  .gap-2 {
    gap: 8px;
  }
</style>
