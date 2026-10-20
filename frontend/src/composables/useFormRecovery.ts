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
 * @param formId - Unique form identifier (e.g., 'precuration-new', 'curation-123')
 * @param formData - Reactive form data reference
 * @param options - Configuration options
 * @param options.maxAge - Maximum age of recovery data in milliseconds (default: 24h)
 * @param options.saveInterval - Auto-save interval in milliseconds (default: 5s)
 * @returns Recovery state and methods
 *
 * @example
 * const formData = ref({ gene: '', rationale: '' })
 * const { showRecoveryDialog, lastSaved, restoreRecovery, discardRecovery, clearRecovery } =
 *   useFormRecovery('precuration-new', formData)
 */

import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'
import { useLogger } from './useLogger'
import { useAuthStore } from '@/stores/auth'
import { FORM_RECOVERY_PREFIX } from '@/utils/formRecoveryStorage'

export interface FormRecoveryOptions {
  maxAge?: number
  saveInterval?: number
}

interface RecoverySnapshot {
  data: unknown
  timestamp: string
  url: string
  formId: string
}

export interface UseFormRecoveryReturn {
  showRecoveryDialog: Ref<boolean>
  recoveryData: Ref<unknown>
  recoveryTimestamp: Ref<string | null>
  lastSaved: Ref<string | null>
  restoreRecovery: () => void
  discardRecovery: () => void
  clearRecovery: () => void
  resumeAutoSave: () => void
}

/**
 * Check if data object has meaningful (non-empty) values
 * Recursively checks nested objects and arrays
 */
function hasNonEmptyData(data: unknown): boolean {
  if (data === null || data === undefined) return false
  if (typeof data === 'string') return data.trim().length > 0
  if (typeof data === 'number' || typeof data === 'boolean') return true
  if (Array.isArray(data)) return data.length > 0 && data.some(item => hasNonEmptyData(item))
  if (typeof data === 'object') {
    const values = Object.values(data)
    if (values.length === 0) return false
    return values.some(value => hasNonEmptyData(value))
  }
  return false
}

export function useFormRecovery<T extends object>(
  formId: string,
  formData: Ref<T>,
  options: FormRecoveryOptions = {}
): UseFormRecoveryReturn {
  const logger = useLogger()
  // Keyed by user so drafts never cross accounts on a shared browser
  const recoveryKey = `${FORM_RECOVERY_PREFIX}${useAuthStore().user?.id ?? 'anon'}_${formId}`
  const maxAge = options.maxAge || 24 * 60 * 60 * 1000 // 24 hours
  const saveInterval = options.saveInterval || 5000 // 5 seconds

  const showRecoveryDialog = ref(false)
  const recoveryData = ref<unknown>(null)
  const recoveryTimestamp = ref<string | null>(null)
  const lastSaved = ref<string | null>(null)
  const isPaused = ref(false) // Pause auto-save after discard

  let saveTimer: ReturnType<typeof setInterval> | null = null

  /**
   * Save form data to localStorage with metadata
   * Uses deep clone to avoid reactivity issues
   * Only saves if form has meaningful data
   */
  function saveToLocalStorage(): void {
    // Skip if paused or no meaningful data
    if (isPaused.value) {
      return
    }

    if (!hasNonEmptyData(formData.value)) {
      logger.debug('Form auto-save skipped - no meaningful data', { formId })
      return
    }

    try {
      const snapshot: RecoverySnapshot = {
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
      logger.error('Failed to save form', {
        formId,
        error: error instanceof Error ? error.message : undefined
      })
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
        const snapshot: RecoverySnapshot = JSON.parse(saved)
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
      logger.error('Failed to check recovery data', {
        formId,
        error: error instanceof Error ? error.message : undefined
      })
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
  function restoreRecovery(): void {
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
  function discardRecovery(): void {
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
  function clearRecovery(): void {
    localStorage.removeItem(recoveryKey)
    lastSaved.value = null
    isPaused.value = true // Prevent re-saving after submit
    logger.debug('Recovery data cleared', { formId })
  }

  /**
   * Manually resume auto-save (e.g., after navigation)
   */
  function resumeAutoSave(): void {
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
