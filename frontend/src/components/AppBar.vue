<template>
  <v-app-bar app color="primary" dark>
    <!-- Logo Image -->
    <v-img
      src="/img/logo.png"
      class="mr-3 app-logo"
      contain
      max-height="48"
      max-width="48"
      @click="$router.push('/')"
    />

    <!-- Toolbar Title -->
    <v-toolbar-title>
      <span class="clickable" @click="$router.push('/')"> Gene Curator </span>
      <br />
      <span class="version-info"> Version: {{ version }} - Build: {{ buildHash }} </span>
    </v-toolbar-title>

    <v-spacer />

    <!-- Main Navigation -->
    <MainNavigation />

    <!-- Theme Toggle -->
    <v-btn icon class="ml-2" @click="toggleTheme">
      <v-icon>
        {{ isDark ? 'mdi-weather-night' : 'mdi-white-balance-sunny' }}
      </v-icon>
    </v-btn>

    <!-- User Menu -->
    <UserMenu />
  </v-app-bar>
</template>

<script setup>
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

  import { ref, computed, onMounted } from 'vue'
  import { useTheme } from 'vuetify'
  import { useLogger } from '@/composables/useLogger'
  import MainNavigation from '@/components/navigation/MainNavigation.vue'
  import UserMenu from '@/components/navigation/UserMenu.vue'

  const logger = useLogger()
  const theme = useTheme()

  // Version info
  const version = ref('0.3.0')
  const buildHash = ref('dev')

  // Theme
  const isDark = computed(() => theme.global.current.value.dark)

  /**
   * Toggle dark/light theme
   */
  const toggleTheme = () => {
    // Use the modern Vuetify 3.9+ theme API
    theme.toggle()
    const newTheme = theme.global.current.value.dark ? 'dark' : 'light'
    localStorage.setItem('theme', newTheme)
    logger.info('Theme toggled', { theme: newTheme })
  }

  /**
   * Apply saved theme on mount
   */
  onMounted(() => {
    // Apply saved theme using modern Vuetify 3.9+ API
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme && theme.global.name.value !== savedTheme) {
      theme.change(savedTheme)
      logger.debug('Applied saved theme', { theme: savedTheme })
    }
  })
</script>

<style scoped>
  .app-logo {
    cursor: pointer;
    transition: transform 0.2s ease;
  }

  .app-logo:hover {
    transform: scale(1.05);
  }

  .clickable {
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .clickable:hover {
    opacity: 0.8;
  }

  .version-info {
    font-size: 0.75rem;
    opacity: 0.7;
    line-height: 1;
    margin-top: -4px;
  }
</style>
