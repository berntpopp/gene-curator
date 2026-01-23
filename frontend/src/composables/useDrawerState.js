/**
 * Drawer State Composable
 *
 * Manages drawer state to ensure only one drawer is open at a time.
 * Implements single-open-drawer pattern for better UX.
 *
 * @module composables/useDrawerState
 * @see plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */

import { ref, computed, readonly } from 'vue'

/**
 * Shared state for drawer management across components
 * Using module-level state for singleton pattern
 */
const activeDrawerId = ref(null)
const drawerRegistry = ref(new Map())

/**
 * Create a drawer state manager
 *
 * @param {string} drawerId - Unique identifier for this drawer instance
 * @returns {Object} Drawer state management object
 *
 * @example
 * // In a component
 * const { isOpen, open, close, toggle } = useDrawerState('add-genes')
 *
 * // In template
 * <v-navigation-drawer v-model="isOpen">...</v-navigation-drawer>
 * <v-btn @click="toggle">Toggle Drawer</v-btn>
 */
export function useDrawerState(drawerId) {
  if (!drawerId) {
    throw new Error('useDrawerState requires a unique drawerId')
  }

  // Register this drawer if not already registered
  if (!drawerRegistry.value.has(drawerId)) {
    drawerRegistry.value.set(drawerId, { id: drawerId })
  }

  /**
   * Whether this drawer is currently open
   */
  const isOpen = computed({
    get: () => activeDrawerId.value === drawerId,
    set: value => {
      if (value) {
        activeDrawerId.value = drawerId
      } else if (activeDrawerId.value === drawerId) {
        activeDrawerId.value = null
      }
    }
  })

  /**
   * Open this drawer (closes any other open drawer)
   */
  const open = () => {
    activeDrawerId.value = drawerId
  }

  /**
   * Close this drawer
   */
  const close = () => {
    if (activeDrawerId.value === drawerId) {
      activeDrawerId.value = null
    }
  }

  /**
   * Toggle this drawer open/closed
   */
  const toggle = () => {
    if (activeDrawerId.value === drawerId) {
      activeDrawerId.value = null
    } else {
      activeDrawerId.value = drawerId
    }
  }

  return {
    isOpen,
    open,
    close,
    toggle,
    drawerId: readonly(ref(drawerId))
  }
}

/**
 * Get global drawer state management utilities
 *
 * @returns {Object} Global drawer state utilities
 *
 * @example
 * const { closeAll, getActiveDrawer, hasOpenDrawer } = useGlobalDrawerState()
 * closeAll() // Close all drawers
 */
export function useGlobalDrawerState() {
  /**
   * Close all drawers
   */
  const closeAll = () => {
    activeDrawerId.value = null
  }

  /**
   * Get the currently active drawer ID
   */
  const getActiveDrawer = computed(() => activeDrawerId.value)

  /**
   * Check if any drawer is currently open
   */
  const hasOpenDrawer = computed(() => activeDrawerId.value !== null)

  /**
   * Get all registered drawer IDs
   */
  const getRegisteredDrawers = computed(() => Array.from(drawerRegistry.value.keys()))

  return {
    closeAll,
    getActiveDrawer,
    hasOpenDrawer,
    getRegisteredDrawers
  }
}

export default {
  useDrawerState,
  useGlobalDrawerState
}
