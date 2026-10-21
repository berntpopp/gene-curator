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
        <v-btn variant="outlined" prepend-icon="mdi-refresh" @click="reset"> Try again </v-btn>
      </template>
    </v-alert>

    <!-- Additional actions -->
    <div class="mt-4 d-flex ga-2">
      <v-btn variant="text" prepend-icon="mdi-home" @click="goHome"> Go to dashboard </v-btn>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
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

  // Vue hands over the thrown value as unknown; the template reads message/stack, which
  // is also safe for non-Error throws (they render the fallback text).
  const error = ref<Error | null>(null)
  const errorInfo = ref<string | null>(null)

  // Check if running in development mode
  const isDevelopment = import.meta.env.DEV

  /**
   * Capture errors from child components
   * Vue's onErrorCaptured hook
   */
  onErrorCaptured((err: unknown, instance, info) => {
    const caught = err as Error
    error.value = caught
    errorInfo.value = info

    logger.error('Component error boundary caught error', {
      error: caught.message,
      stack: caught.stack,
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
</script>

<style scoped>
  .error-boundary {
    padding: 16px;
  }

  .error-stack {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    background-color: rgba(var(--v-theme-on-surface), 0.05);
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
  }

  /* Ensure proper spacing for action buttons */
</style>
