/**
 * useResponsive Composable
 *
 * Provides reactive responsive breakpoint detection for mobile-first design.
 * Uses matchMedia API for efficient browser-native detection.
 *
 * Benefits:
 * - Performance: Uses matchMedia (more efficient than resize events)
 * - SSR-safe: Handles server-side rendering gracefully
 * - Configurable: Breakpoints can be customized
 * - Type-safe: Returns typed breakpoint information
 *
 * @example
 * ```vue
 * <template>
 *   <v-app-bar-nav-icon v-if="isMobile" @click="openDrawer" />
 *   <MainNavigation v-else />
 * </template>
 *
 * <script setup>
 * import { useResponsive } from '@/composables/useResponsive'
 * const { isMobile, isTablet, isDesktop } = useResponsive()
 * </script>
 * ```
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#mobile-first-design-day-1
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { NAVIGATION_CONFIG } from '@/config/navigation'

/**
 * Default breakpoint configuration (in pixels)
 * Matches Vuetify's default breakpoints for consistency
 */
const DEFAULT_BREAKPOINTS = {
  mobile: NAVIGATION_CONFIG.MOBILE_BREAKPOINT, // 768px
  tablet: NAVIGATION_CONFIG.TABLET_BREAKPOINT // 1024px
  // desktop is anything above tablet
}

/**
 * Responsive breakpoint detection composable
 * @param {Object} [customBreakpoints] - Optional custom breakpoints
 * @returns {Object} Reactive breakpoint state
 */
export function useResponsive(customBreakpoints = {}) {
  const breakpoints = { ...DEFAULT_BREAKPOINTS, ...customBreakpoints }

  // Window width state
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)

  // Media query listeners for better performance
  const mediaQueries = ref({})
  const mediaQueryListeners = ref({})

  /**
   * Update window width
   */
  const updateWidth = () => {
    if (typeof window !== 'undefined') {
      windowWidth.value = window.innerWidth
    }
  }

  /**
   * Setup media query listeners
   * More performant than resize event listeners
   */
  const setupMediaQueries = () => {
    if (typeof window === 'undefined' || !window.matchMedia) {
      return
    }

    // Mobile query
    const mobileQuery = window.matchMedia(`(max-width: ${breakpoints.mobile - 1}px)`)
    const mobileListener = e => {
      if (e.matches) {
        updateWidth()
      }
    }
    mobileQuery.addEventListener('change', mobileListener)
    mediaQueries.value.mobile = mobileQuery
    mediaQueryListeners.value.mobile = mobileListener

    // Tablet query
    const tabletQuery = window.matchMedia(
      `(min-width: ${breakpoints.mobile}px) and (max-width: ${breakpoints.tablet - 1}px)`
    )
    const tabletListener = e => {
      if (e.matches) {
        updateWidth()
      }
    }
    tabletQuery.addEventListener('change', tabletListener)
    mediaQueries.value.tablet = tabletQuery
    mediaQueryListeners.value.tablet = tabletListener

    // Desktop query
    const desktopQuery = window.matchMedia(`(min-width: ${breakpoints.tablet}px)`)
    const desktopListener = e => {
      if (e.matches) {
        updateWidth()
      }
    }
    desktopQuery.addEventListener('change', desktopListener)
    mediaQueries.value.desktop = desktopQuery
    mediaQueryListeners.value.desktop = desktopListener
  }

  /**
   * Cleanup media query listeners
   */
  const cleanupMediaQueries = () => {
    if (typeof window === 'undefined' || !window.matchMedia) {
      return
    }

    Object.keys(mediaQueries.value).forEach(key => {
      const query = mediaQueries.value[key]
      const listener = mediaQueryListeners.value[key]
      if (query && listener) {
        query.removeEventListener('change', listener)
      }
    })
  }

  // Computed breakpoint flags
  const isMobile = computed(() => windowWidth.value < breakpoints.mobile)
  const isTablet = computed(
    () => windowWidth.value >= breakpoints.mobile && windowWidth.value < breakpoints.tablet
  )
  const isDesktop = computed(() => windowWidth.value >= breakpoints.tablet)

  // Computed device type string
  const deviceType = computed(() => {
    if (isMobile.value) return 'mobile'
    if (isTablet.value) return 'tablet'
    return 'desktop'
  })

  // Touch device detection
  const isTouchDevice = computed(() => {
    if (typeof window === 'undefined') return false
    return (
      'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0
    )
  })

  // Orientation detection
  const isPortrait = computed(() => {
    if (typeof window === 'undefined') return true
    return window.innerHeight > window.innerWidth
  })

  const isLandscape = computed(() => !isPortrait.value)

  /**
   * Check if viewport matches a specific breakpoint
   * @param {string} breakpoint - 'mobile', 'tablet', or 'desktop'
   * @returns {boolean} True if matches
   */
  const matches = breakpoint => {
    switch (breakpoint.toLowerCase()) {
      case 'mobile':
        return isMobile.value
      case 'tablet':
        return isTablet.value
      case 'desktop':
        return isDesktop.value
      default:
        return false
    }
  }

  /**
   * Check if viewport is at least a specific breakpoint
   * @param {string} breakpoint - 'mobile', 'tablet', or 'desktop'
   * @returns {boolean} True if at least this breakpoint
   */
  const atLeast = breakpoint => {
    const value = windowWidth.value
    switch (breakpoint.toLowerCase()) {
      case 'mobile':
        return true // Always at least mobile
      case 'tablet':
        return value >= breakpoints.mobile
      case 'desktop':
        return value >= breakpoints.tablet
      default:
        return false
    }
  }

  /**
   * Check if viewport is at most a specific breakpoint
   * @param {string} breakpoint - 'mobile', 'tablet', or 'desktop'
   * @returns {boolean} True if at most this breakpoint
   */
  const atMost = breakpoint => {
    const value = windowWidth.value
    switch (breakpoint.toLowerCase()) {
      case 'mobile':
        return value < breakpoints.mobile
      case 'tablet':
        return value < breakpoints.tablet
      case 'desktop':
        return true // Always at most desktop (no upper bound)
      default:
        return false
    }
  }

  // Lifecycle hooks
  onMounted(() => {
    if (typeof window !== 'undefined') {
      // Initial width
      updateWidth()

      // Setup media query listeners (more performant)
      setupMediaQueries()

      // Fallback to resize listener if matchMedia not supported
      if (!window.matchMedia) {
        window.addEventListener('resize', updateWidth)
      }
    }
  })

  onUnmounted(() => {
    if (typeof window !== 'undefined') {
      // Cleanup media query listeners
      cleanupMediaQueries()

      // Cleanup resize listener if used
      if (!window.matchMedia) {
        window.removeEventListener('resize', updateWidth)
      }
    }
  })

  return {
    // Window state
    windowWidth,

    // Breakpoint flags
    isMobile,
    isTablet,
    isDesktop,
    deviceType,

    // Device capabilities
    isTouchDevice,
    isPortrait,
    isLandscape,

    // Utility methods
    matches,
    atLeast,
    atMost,

    // Breakpoint values (for reference)
    breakpoints: computed(() => breakpoints)
  }
}

export default useResponsive
