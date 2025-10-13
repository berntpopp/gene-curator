<template>
  <div class="main-navigation">
    <!-- Simple nav items (no dropdown) -->
    <template v-for="item in simpleItems" :key="item.name">
      <v-btn :to="item.to" text>
        <v-icon v-if="item.icon" start>{{ item.icon }}</v-icon>
        {{ item.label }}
      </v-btn>
    </template>

    <!-- Curation Dropdown -->
    <v-menu v-if="curationItems.length > 0" offset-y>
      <template #activator="{ props }">
        <v-btn text v-bind="props">
          <v-icon start>mdi-clipboard-check</v-icon>
          {{ curationLabel }}
          <v-icon end>mdi-menu-down</v-icon>
        </v-btn>
      </template>
      <v-list>
        <BaseNavigationItem
          v-for="item in curationItems"
          :key="item.name"
          :to="item.to"
          :icon="item.icon"
          :label="item.label"
        />
      </v-list>
    </v-menu>

    <!-- Curation Setup Dropdown (Admin only) -->
    <v-menu v-if="curationSetupItems.length > 0" offset-y>
      <template #activator="{ props }">
        <v-btn text v-bind="props">
          <v-icon start>mdi-cog-outline</v-icon>
          {{ curationSetupLabel }}
          <v-icon end>mdi-menu-down</v-icon>
        </v-btn>
      </template>
      <v-list>
        <BaseNavigationItem
          v-for="item in curationSetupItems"
          :key="item.name"
          :to="item.to"
          :icon="item.icon"
          :label="item.label"
        />
      </v-list>
    </v-menu>
  </div>
</template>

<script setup>
  /**
   * MainNavigation Component
   *
   * Auto-generates main navigation menu from router metadata.
   * Uses useNavigation composable for role-based filtering.
   *
   * Features:
   * - Route-driven navigation (single source of truth)
   * - Role-based access control
   * - Dropdown support (Curation, Curation Setup)
   * - Consistent terminology
   * - Responsive-ready
   *
   * @see src/composables/useNavigation.js
   */

  import { computed } from 'vue'
  import { useRouter } from 'vue-router'
  import { usePermissions } from '@/composables/usePermissions'
  import { TERMINOLOGY } from '@/config/terminology'
  import BaseNavigationItem from './BaseNavigationItem.vue'

  const router = useRouter()
  const { can, isAuthenticated } = usePermissions()

  /**
   * Get all routes with showInMainMenu metadata
   */
  const mainMenuItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => route.meta?.showInMainMenu === true)
      .filter(route => hasAccess(route.meta))
      .map(route => ({
        name: route.name,
        to: { name: route.name },
        icon: route.meta.icon,
        label: route.meta.label || route.meta.title,
        order: route.meta.order || 999
      }))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Get items for Curation dropdown
   */
  const curationItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => route.meta?.showInDropdown === 'curation')
      .filter(route => hasAccess(route.meta))
      .map(route => ({
        name: route.name,
        to: { name: route.name },
        icon: route.meta.icon,
        label: route.meta.label || route.meta.title,
        order: route.meta.order || 999
      }))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Get items for Curation Setup dropdown (admin only)
   */
  const curationSetupItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => route.meta?.showInDropdown === 'curationSetup')
      .filter(route => hasAccess(route.meta))
      .map(route => ({
        name: route.name,
        to: { name: route.name },
        icon: route.meta.icon,
        label: route.meta.label || route.meta.title,
        order: route.meta.order || 999
      }))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Simple items (no dropdown)
   */
  const simpleItems = computed(() => {
    return mainMenuItems.value
  })

  /**
   * Dropdown labels from terminology
   */
  const curationLabel = computed(() => TERMINOLOGY.CURATION || 'Curation')
  const curationSetupLabel = computed(() => TERMINOLOGY.CURATION_SETUP || 'Curation Setup')

  /**
   * Check if user has access to a route
   */
  function hasAccess(routeMeta) {
    if (!routeMeta) return true

    // Check authentication
    if (routeMeta.requiresAuth && !isAuthenticated.value) {
      return false
    }

    // Check guest-only routes
    if (routeMeta.requiresGuest && isAuthenticated.value) {
      return false
    }

    // Check role requirements
    if (routeMeta.requiredRoles) {
      return can.hasAnyRole(routeMeta.requiredRoles)
    }

    return true
  }
</script>

<style scoped>
  .main-navigation {
    display: flex;
    align-items: center;
  }
</style>
