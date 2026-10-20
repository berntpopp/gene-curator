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
          :badge="item.badge"
          :badge-color="item.badgeColor"
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

<script setup lang="ts">
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

  import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
  import { useRouter, type RouteRecordNormalized } from 'vue-router'
  import { storeToRefs } from 'pinia'
  import { useAuthStore } from '@/stores/auth'
  import { useWorkflowStore } from '@/stores/workflow'
  import { TERMINOLOGY } from '@/config/terminology'
  import BaseNavigationItem from './BaseNavigationItem.vue'

  // Route meta is untyped in vue-router here; these are the keys this menu reads
  interface NavRouteMeta {
    icon?: string
    label?: string
    title?: string
    order?: number
    requiresAuth?: boolean
    requiresGuest?: boolean
    requiredRoles?: string[]
    showInMainMenu?: boolean
    showInDropdown?: string
  }

  const metaOf = (route: RouteRecordNormalized): NavRouteMeta => route.meta as NavRouteMeta

  const router = useRouter()
  const authStore = useAuthStore()
  const { isAuthenticated } = storeToRefs(authStore)
  const workflowStore = useWorkflowStore()
  const pendingReviewCount = ref(0)
  let badgeRefreshInterval: ReturnType<typeof setInterval> | null = null

  async function refreshBadgeCount() {
    try {
      pendingReviewCount.value = await workflowStore.fetchPendingReviewCount()
    } catch {
      // Silent fail for badge refresh — don't break navigation
    }
  }

  function startBadgeRefresh() {
    if (!badgeRefreshInterval) {
      refreshBadgeCount()
      badgeRefreshInterval = setInterval(refreshBadgeCount, 60000)
    }
  }

  function stopBadgeRefresh() {
    if (badgeRefreshInterval) {
      clearInterval(badgeRefreshInterval)
      badgeRefreshInterval = null
    }
    pendingReviewCount.value = 0
  }

  onMounted(() => {
    if (isAuthenticated.value) {
      startBadgeRefresh()
    }
  })

  watch(isAuthenticated, newVal => {
    if (newVal) {
      startBadgeRefresh()
    } else {
      stopBadgeRefresh()
    }
  })

  onUnmounted(() => {
    stopBadgeRefresh()
  })

  /**
   * Get all routes with showInMainMenu metadata
   */
  const mainMenuItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => metaOf(route).showInMainMenu === true)
      .filter(route => hasAccess(metaOf(route)))
      .map(route => ({
        name: route.name,
        to: { name: route.name },
        icon: metaOf(route).icon,
        label: metaOf(route).label || metaOf(route).title || '',
        order: metaOf(route).order || 999
      }))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Get items for Curation dropdown
   */
  const curationItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => metaOf(route).showInDropdown === 'curation')
      .filter(route => hasAccess(metaOf(route)))
      .map(route => ({
        name: route.name,
        to: { name: route.name },
        icon: metaOf(route).icon,
        label: metaOf(route).label || metaOf(route).title || '',
        order: metaOf(route).order || 999,
        badge:
          route.name === 'review-queue' && pendingReviewCount.value > 0
            ? pendingReviewCount.value
            : null,
        badgeColor: 'warning'
      }))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Get items for Curation Setup dropdown (admin only)
   */
  const curationSetupItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => metaOf(route).showInDropdown === 'curationSetup')
      .filter(route => hasAccess(metaOf(route)))
      .map(route => ({
        name: route.name,
        to: { name: route.name },
        icon: metaOf(route).icon,
        label: metaOf(route).label || metaOf(route).title || '',
        order: metaOf(route).order || 999
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
  function hasAccess(routeMeta: NavRouteMeta | undefined) {
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
      return authStore.hasAnyRole(routeMeta.requiredRoles)
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
