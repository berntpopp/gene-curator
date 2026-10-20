/**
 * History composable - provides undo/redo functionality for components
 *
 * Wraps the history store with a convenient API for components.
 * Follows DRY principle by providing reusable undo/redo logic.
 *
 * @example
 * // In component:
 * const { canUndo, canRedo, recordAction, undo, redo } = useHistory(
 *   'curation-form',
 *   (state) => { formData.value = state }
 * )
 *
 * // Record changes
 * watch(formData, (newVal, oldVal) => {
 *   recordAction('edit', oldVal, newVal)
 * }, { deep: true })
 *
 * // Undo/Redo
 * <v-btn @click="undo" :disabled="!canUndo">Undo</v-btn>
 */

import { computed } from 'vue'
import type { ComputedRef } from 'vue'
import { useHistoryStore } from '@/stores/history'
import { useLogger } from './useLogger'

export interface HistoryStateSummary {
  canUndo: boolean
  canRedo: boolean
  lastAction: string | null
}

export interface UseHistoryReturn<T> {
  canUndo: ComputedRef<boolean>
  canRedo: ComputedRef<boolean>
  historySize: ComputedRef<number>
  recordAction: (action: string, previousState: T, newState: T) => void
  undo: () => T | null
  redo: () => T | null
  clearHistory: () => void
  getStateSummary: () => HistoryStateSummary | null
}

/** Subset of the JS history store used here (its getter typings are not precise). */
interface HistoryStoreApi {
  initContext: (context: string) => void
  canUndo: (context: string) => boolean
  canRedo: (context: string) => boolean
  getHistorySize: (context: string) => number
  pushState: (context: string, action: string, previous: unknown, next: unknown) => void
  undo: (context: string) => unknown
  redo: (context: string) => unknown
  clearHistory: (context: string) => void
  getStateSummary: (context: string) => HistoryStateSummary | null
}

export function useHistory<T = unknown>(
  context = 'default',
  applyState: ((state: T) => void) | null = null
): UseHistoryReturn<T> {
  const historyStore = useHistoryStore() as unknown as HistoryStoreApi
  const logger = useLogger()

  // Initialize context
  historyStore.initContext(context)

  /**
   * Computed properties for button states
   */
  const canUndo = computed<boolean>(() => historyStore.canUndo(context))
  const canRedo = computed<boolean>(() => historyStore.canRedo(context))
  const historySize = computed<number>(() => historyStore.getHistorySize(context))

  /**
   * Record an action in history
   * Skips the entry when previous and new states serialize identically
   */
  function recordAction(action: string, previousState: T, newState: T): void {
    if (JSON.stringify(previousState) === JSON.stringify(newState)) {
      return
    }

    historyStore.pushState(context, action, previousState, newState)
  }

  /**
   * Undo last action
   * Optionally applies state if applyState function provided
   *
   * @returns Previous state, or null if nothing to undo
   */
  function undo(): T | null {
    const previousState = historyStore.undo(context) as T | null

    if (previousState && applyState) {
      try {
        applyState(previousState)
      } catch (error) {
        logger.error('Failed to apply undo state', {
          context,
          error: error instanceof Error ? error.message : undefined
        })
      }
    }

    return previousState
  }

  /**
   * Redo last undone action
   * Optionally applies state if applyState function provided
   *
   * @returns New state, or null if nothing to redo
   */
  function redo(): T | null {
    const newState = historyStore.redo(context) as T | null

    if (newState && applyState) {
      try {
        applyState(newState)
      } catch (error) {
        logger.error('Failed to apply redo state', {
          context,
          error: error instanceof Error ? error.message : undefined
        })
      }
    }

    return newState
  }

  /**
   * Clear history for this context
   * Call when form is submitted or component unmounted
   */
  function clearHistory(): void {
    historyStore.clearHistory(context)
  }

  /**
   * Get state summary (for debugging)
   */
  function getStateSummary(): HistoryStateSummary | null {
    return historyStore.getStateSummary(context)
  }

  return {
    // State
    canUndo,
    canRedo,
    historySize,

    // Methods
    recordAction,
    undo,
    redo,
    clearHistory,
    getStateSummary
  }
}
