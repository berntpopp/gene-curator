/**
 * History composable - provides undo/redo functionality for components
 *
 * Wraps the history store with a convenient API for components.
 * Follows DRY principle by providing reusable undo/redo logic.
 *
 * @param {string} context - Unique context identifier (e.g., 'precuration-123')
 * @param {Function} applyState - Function to apply state to component (optional)
 * @returns {Object} History state and methods
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
import { useHistoryStore } from '@/stores/history'
import { useLogger } from './useLogger'

export function useHistory(context = 'default', applyState = null) {
  const historyStore = useHistoryStore()
  const logger = useLogger()

  // Initialize context
  historyStore.initContext(context)

  /**
   * Computed properties for button states
   */
  const canUndo = computed(() => historyStore.canUndo(context))
  const canRedo = computed(() => historyStore.canRedo(context))
  const historySize = computed(() => historyStore.getHistorySize(context))

  /**
   * Record an action in history
   *
   * @param {string} action - Action description
   * @param {*} previousState - State before action
   * @param {*} newState - State after action
   */
  function recordAction(action, previousState, newState) {
    // Skip if states are identical (avoid unnecessary history entries)
    if (JSON.stringify(previousState) === JSON.stringify(newState)) {
      return
    }

    historyStore.pushState(context, action, previousState, newState)
  }

  /**
   * Undo last action
   * Optionally applies state if applyState function provided
   *
   * @returns {*} Previous state, or null if nothing to undo
   */
  function undo() {
    const previousState = historyStore.undo(context)

    if (previousState && applyState) {
      try {
        applyState(previousState)
      } catch (error) {
        logger.error('Failed to apply undo state', { context, error: error.message })
      }
    }

    return previousState
  }

  /**
   * Redo last undone action
   * Optionally applies state if applyState function provided
   *
   * @returns {*} New state, or null if nothing to redo
   */
  function redo() {
    const newState = historyStore.redo(context)

    if (newState && applyState) {
      try {
        applyState(newState)
      } catch (error) {
        logger.error('Failed to apply redo state', { context, error: error.message })
      }
    }

    return newState
  }

  /**
   * Clear history for this context
   * Call when form is submitted or component unmounted
   */
  function clearHistory() {
    historyStore.clearHistory(context)
  }

  /**
   * Get state summary (for debugging)
   * @returns {Object}
   */
  function getStateSummary() {
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
