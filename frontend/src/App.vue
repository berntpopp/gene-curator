<template>
  <v-app>
    <a href="#main-content" class="skip-link" @click.prevent="focusMain">Skip to content</a>
    <SideRail v-if="mdAndUp && authStore.isAuthenticated" />
    <PhoneHeader v-else-if="!mdAndUp && authStore.isAuthenticated" />
    <AppBar v-else />
    <BottomTabs v-if="!mdAndUp" />

    <v-main id="main-content" tabindex="-1">
      <v-container fluid>
        <ErrorBoundary :key="$route.fullPath">
          <router-view />
        </ErrorBoundary>
      </v-container>
      <FooterBar />
    </v-main>

    <MessageSnackbar
      v-model="snackbarState.show"
      :message="snackbarState.message"
      :color="snackbarState.color"
      :timeout="snackbarState.timeout"
    />

    <ConfirmDialog />
    <CommandPalette />

    <!-- Log Viewer Component -->
    <LogViewer v-if="logStore.isViewerVisible" />

    <!-- Disclaimer Dialog -->
    <DisclaimerDialog
      v-model="disclaimerDialogVisible"
      @acknowledged="handleDisclaimerAcknowledged"
    />
  </v-app>
</template>

<script setup lang="ts">
  import { ref, watch, onMounted, onUnmounted } from 'vue'
  import { useAuthStore } from '@/stores/auth'
  import { useLogStore } from '@/stores/logStore'
  import { useDisclaimerStore } from '@/stores/disclaimer'
  import { snackbarState } from '@/composables/useNotifications'
  import { useLogger } from '@/composables/useLogger'
  import ErrorBoundary from '@/components/ErrorBoundary.vue'
  import { useDisplay } from 'vuetify'
  import BottomTabs from '@/components/navigation/BottomTabs.vue'
  import SideRail from '@/components/navigation/SideRail.vue'
  import PhoneHeader from '@/components/navigation/PhoneHeader.vue'
  import AppBar from '@/components/AppBar.vue'
  import FooterBar from '@/components/FooterBar.vue'
  import MessageSnackbar from '@/components/MessageSnackbar.vue'
  import ConfirmDialog from '@/components/ConfirmDialog.vue'
  import CommandPalette from '@/components/palette/CommandPalette.vue'
  import LogViewer from '@/components/logging/LogViewer.vue'
  import DisclaimerDialog from '@/components/DisclaimerDialog.vue'

  // useLogger() is still JS and its JSDoc types the result as Object; narrow it here
  interface ScopedLogger {
    debug(message: string, data?: unknown): void
    info(message: string, data?: unknown): void
  }
  const logger = useLogger() as ScopedLogger
  const { mdAndUp } = useDisplay()
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

  const focusMain = () => document.getElementById('main-content')?.focus()

  // Keyboard shortcut for log viewer (Ctrl+Shift+L)
  const handleKeyPress = (event: KeyboardEvent) => {
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

    // Auth is bootstrapped by the router guard (single /auth/me request)
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
  :root {
    --font-sans: 'IBM Plex Sans', system-ui, sans-serif;
    --font-mono: 'IBM Plex Mono', ui-monospace, Menlo, monospace;
  }

  .v-application {
    font-family: var(--font-sans);
  }

  .v-table,
  .v-data-table,
  .tabular {
    font-variant-numeric: tabular-nums;
  }

  .mono {
    font-family: var(--font-mono);
  }

  :focus-visible {
    outline: 2px solid rgb(var(--v-theme-info));
    outline-offset: 1px;
  }

  /* Visually hidden until focused */
  .skip-link {
    position: absolute;
    left: -9999px;
    z-index: 2100;
    padding: 8px 16px;
    background: rgb(var(--v-theme-surface));
    color: rgb(var(--v-theme-primary));
  }

  .skip-link:focus {
    left: 8px;
    top: 8px;
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

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .v-container {
      padding: 8px;
    }
  }
</style>
