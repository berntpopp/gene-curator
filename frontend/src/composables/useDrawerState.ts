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
import type { ComputedRef, Ref, WritableComputedRef } from 'vue'

export interface UseDrawerStateReturn {
  isOpen: WritableComputedRef<boolean>
  open: () => void
  close: () => void
  toggle: () => void
  drawerId: Readonly<Ref<string>>
}

export interface UseGlobalDrawerStateReturn {
  closeAll: () => void
  getActiveDrawer: ComputedRef<string | null>
  hasOpenDrawer: ComputedRef<boolean>
  getRegisteredDrawers: ComputedRef<string[]>
}

/**
 * Shared state for drawer management across components
 * Using module-level state for singleton pattern
 */
const activeDrawerId = ref<string | null>(null)
const drawerRegistry = ref(new Map<string, { id: string }>())

/**
 * Create a drawer state manager
 *
 * @param drawerId - Unique identifier for this drawer instance
 * @returns Drawer state management object
 *
 * @example
 * // In a component
 * const { isOpen, open, close, toggle } = useDrawerState('add-genes')
 *
 * // In template
 * <v-navigation-drawer v-model="isOpen">...</v-navigation-drawer>
 * <v-btn @click="toggle">Toggle Drawer</v-btn>
 */
export function useDrawerState(drawerId: string): UseDrawerStateReturn {
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
    set: (value: boolean) => {
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
  const open = (): void => {
    activeDrawerId.value = drawerId
  }

  /**
   * Close this drawer
   */
  const close = (): void => {
    if (activeDrawerId.value === drawerId) {
      activeDrawerId.value = null
    }
  }

  /**
   * Toggle this drawer open/closed
   */
  const toggle = (): void => {
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
 * @returns Global drawer state utilities
 *
 * @example
 * const { closeAll, getActiveDrawer, hasOpenDrawer } = useGlobalDrawerState()
 * closeAll() // Close all drawers
 */
export function useGlobalDrawerState(): UseGlobalDrawerStateReturn {
  /**
   * Close all drawers
   */
  const closeAll = (): void => {
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
