/**
 * useNavigation Composable
 *
 * Auto-generates navigation menus from route metadata.
 * This is the core of the DRY navigation system - routes define everything,
 * and menus are generated automatically.
 *
 * Benefits:
 * - DRY: Single source of truth (routes)
 * - Type-safe: Routes already define metadata
 * - Maintainable: Add route = add menu item automatically
 * - Testable: Pure functions, easy to mock
 *
 * @example
 * ```vue
 * <template>
 *   <v-list>
 *     <v-list-item
 *       v-for="item in mainMenuItems"
 *       :key="item.name"
 *       :to="item.to"
 *     >
 *       {{ item.title }}
 *     </v-list-item>
 *   </v-list>
 * </template>
 *
 * <script setup>
 * import { useNavigation } from '@/composables/useNavigation'
 * const { mainMenuItems, userMenuItems } = useNavigation()
 * </script>
 * ```
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#centralized-configuration-dry
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePermissions } from '@/composables/usePermissions'

/**
 * Navigation menu generation composable
 * @returns {Object} Navigation utilities and menu items
 */
export function useNavigation() {
  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()
  const { can } = usePermissions()

  /**
   * Check if user has access to a route
   * @param {Object} routeMeta - Route meta object
   * @returns {boolean} True if user has access
   */
  const hasAccess = routeMeta => {
    // Check authentication requirement
    if (routeMeta.requiresAuth && !authStore.isAuthenticated) {
      return false
    }

    // Check guest-only routes (login, register)
    if (routeMeta.requiresGuest && authStore.isAuthenticated) {
      return false
    }

    // Check role requirements
    if (routeMeta.requiredRoles && routeMeta.requiredRoles.length > 0) {
      const hasRequiredRole = routeMeta.requiredRoles.some(role => authStore.hasRole(role))
      if (!hasRequiredRole) {
        return false
      }
    }

    return true
  }

  /**
   * Convert route to menu item
   * @param {Object} route - Vue Router route object
   * @returns {Object} Menu item object
   */
  const routeToMenuItem = route => {
    const meta = route.meta || {}

    return {
      name: route.name,
      title: meta.menuLabel || meta.title || route.name,
      to: { name: route.name },
      icon: meta.icon,
      badge: meta.badge,
      badgeColor: meta.badgeColor || 'error',
      dividerBefore: meta.dividerBefore || false,
      dividerAfter: meta.dividerAfter || false,
      order: meta.menuOrder || 999,
      ariaLabel: meta.ariaLabel || meta.title || route.name,
      children: meta.menuChildren || []
    }
  }

  /**
   * Main navigation menu items (top navigation bar)
   * Only includes routes with showInMainMenu: true
   */
  const mainMenuItems = computed(() => {
    return router
      .getRoutes()
      .filter(route => route.meta?.showInMainMenu === true)
      .filter(route => hasAccess(route.meta))
      .map(route => routeToMenuItem(route))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * User menu items (avatar dropdown)
   * Only includes routes with showInUserMenu: true
   */
  const userMenuItems = computed(() => {
    if (!authStore.isAuthenticated) {
      return []
    }

    return router
      .getRoutes()
      .filter(route => route.meta?.showInUserMenu === true)
      .filter(route => hasAccess(route.meta))
      .map(route => routeToMenuItem(route))
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Curation submenu items
   * Items shown in the Curation dropdown
   */
  const curationMenuItems = computed(() => {
    if (!can.viewCurations.value) {
      return []
    }

    // Define curation menu structure
    // This could also come from routes with showInCurationMenu: true
    return [
      {
        name: 'assignments',
        title: 'Assignments',
        to: { name: 'GeneAssignments' },
        icon: 'mdi-clipboard-text',
        order: 1
      },
      {
        name: 'new-assignment',
        title: 'New Assignment',
        to: { name: 'ScopeSelection' },
        icon: 'mdi-plus-circle',
        order: 2
      },
      {
        name: 'precurations',
        title: 'Precurations',
        to: { name: 'Precurations' },
        icon: 'mdi-file-document-edit-outline',
        order: 3
      },
      {
        name: 'curations',
        title: 'Curations',
        to: { name: 'Curations' },
        icon: 'mdi-file-check-outline',
        order: 4
      },
      {
        name: 'validation',
        title: 'Validation',
        to: { name: 'ValidationDashboard' },
        icon: 'mdi-check-decagram',
        order: 5,
        dividerBefore: true
      }
    ]
      .filter(item => {
        // Check if route exists
        const routeExists = router.hasRoute(item.to.name)
        if (!routeExists) return false

        // Check permissions for route
        const route = router.resolve(item.to)
        return hasAccess(route.meta)
      })
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Help submenu items
   * Items shown in the Help dropdown
   */
  const helpMenuItems = computed(() => {
    return [
      {
        name: 'documentation',
        title: 'Documentation',
        to: { name: 'About' }, // TODO: Create proper docs page
        icon: 'mdi-book-open-variant',
        order: 1
      },
      {
        name: 'faq',
        title: 'FAQ',
        to: { name: 'FAQ' },
        icon: 'mdi-frequently-asked-questions',
        order: 2
      },
      {
        name: 'about',
        title: 'About',
        to: { name: 'About' },
        icon: 'mdi-information',
        order: 3
      }
    ]
      .filter(item => {
        const routeExists = router.hasRoute(item.to.name)
        if (!routeExists) return false

        const route = router.resolve(item.to)
        return hasAccess(route.meta)
      })
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Admin submenu items
   * Items shown in the admin section of user menu
   */
  const adminMenuItems = computed(() => {
    if (!can.viewAdminPages.value) {
      return []
    }

    return [
      {
        name: 'user-management',
        title: 'User Management',
        to: { name: 'UserManagement' },
        icon: 'mdi-account-group',
        order: 1
      },
      {
        name: 'gene-management',
        title: 'Gene Management',
        to: { name: 'GeneAdmin' },
        icon: 'mdi-dna',
        order: 2
      },
      {
        name: 'schema-management',
        title: 'Curation Setup',
        to: { name: 'SchemaManagement' },
        icon: 'mdi-cog',
        order: 3
      }
    ]
      .filter(item => {
        const routeExists = router.hasRoute(item.to.name)
        if (!routeExists) return false

        const route = router.resolve(item.to)
        return hasAccess(route.meta)
      })
      .sort((a, b) => a.order - b.order)
  })

  /**
   * Check if a route is currently active
   * @param {string} routeName - Route name to check
   * @returns {boolean} True if route is active
   */
  const isActive = routeName => {
    return route.name === routeName
  }

  /**
   * Check if any child route is active
   * @param {Array} children - Array of child menu items
   * @returns {boolean} True if any child is active
   */
  const hasActiveChild = children => {
    if (!children || children.length === 0) return false
    return children.some(child => isActive(child.name))
  }

  /**
   * Get breadcrumb trail for current route
   * @returns {Array} Array of breadcrumb items
   */
  const breadcrumbs = computed(() => {
    const crumbs = []

    // Always start with home
    crumbs.push({
      name: 'Home',
      to: { name: 'Home' },
      disabled: false
    })

    // Get matched routes (parent to child)
    const matched = route.matched

    matched.forEach((matchedRoute, index) => {
      const meta = matchedRoute.meta

      // Skip if explicitly hidden
      if (meta?.hideBreadcrumb) return

      // Skip last item (current page) - it's not clickable
      const isLast = index === matched.length - 1

      crumbs.push({
        name: meta?.breadcrumb || meta?.title || matchedRoute.name,
        to: { name: matchedRoute.name },
        disabled: isLast
      })
    })

    return crumbs
  })

  /**
   * Get default landing page for authenticated users
   * @returns {Object} Route object
   */
  const defaultLandingPage = computed(() => {
    const landingRoute = router.getRoutes().find(route => route.meta?.isDefaultLandingPage === true)

    return landingRoute ? { name: landingRoute.name } : { name: 'Dashboard' }
  })

  return {
    // Menu items
    mainMenuItems,
    userMenuItems,
    curationMenuItems,
    helpMenuItems,
    adminMenuItems,

    // Utilities
    hasAccess,
    isActive,
    hasActiveChild,
    breadcrumbs,
    defaultLandingPage,

    // For testing and debugging
    routeToMenuItem
  }
}

export default useNavigation
