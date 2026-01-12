/**
 * Form recovery composable - auto-saves to localStorage and offers recovery
 *
 * Prevents data loss from browser crashes, tab closures, or navigation.
 * Follows best practices: KISS (simple save/restore), DRY (reusable), SOLID (single responsibility)
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

  let saveTimer = null

  /**
   * Save form data to localStorage with metadata
   * Uses deep clone to avoid reactivity issues
   */
  function saveToLocalStorage() {
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
   * Shows recovery dialog if recent data found
   */
  onMounted(() => {
    try {
      const saved = localStorage.getItem(recoveryKey)
      if (saved) {
        const snapshot = JSON.parse(saved)
        const age = Date.now() - new Date(snapshot.timestamp).getTime()

        if (age < maxAge) {
          // Recent data found - offer recovery
          recoveryData.value = snapshot.data
          recoveryTimestamp.value = snapshot.timestamp
          showRecoveryDialog.value = true
          logger.info('Recovery data found', {
            formId,
            age: Math.floor(age / 1000),
            timestamp: snapshot.timestamp
          })
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
   * Watch for changes and save
   * Deep watch to catch nested property changes
   */
  watch(formData, saveToLocalStorage, { deep: true })

  /**
   * Restore recovered data into form
   */
  function restoreRecovery() {
    if (recoveryData.value) {
      Object.assign(formData.value, recoveryData.value)
      showRecoveryDialog.value = false
      logger.info('Form data restored', { formId, timestamp: recoveryTimestamp.value })
    }
  }

  /**
   * Discard recovery data and start fresh
   */
  function discardRecovery() {
    localStorage.removeItem(recoveryKey)
    recoveryData.value = null
    recoveryTimestamp.value = null
    showRecoveryDialog.value = false
    logger.info('Recovery data discarded', { formId })
  }

  /**
   * Clear recovery data on successful submit
   * Call this after form is successfully submitted
   */
  function clearRecovery() {
    localStorage.removeItem(recoveryKey)
    lastSaved.value = null
    logger.debug('Recovery data cleared', { formId })
  }

  return {
    showRecoveryDialog,
    recoveryData,
    recoveryTimestamp,
    lastSaved,
    restoreRecovery,
    discardRecovery,
    clearRecovery
  }
}
