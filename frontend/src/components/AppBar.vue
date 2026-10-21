<template>
  <v-app-bar app color="primary">
    <!-- Logo + title: one focusable link -->
    <router-link to="/" aria-label="Gene Curator home" class="brand">
      <v-img
        src="/img/logo.png"
        alt=""
        class="mr-3"
        contain
        max-height="48"
        max-width="48"
        aspect-ratio="1"
        width="48"
      />
      <span>
        <span class="text-title-large">Gene Curator</span>
        <br v-if="mdAndUp" />
        <span v-if="mdAndUp" class="version-info">
          Version: {{ version }} - Build: {{ buildHash }}
        </span>
      </span>
    </router-link>

    <v-spacer />

    <!-- Main Navigation -->
    <!-- While a stored token is still being verified, show neither guest nor user nav -->
    <MainNavigation v-if="authReady" />

    <!-- Theme Toggle -->
    <v-tooltip v-if="mdAndUp" :text="themeLabel" location="bottom">
      <template #activator="{ props }">
        <v-btn v-bind="props" :aria-label="themeLabel" icon class="ml-2" @click="toggleTheme">
          <v-icon>{{ MODE_ICON[mode] }}</v-icon>
        </v-btn>
      </template>
    </v-tooltip>

    <!-- User Menu -->
    <UserMenu v-if="mdAndUp && authReady" />
  </v-app-bar>
</template>

<script setup lang="ts">
  /**
   * AppBar Component (Refactored)
   *
   * Main application navigation bar with auto-generated menus.
   *
   * Features:
   * - Logo and branding
   * - Auto-generated main navigation (route-driven)
   * - Auto-generated user menu (route-driven)
   * - Theme toggle
   * - Version display
   *
   * Architecture:
   * - Uses MainNavigation component for main menu
   * - Uses UserMenu component for user dropdown
   * - Single source of truth: Router metadata
   * - Zero hard-coded menu items
   *
   * @see src/components/navigation/MainNavigation.vue
   * @see src/components/navigation/UserMenu.vue
   * @see src/router/index.js (menu metadata)
   */

  import { ref, computed } from 'vue'
  import { useDisplay, useTheme } from 'vuetify'
  import { useAuthStore } from '@/stores/auth'
  import { useLogger } from '@/composables/useLogger'
  import MainNavigation from '@/components/navigation/MainNavigation.vue'
  import UserMenu from '@/components/navigation/UserMenu.vue'

  const logger = useLogger()
  const theme = useTheme()
  const { mdAndUp } = useDisplay()
  const authStore = useAuthStore()
  const authReady = computed(() => !authStore.token || !!authStore.user)

  // Version info
  const version = ref('0.4.0')
  const buildHash = ref('dev')

  // Theme mode (persisted in localStorage, restored in main.ts before Vuetify init)
  type ThemeMode = 'light' | 'dark' | 'system'
  const NEXT_MODE: Record<ThemeMode, ThemeMode> = { system: 'light', light: 'dark', dark: 'system' }
  const MODE_ICON: Record<ThemeMode, string> = {
    system: 'mdi-theme-light-dark',
    light: 'mdi-white-balance-sunny',
    dark: 'mdi-weather-night'
  }
  const saved = localStorage.getItem('theme')
  const mode = ref<ThemeMode>(saved === 'light' || saved === 'dark' ? saved : 'system')

  const themeLabel = computed(
    () => `Theme: ${mode.value}. Switch to ${NEXT_MODE[mode.value]} theme`
  )

  /** Cycle system -> light -> dark -> system */
  const toggleTheme = () => {
    mode.value = NEXT_MODE[mode.value]
    void theme.change(mode.value)
    localStorage.setItem('theme', mode.value)
    logger.info('Theme changed', { theme: mode.value })
  }
</script>

<style scoped>
  .brand {
    display: flex;
    align-items: center;
    color: inherit;
    text-decoration: none;
    min-width: 0;
  }

  .version-info {
    font-size: 0.75rem;
    opacity: 0.7;
    line-height: 1;
    margin-top: -4px;
  }
</style>
