/**
 * Form recovery composable - auto-saves to localStorage and offers recovery
 *
 * Prevents data loss from browser crashes, tab closures, or navigation.
 * Follows best practices: KISS (simple save/restore), DRY (reusable), SOLID (single responsibility)
 *
 * Best practices implemented:
 * - Only saves when form has meaningful data (dirty checking)
 * - Only shows recovery dialog when recovered data is non-empty
 * - Pauses auto-save after discard to prevent immediate re-save of empty state
 * - Clear on successful submission
 *
 * @param {string} formId - Unique form identifier (e.g., 'precuration-new', 'curation-123')
 * @param {Ref} formData - Reactive form data reference
 * @param {Object} options - Configuration options
 * @param {number} options.maxAge - Maximum age of recovery data in milliseconds (default: 24h)
 * @param {number} options.saveInterval - Auto-save interval in milliseconds (default: 5s)
 * @returns {Object} Recovery state and methods
 *
 * @example
 * const formData = ref({ gene: '', rationale: '' })
 * const { showRecoveryDialog, lastSaved, restoreRecovery, discardRecovery, clearRecovery } =
 *   useFormRecovery('precuration-new', formData)
 */

import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useLogger } from './useLogger'

export function useFormRecovery(formId, formData, options = {}) {
  const logger = useLogger()
  const recoveryKey = `form_recovery_${formId}`
  const maxAge = options.maxAge || 24 * 60 * 60 * 1000 // 24 hours
  const saveInterval = options.saveInterval || 5000 // 5 seconds

  const showRecoveryDialog = ref(false)
  const recoveryData = ref(null)
  const recoveryTimestamp = ref(null)
  const lastSaved = ref(null)
  const isPaused = ref(false) // Pause auto-save after discard

  let saveTimer = null

  /**
   * Check if data object has meaningful (non-empty) values
   * Recursively checks nested objects and arrays
   * @param {any} data - Data to check
   * @returns {boolean} True if data has meaningful values
   */
  function hasNonEmptyData(data) {
    if (data === null || data === undefined) return false
    if (typeof data === 'string') return data.trim().length > 0
    if (typeof data === 'number' || typeof data === 'boolean') return true
    if (Array.isArray(data)) return data.length > 0 && data.some(item => hasNonEmptyData(item))
    if (typeof data === 'object') {
      const keys = Object.keys(data)
      if (keys.length === 0) return false
      return keys.some(key => hasNonEmptyData(data[key]))
    }
    return false
  }

  /**
   * Save form data to localStorage with metadata
   * Uses deep clone to avoid reactivity issues
   * Only saves if form has meaningful data
   */
  function saveToLocalStorage() {
    // Skip if paused or no meaningful data
    if (isPaused.value) {
      return
    }

    if (!hasNonEmptyData(formData.value)) {
      logger.debug('Form auto-save skipped - no meaningful data', { formId })
      return
    }

    try {
      const snapshot = {
        data: JSON.parse(JSON.stringify(formData.value)),
        timestamp: new Date().toISOString(),
        url: window.location.href,
        formId
      }
      localStorage.setItem(recoveryKey, JSON.stringify(snapshot))
      lastSaved.value = snapshot.timestamp
      logger.debug('Form auto-saved', { formId, timestamp: snapshot.timestamp })
    } catch (error) {
      // Silently fail for quota exceeded or other localStorage errors
      logger.error('Failed to save form', { formId, error: error.message })
    }
  }

  /**
   * Check for recoverable data on mount
   * Shows recovery dialog only if recent data with meaningful content found
   */
  onMounted(() => {
    try {
      const saved = localStorage.getItem(recoveryKey)
      if (saved) {
        const snapshot = JSON.parse(saved)
        const age = Date.now() - new Date(snapshot.timestamp).getTime()

        // Check if data is still valid (not expired)
        if (age < maxAge) {
          // Only offer recovery if data has meaningful content
          if (hasNonEmptyData(snapshot.data)) {
            recoveryData.value = snapshot.data
            recoveryTimestamp.value = snapshot.timestamp
            showRecoveryDialog.value = true
            logger.info('Recovery data found', {
              formId,
              age: Math.floor(age / 1000),
              timestamp: snapshot.timestamp
            })
          } else {
            // Empty data - clean up silently
            localStorage.removeItem(recoveryKey)
            logger.debug('Empty recovery data removed', { formId })
          }
        } else {
          // Stale data - clean up
          localStorage.removeItem(recoveryKey)
          logger.debug('Stale recovery data removed', { formId, age: Math.floor(age / 1000) })
        }
      }
    } catch (error) {
      logger.error('Failed to check recovery data', { formId, error: error.message })
    }

    // Start auto-save timer
    saveTimer = setInterval(saveToLocalStorage, saveInterval)
    logger.debug('Form recovery initialized', { formId, saveInterval })
  })

  /**
   * Clean up timer on unmount
   */
  onBeforeUnmount(() => {
    if (saveTimer) {
      clearInterval(saveTimer)
      logger.debug('Form recovery cleanup', { formId })
    }
  })

  /**
   * Watch for changes and save (only if has meaningful data)
   * Deep watch to catch nested property changes
   */
  watch(formData, saveToLocalStorage, { deep: true })

  /**
   * Restore recovered data into form
   * Resumes auto-save since form now has data
   */
  function restoreRecovery() {
    if (recoveryData.value) {
      Object.assign(formData.value, recoveryData.value)
      showRecoveryDialog.value = false
      isPaused.value = false // Resume auto-save
      logger.info('Form data restored', { formId, timestamp: recoveryTimestamp.value })
    }
  }

  /**
   * Discard recovery data and start fresh
   * Pauses auto-save temporarily to prevent immediate re-save of empty state
   */
  function discardRecovery() {
    localStorage.removeItem(recoveryKey)
    recoveryData.value = null
    recoveryTimestamp.value = null
    showRecoveryDialog.value = false

    // Pause auto-save temporarily to prevent immediate re-save of empty form
    // Will resume automatically when user adds meaningful data
    isPaused.value = true

    // Resume after a delay (gives user time to start typing)
    // Or rely on the dirty check in saveToLocalStorage
    setTimeout(() => {
      isPaused.value = false
      logger.debug('Auto-save resumed after discard', { formId })
    }, 10000) // 10 second grace period

    logger.info('Recovery data discarded', { formId })
  }

  /**
   * Clear recovery data on successful submit
   * Call this after form is successfully submitted
   */
  function clearRecovery() {
    localStorage.removeItem(recoveryKey)
    lastSaved.value = null
    isPaused.value = true // Prevent re-saving after submit
    logger.debug('Recovery data cleared', { formId })
  }

  /**
   * Manually resume auto-save (e.g., after navigation)
   */
  function resumeAutoSave() {
    isPaused.value = false
  }

  return {
    showRecoveryDialog,
    recoveryData,
    recoveryTimestamp,
    lastSaved,
    restoreRecovery,
    discardRecovery,
    clearRecovery,
    resumeAutoSave
  }
}
