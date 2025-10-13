/**
 * Navigation Configuration
 *
 * Centralized navigation configuration that will be used by composables
 * to generate menu items dynamically from route metadata.
 *
 * This file serves as documentation and exports any static navigation
 * configuration that can't be derived from routes.
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#centralized-configuration-dry
 */

/**
 * Navigation configuration constants
 */
export const NAVIGATION_CONFIG = {
  // Main menu maximum items (UX best practice)
  MAX_MAIN_MENU_ITEMS: 6,

  // Dropdown configuration
  DROPDOWN_DELAY_MS: 200,
  DROPDOWN_CLOSE_DELAY_MS: 300,

  // Mobile breakpoints (px)
  MOBILE_BREAKPOINT: 768,
  TABLET_BREAKPOINT: 1024,

  // Touch target sizes (WCAG 2.5.5)
  MIN_TOUCH_TARGET_SIZE: 44, // pixels

  // Notification badge configuration
  MAX_BADGE_COUNT: 99,
  BADGE_ANIMATION_DURATION: 300, // ms

  // Menu animation durations
  MENU_TRANSITION_DURATION: 200, // ms
  MOBILE_DRAWER_TRANSITION: 300, // ms

  // Accessibility
  FOCUS_VISIBLE_OUTLINE_WIDTH: 2, // pixels
  SKIP_LINK_Z_INDEX: 9999
}

/**
 * Route metadata schema for type checking
 * This documents the expected structure of route.meta
 *
 * @typedef {Object} RouteMeta
 * @property {string} title - Page title
 * @property {string} [icon] - MDI icon name
 * @property {string} [menuLabel] - Override title in menu
 * @property {boolean} [showInMainMenu] - Show in main navigation
 * @property {boolean} [showInUserMenu] - Show in user menu
 * @property {number} [menuOrder] - Sort order (lower first)
 * @property {string} [menuParent] - Parent menu item name
 * @property {Array} [menuChildren] - Child menu items
 * @property {boolean} [requiresAuth] - Requires authentication
 * @property {boolean} [requiresGuest] - Only for guests
 * @property {string[]} [requiredRoles] - Required roles
 * @property {string[]} [requiredScopes] - Required scopes
 * @property {boolean} [isDefaultLandingPage] - Redirect here after login
 * @property {boolean} [skipAuth] - Skip auth check
 * @property {boolean} [trackPageView] - Track in analytics
 * @property {boolean} [trackTime] - Track time on page
 * @property {string} [metaDescription] - Meta description
 * @property {string[]} [metaKeywords] - Meta keywords
 * @property {string} [ariaLabel] - ARIA label for nav item
 * @property {string} [breadcrumb] - Breadcrumb label
 * @property {boolean} [hideBreadcrumb] - Hide from breadcrumbs
 */

/**
 * Static navigation items that don't correspond to routes
 * (e.g., external links, actions)
 */
export const STATIC_NAV_ITEMS = {
  // Example: External documentation link
  // externalDocs: {
  //   name: 'external-docs',
  //   title: 'Documentation',
  //   href: 'https://docs.example.com',
  //   icon: 'mdi-book-open-variant',
  //   external: true,
  //   showInMainMenu: false,
  //   showInHelpMenu: true
  // }
}

/**
 * Menu divider configuration
 * Defines where dividers should appear in menus
 */
export const MENU_DIVIDERS = {
  userMenu: [
    { after: 'profile', label: 'Personal' },
    { after: 'validation', label: 'Tools' },
    { after: 'curation-setup', label: 'Admin' }
  ]
}

/**
 * Feature flags for gradual rollout
 */
export const FEATURE_FLAGS = {
  // New navigation system
  NEW_NAVIGATION: import.meta.env.VITE_FEATURE_NEW_NAVIGATION !== 'false',

  // Mobile bottom navigation
  MOBILE_BOTTOM_NAV: import.meta.env.VITE_FEATURE_MOBILE_BOTTOM_NAV !== 'false',

  // Notification system
  NOTIFICATIONS: import.meta.env.VITE_FEATURE_NOTIFICATIONS !== 'false',

  // Breadcrumbs
  BREADCRUMBS: import.meta.env.VITE_FEATURE_BREADCRUMBS !== 'false',

  // Interactive tour
  INTERACTIVE_TOUR: import.meta.env.VITE_FEATURE_INTERACTIVE_TOUR === 'true'
}

/**
 * Check if a feature is enabled
 * @param {string} featureName - Name of the feature flag
 * @returns {boolean} True if feature is enabled
 */
export function isFeatureEnabled(featureName) {
  return FEATURE_FLAGS[featureName] ?? false
}

export default {
  NAVIGATION_CONFIG,
  STATIC_NAV_ITEMS,
  MENU_DIVIDERS,
  FEATURE_FLAGS,
  isFeatureEnabled
}
