<template>
  <div class="user-menu">
    <!-- Login Button (when not authenticated) -->
    <v-btn v-if="!isAuthenticated" icon :to="{ name: 'Login' }">
      <v-icon>mdi-login</v-icon>
    </v-btn>

    <!-- User Menu (when authenticated) -->
    <v-menu v-else offset-y>
      <template #activator="{ props }">
        <!-- User Avatar with Notification Badge -->
        <NotificationBadge :count="totalUnread" :priority="highestPriority">
          <v-btn icon v-bind="props">
            <v-avatar size="32">
              <v-icon>mdi-account-circle</v-icon>
            </v-avatar>
          </v-btn>
        </NotificationBadge>
      </template>

      <v-list>
        <!-- User Info Header -->
        <v-list-item>
          <v-list-item-title class="font-weight-bold">
            {{ user?.email }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ roleLabel }}
          </v-list-item-subtitle>
        </v-list-item>

        <v-divider />

        <!-- Dynamic User Menu Items from Router -->
        <BaseNavigationItem
          v-for="item in userMenuItems"
          :key="item.name"
          :to="item.to"
          :icon="item.icon"
          :label="item.label"
        />

        <v-divider />

        <!-- Logout -->
        <v-list-item @click="handleLogout">
          <template #prepend>
            <v-icon>mdi-logout</v-icon>
          </template>
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
  /**
   * UserMenu Component
   *
   * Displays user menu with notification badge and dynamic menu items.
   *
   * Features:
   * - Auto-generated menu items from router
   * - Notification badge with unread count
   * - User information display
   * - Logout functionality
   * - Role-based content
   *
   * @see src/composables/useNavigation.js
   * @see src/stores/notifications.js
   */

  import { computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '@/stores/auth'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import { TERMINOLOGY } from '@/config/terminology'
  import NotificationBadge from './NotificationBadge.vue'
  import BaseNavigationItem from './BaseNavigationItem.vue'
  import type { RouteRecordNormalized } from 'vue-router'

  /** Scoped logger from useLogger(); its JSDoc types the return as Object, so it is narrowed here */
  type LogFn = (message: string, data?: Record<string, unknown>) => void
  type ComponentLogger = { debug: LogFn; info: LogFn; error: LogFn }

  type NotificationPriority = 'critical' | 'warning' | 'info'

  /** Route meta keys this menu reads (vue-router meta is untyped here) */
  interface MenuRouteMeta {
    icon?: string
    label?: string
    title?: string
    order?: number
    showInUserMenu?: boolean
    requiresAuth?: boolean
    requiredRoles?: string[]
  }

  /** Auth store user fields shown in the menu (store state is typed null) */
  interface MenuUser {
    email?: string
    role?: string
  }

  const metaOf = (route: RouteRecordNormalized): MenuRouteMeta => route.meta as MenuRouteMeta

  const router = useRouter()
  const authStore = useAuthStore()
  const notificationsStore = useNotificationsStore()
  const logger = useLogger() as ComponentLogger

  /**
   * User menu items from router
   */
  const userMenuItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => metaOf(route).showInUserMenu === true)
      .filter(route => {
        if (metaOf(route).requiresAuth && !authStore.isAuthenticated) {
          return false
        }
        const requiredRoles = metaOf(route).requiredRoles
        if (requiredRoles) {
          return authStore.hasAnyRole(requiredRoles)
        }
        return true
      })
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
   * User authentication state
   */
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const user = computed(() => authStore.user as MenuUser | null)

  /**
   * User role label
   */
  const roleLabel = computed(() => {
    const role = user.value?.role
    if (!role) return ''

    // Use terminology for consistent role names
    const roleKey = role.toUpperCase().replace(/-/g, '_')
    const terminology: Record<string, string> = TERMINOLOGY
    return terminology[roleKey] || role
  })

  /**
   * Notification counts from store
   */
  const totalUnread = computed(() => notificationsStore.totalUnread)
  // The notifications store does not define highestPriority today, so this is undefined and the badge keeps its default priority
  const highestPriority = computed(
    () => (notificationsStore as { highestPriority?: NotificationPriority }).highestPriority
  )

  /**
   * Handle user logout
   */
  async function handleLogout() {
    try {
      await authStore.logout()
      router.push({ name: 'Home' })
      logger.info('User logged out')
    } catch (error) {
      const err = error instanceof Error ? error : undefined
      logger.error('Logout error:', { error: err?.message, stack: err?.stack })
    }
  }

  /**
   * Load notifications on mount (if authenticated)
   */
  onMounted(() => {
    if (authStore.isAuthenticated) {
      notificationsStore.fetchNotifications()
    }
  })
</script>

<style scoped>
  .user-menu {
    display: flex;
    align-items: center;
  }

  .font-weight-bold {
    font-weight: 600;
  }
</style>
