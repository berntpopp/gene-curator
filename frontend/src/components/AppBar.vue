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

    <!-- Theme toggle stays reachable at every width -->
    <ThemeToggle class="ml-2" />

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
  import { useDisplay } from 'vuetify'
  import { useAuthStore } from '@/stores/auth'
  import MainNavigation from '@/components/navigation/MainNavigation.vue'
  import ThemeToggle from '@/components/navigation/ThemeToggle.vue'
  import UserMenu from '@/components/navigation/UserMenu.vue'

  const { mdAndUp } = useDisplay()
  const authStore = useAuthStore()
  const authReady = computed(() => !authStore.token || !!authStore.user)

  // Version info
  const version = ref('0.4.1')
  const buildHash = ref('dev')
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
