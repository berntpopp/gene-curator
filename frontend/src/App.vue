<template>
  <v-app>
    <AppBar />

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <MessageSnackbar
      v-model="snackbarState.show"
      :message="snackbarState.message"
      :color="snackbarState.color"
      :timeout="snackbarState.timeout"
    />

    <!-- Log Viewer Component -->
    <LogViewer />

    <!-- Disclaimer Dialog -->
    <DisclaimerDialog
      v-model="disclaimerDialogVisible"
      @acknowledged="handleDisclaimerAcknowledged"
    />

    <FooterBar />
  </v-app>
</template>

<script setup>
  import { ref, watch, onMounted, onUnmounted } from 'vue'
  import { useAuthStore } from '@/stores/auth.js'
  import { useLogStore } from '@/stores/logStore'
  import { useDisclaimerStore } from '@/stores/disclaimer'
  import { snackbarState } from '@/composables/useNotifications.js'
  import { useLogger } from '@/composables/useLogger'
  import AppBar from '@/components/AppBar.vue'
  import FooterBar from '@/components/FooterBar.vue'
  import MessageSnackbar from '@/components/MessageSnackbar.vue'
  import LogViewer from '@/components/logging/LogViewer.vue'
  import DisclaimerDialog from '@/components/DisclaimerDialog.vue'

  const logger = useLogger()
  const authStore = useAuthStore()
  const logStore = useLogStore()
  const disclaimerStore = useDisclaimerStore()

  // Disclaimer dialog visibility
  const disclaimerDialogVisible = ref(false)

  // Watch for manual disclaimer requests from footer
  watch(
    () => disclaimerStore.showManually,
    shouldShow => {
      if (shouldShow) {
        logger.debug('Showing disclaimer dialog (manual request)')
        disclaimerDialogVisible.value = true
        disclaimerStore.resetShowManually()
      }
    }
  )

  // Keyboard shortcut for log viewer (Ctrl+Shift+L)
  const handleKeyPress = event => {
    if (event.ctrlKey && event.shiftKey && event.key === 'L') {
      event.preventDefault()
      logStore.toggleViewer()
    }
  }

  // Handle disclaimer acknowledgment
  const handleDisclaimerAcknowledged = () => {
    logger.info('User acknowledged disclaimer')
    disclaimerStore.saveAcknowledgment()
    disclaimerDialogVisible.value = false
  }

  onMounted(async () => {
    logger.info('App component mounted, initializing stores')

    // Initialize authentication state on app startup
    await authStore.initialize()

    // Initialize disclaimer store
    disclaimerStore.initialize()

    // Show disclaimer if not acknowledged
    if (disclaimerStore.shouldShowDisclaimer) {
      logger.info('Showing disclaimer dialog (first visit or version update)')
      // Small delay to ensure app is fully rendered
      setTimeout(() => {
        disclaimerDialogVisible.value = true
      }, 500)
    } else {
      logger.debug('Disclaimer already acknowledged', {
        version: disclaimerStore.disclaimerVersion,
        acknowledgedAt: disclaimerStore.formattedAcknowledgmentDate
      })
    }

    // Add keyboard listener for log viewer
    window.addEventListener('keydown', handleKeyPress)

    logger.info('App initialization complete')
  })

  onUnmounted(() => {
    // Clean up keyboard listener
    window.removeEventListener('keydown', handleKeyPress)
    logger.debug('App component unmounted')
  })
</script>

<style>
  /* Global styles */
  .v-application {
    font-family: 'Roboto', sans-serif;
  }

  /* Custom scrollbar */
  ::-webkit-scrollbar {
    width: 8px;
  }

  ::-webkit-scrollbar-track {
    background: var(--v-theme-surface);
  }

  ::-webkit-scrollbar-thumb {
    background: var(--v-theme-primary);
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: var(--v-theme-primary-darken-1);
  }

  /* Loading state */
  .loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 200px;
  }

  /* Error state */
  .error-container {
    text-align: center;
    padding: 2rem;
  }

  /* Table styles */
  .gene-table .v-data-table__wrapper {
    border-radius: 8px;
  }

  /* Form styles */
  .form-container {
    max-width: 600px;
    margin: 0 auto;
  }

  /* Card styles */
  .info-card {
    margin-bottom: 1rem;
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .v-container {
      padding: 8px;
    }
  }
</style>
