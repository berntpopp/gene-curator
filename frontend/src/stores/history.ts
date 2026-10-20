/**
 * History Store - Undo/Redo functionality using Command Pattern
 *
 * Manages undo/redo state for forms and other reversible actions.
 * Follows SOLID principles: Single Responsibility (history management only)
 *
 * Design patterns:
 * - Command Pattern: Each action is encapsulated with previous/new state
 * - Memento Pattern: State snapshots for time-travel debugging
 *
 * @example
 * // In component:
 * const historyStore = useHistoryStore()
 * historyStore.pushState('form-123', 'edit', oldData, newData)
 * const previousState = historyStore.undo('form-123')
 */

import { defineStore } from 'pinia'
import { logService } from '@/services/logService'

/** One undoable change: the state before and after the action (deep-cloned). */
export interface HistoryEntry {
  action: string
  previousState: unknown
  newState: unknown
  timestamp: number
}

export interface HistoryContext {
  past: HistoryEntry[]
  future: HistoryEntry[]
}

export type HistoryStateSummary =
  | { exists: false }
  | {
      exists: true
      pastSize: number
      futureSize: number
      canUndo: boolean
      canRedo: boolean
      lastAction: string | null
    }

export const useHistoryStore = defineStore('history', {
  state: () => ({
    /**
     * Map of context -> { past: [], future: [] }
     * Allows multiple independent undo/redo stacks
     */
    contexts: new Map<string, HistoryContext>(),

    /**
     * Maximum history entries per context
     * Prevents memory leaks from long sessions
     */
    maxHistory: 50
  }),

  getters: {
    /**
     * Check if undo is available for a context
     * @param {string} context - Context identifier
     * @returns {boolean}
     */
    canUndo:
      state =>
      (context: string = 'default') => {
        const history = state.contexts.get(context)
        return history !== undefined && history.past.length > 0
      },

    /**
     * Check if redo is available for a context
     * @param {string} context - Context identifier
     * @returns {boolean}
     */
    canRedo:
      state =>
      (context: string = 'default') => {
        const history = state.contexts.get(context)
        return history !== undefined && history.future.length > 0
      },

    /**
     * Get history size for a context
     * @param {string} context - Context identifier
     * @returns {number}
     */
    getHistorySize:
      state =>
      (context: string = 'default') => {
        const history = state.contexts.get(context)
        return history ? history.past.length : 0
      },

    /**
     * Get all contexts (for debugging)
     * @returns {Array<string>}
     */
    getAllContexts: state => {
      return Array.from(state.contexts.keys())
    }
  },

  actions: {
    /**
     * Initialize a new context if it doesn't exist
     * @param {string} context - Context identifier
     */
    initContext(context: string) {
      if (!this.contexts.has(context)) {
        this.contexts.set(context, {
          past: [],
          future: []
        })
        logService.debug('History context initialized', { context })
      }
    },

    /**
     * Push a new state to history
     * Invalidates future (redo) stack
     *
     * @param {string} context - Context identifier
     * @param {string} action - Action description (e.g., 'edit', 'delete', 'add')
     * @param {*} previousState - State before the action
     * @param {*} newState - State after the action
     */
    pushState(context: string, action: string, previousState: unknown, newState: unknown) {
      this.initContext(context)
      const history = this.contexts.get(context)
      if (!history) return

      // Create deep clones to prevent mutation issues
      const entry: HistoryEntry = {
        action,
        previousState: JSON.parse(JSON.stringify(previousState)),
        newState: JSON.parse(JSON.stringify(newState)),
        timestamp: Date.now()
      }

      history.past.push(entry)

      // Limit history size (FIFO)
      if (history.past.length > this.maxHistory) {
        history.past.shift()
        logService.debug('History limit reached, removed oldest entry', { context })
      }

      // Clear future (new action invalidates redo)
      history.future = []

      logService.debug('History state pushed', {
        context,
        action,
        pastSize: history.past.length
      })
    },

    /**
     * Undo last action
     * Moves entry from past to future
     *
     * @param {string} context - Context identifier
     * @returns {*} Previous state, or null if nothing to undo
     */
    undo(context: string = 'default'): unknown {
      const history = this.contexts.get(context)

      if (!history || history.past.length === 0) {
        logService.warn('Undo called but no history available', { context })
        return null
      }

      const entry = history.past.pop()
      if (!entry) return null
      history.future.push(entry)

      logService.info('Undo action', {
        context,
        action: entry.action,
        remainingPast: history.past.length
      })

      return entry.previousState
    },

    /**
     * Redo last undone action
     * Moves entry from future back to past
     *
     * @param {string} context - Context identifier
     * @returns {*} New state, or null if nothing to redo
     */
    redo(context: string = 'default'): unknown {
      const history = this.contexts.get(context)

      if (!history || history.future.length === 0) {
        logService.warn('Redo called but no future available', { context })
        return null
      }

      const entry = history.future.pop()
      if (!entry) return null
      history.past.push(entry)

      logService.info('Redo action', {
        context,
        action: entry.action,
        remainingFuture: history.future.length
      })

      return entry.newState
    },

    /**
     * Clear all history for a context
     * Useful when submitting a form or navigating away
     *
     * @param {string} context - Context identifier
     */
    clearHistory(context: string = 'default') {
      this.contexts.delete(context)
      logService.debug('History cleared', { context })
    },

    /**
     * Clear all contexts (cleanup on logout)
     */
    clearAllHistory() {
      const contextCount = this.contexts.size
      this.contexts.clear()
      logService.info('All history cleared', { contextCount })
    },

    /**
     * Get current state summary (for debugging)
     * @param {string} context - Context identifier
     * @returns {Object} State summary
     */
    getStateSummary(context: string = 'default'): HistoryStateSummary {
      const history = this.contexts.get(context)

      if (!history) {
        return { exists: false }
      }

      return {
        exists: true,
        pastSize: history.past.length,
        futureSize: history.future.length,
        canUndo: history.past.length > 0,
        canRedo: history.future.length > 0,
        lastAction: history.past[history.past.length - 1]?.action || null
      }
    }
  }
})
