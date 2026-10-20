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

// Route meta fields are typed via the RouteMeta augmentation in @/router

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
  ] as { after: string; label: string }[]
}

/**
 * Feature flags for gradual rollout
 */
export const FEATURE_FLAGS: Record<
  'NEW_NAVIGATION' | 'MOBILE_BOTTOM_NAV' | 'NOTIFICATIONS' | 'BREADCRUMBS' | 'INTERACTIVE_TOUR',
  boolean
> = {
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
 * @param featureName - Name of the feature flag
 * @returns True if feature is enabled
 */
export function isFeatureEnabled(featureName: keyof typeof FEATURE_FLAGS): boolean {
  return FEATURE_FLAGS[featureName] ?? false
}

export default {
  NAVIGATION_CONFIG,
  STATIC_NAV_ITEMS,
  MENU_DIVIDERS,
  FEATURE_FLAGS,
  isFeatureEnabled
}
