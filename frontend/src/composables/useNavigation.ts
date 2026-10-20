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
 * <script setup lang="ts">
 * import { useNavigation } from '@/composables/useNavigation'
 * const { mainMenuItems, userMenuItems } = useNavigation()
 * </script>
 * ```
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#centralized-configuration-dry
 */

import { computed } from 'vue'
import type { ComputedRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteRecordName, RouteRecordNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePermissions } from '@/composables/usePermissions'

/** Route meta fields read by the navigation system (router meta is untyped). */
export interface NavRouteMeta {
  requiresAuth?: boolean
  requiresGuest?: boolean
  requiredRoles?: string[]
  title?: string
  ariaLabel?: string
  menuLabel?: string
  icon?: string
  badge?: string | number
  badgeColor?: string
  dividerBefore?: boolean
  dividerAfter?: boolean
  menuOrder?: number
  menuChildren?: NavMenuChild[]
  showInMainMenu?: boolean
  showInUserMenu?: boolean
  breadcrumb?: string
  hideBreadcrumb?: boolean
  isDefaultLandingPage?: boolean
}

export interface NavMenuChild {
  name?: RouteRecordName | null
}

/** Static or route-derived menu entry. */
export interface NavMenuItem {
  name: RouteRecordName | null | undefined
  title: string | RouteRecordName | null
  to: { name: RouteRecordName | null | undefined }
  icon?: string
  badge?: string | number
  badgeColor: string
  dividerBefore: boolean
  dividerAfter: boolean
  order: number
  ariaLabel: string | RouteRecordName | null
  children: NavMenuChild[]
}

/** Static submenu entry (curation, help, admin). */
export interface NavLinkItem {
  name: string
  title: string
  to: { name: string }
  icon: string
  order: number
  dividerBefore?: boolean
}

export interface NavBreadcrumb {
  name: string | RouteRecordName | null | undefined
  to: { name: RouteRecordName | null | undefined }
  disabled: boolean
}

export interface UseNavigationReturn {
  mainMenuItems: ComputedRef<NavMenuItem[]>
  userMenuItems: ComputedRef<NavMenuItem[]>
  curationMenuItems: ComputedRef<NavLinkItem[]>
  helpMenuItems: ComputedRef<NavLinkItem[]>
  adminMenuItems: ComputedRef<NavLinkItem[]>
  hasAccess: (routeMeta: NavRouteMeta) => boolean
  isActive: (routeName: RouteRecordName | null | undefined) => boolean
  hasActiveChild: (children: NavMenuChild[] | null | undefined) => boolean
  breadcrumbs: ComputedRef<NavBreadcrumb[]>
  defaultLandingPage: ComputedRef<{ name: RouteRecordName | null | undefined }>
  routeToMenuItem: (route: RouteRecordNormalized) => NavMenuItem
}

/**
 * Navigation menu generation composable
 */
export function useNavigation(): UseNavigationReturn {
  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()
  const { can } = usePermissions()

  /**
   * Check if user has access to a route
   * @param routeMeta - Route meta object
   * @returns True if user has access
   */
  const hasAccess = (routeMeta: NavRouteMeta): boolean => {
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
   * @param menuRoute - Vue Router route record
   * @returns Menu item object
   */
  const routeToMenuItem = (menuRoute: RouteRecordNormalized): NavMenuItem => {
    const meta = (menuRoute.meta || {}) as NavRouteMeta

    return {
      name: menuRoute.name,
      title: meta.menuLabel || meta.title || menuRoute.name,
      to: { name: menuRoute.name },
      icon: meta.icon,
      badge: meta.badge,
      badgeColor: meta.badgeColor || 'error',
      dividerBefore: meta.dividerBefore || false,
      dividerAfter: meta.dividerAfter || false,
      order: meta.menuOrder || 999,
      ariaLabel: meta.ariaLabel || meta.title || menuRoute.name,
      children: meta.menuChildren || []
    }
  }

  /** Route records whose meta flag is set, filtered by access and mapped to menu items */
  const routeMenuItems = (flag: 'showInMainMenu' | 'showInUserMenu'): NavMenuItem[] =>
    router
      .getRoutes()
      .filter(menuRoute => (menuRoute.meta as NavRouteMeta | undefined)?.[flag] === true)
      .filter(menuRoute => hasAccess(menuRoute.meta as NavRouteMeta))
      .map(menuRoute => routeToMenuItem(menuRoute))
      .sort((a, b) => a.order - b.order)

  /**
   * Main navigation menu items (top navigation bar)
   * Only includes routes with showInMainMenu: true
   */
  const mainMenuItems = computed<NavMenuItem[]>(() => routeMenuItems('showInMainMenu'))

  /**
   * User menu items (avatar dropdown)
   * Only includes routes with showInUserMenu: true
   */
  const userMenuItems = computed<NavMenuItem[]>(() => {
    if (!authStore.isAuthenticated) {
      return []
    }

    return routeMenuItems('showInUserMenu')
  })

  /** Keep static submenu entries whose target route exists and is accessible */
  const accessibleLinks = (items: NavLinkItem[]): NavLinkItem[] =>
    items
      .filter(item => {
        // Check if route exists
        const routeExists = router.hasRoute(item.to.name)
        if (!routeExists) return false

        // Check permissions for route
        const resolved = router.resolve(item.to)
        return hasAccess(resolved.meta as NavRouteMeta)
      })
      .sort((a, b) => a.order - b.order)

  /**
   * Curation submenu items
   * Items shown in the Curation dropdown
   */
  const curationMenuItems = computed<NavLinkItem[]>(() => {
    if (!can.viewCurations.value) {
      return []
    }

    // Define curation menu structure
    // This could also come from routes with showInCurationMenu: true
    return accessibleLinks([
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
    ])
  })

  /**
   * Help submenu items
   * Items shown in the Help dropdown
   */
  const helpMenuItems = computed<NavLinkItem[]>(() => {
    return accessibleLinks([
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
    ])
  })

  /**
   * Admin submenu items
   * Items shown in the admin section of user menu
   */
  const adminMenuItems = computed<NavLinkItem[]>(() => {
    if (!can.viewAdminPages.value) {
      return []
    }

    return accessibleLinks([
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
    ])
  })

  /**
   * Check if a route is currently active
   * @param routeName - Route name to check
   * @returns True if route is active
   */
  const isActive = (routeName: RouteRecordName | null | undefined): boolean => {
    return route.name === routeName
  }

  /**
   * Check if any child route is active
   * @param children - Array of child menu items
   * @returns True if any child is active
   */
  const hasActiveChild = (children: NavMenuChild[] | null | undefined): boolean => {
    if (!children || children.length === 0) return false
    return children.some(child => isActive(child.name))
  }

  /**
   * Get breadcrumb trail for current route
   */
  const breadcrumbs = computed<NavBreadcrumb[]>(() => {
    const crumbs: NavBreadcrumb[] = []

    // Always start with home
    crumbs.push({
      name: 'Home',
      to: { name: 'Home' },
      disabled: false
    })

    // Get matched routes (parent to child)
    const matched = route.matched

    matched.forEach((matchedRoute, index) => {
      const meta = matchedRoute.meta as NavRouteMeta | undefined

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
   */
  const defaultLandingPage = computed<{ name: RouteRecordName | null | undefined }>(() => {
    const landingRoute = router
      .getRoutes()
      .find(
        menuRoute => (menuRoute.meta as NavRouteMeta | undefined)?.isDefaultLandingPage === true
      )

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
