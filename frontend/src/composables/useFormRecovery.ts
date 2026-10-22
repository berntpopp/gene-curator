/**
 * Form recovery composable - auto-saves to localStorage and offers recovery
 *
 * Prevents data loss from browser crashes, tab closures, or navigation.
 * Follows best practices: KISS (simple save/restore), DRY (reusable), SOLID (single responsibility)
 *
 * Best practices implemented:
 * - Only saves local edits: form data that differs from the server copy (setBaseline)
 * - Offers recovery only after the server copy is loaded, and flags a draft that started from
 *   an older server version (restoring it would replace newer data)
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
 * const { showRecoveryDialog, lastSaved, restoreRecovery, discardRecovery, clearRecovery, setBaseline } =
 *   useFormRecovery('precuration-new', formData)
 * // once loaded: setBaseline(formData.value, `${lock_version}@${updated_at}`) (null when new)
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
  /** Server version the edits started from (null: a new record; absent: stored before #436) */
  baseVersion?: string | null
}

export interface UseFormRecoveryReturn {
  showRecoveryDialog: Ref<boolean>
  recoveryData: Ref<unknown>
  recoveryTimestamp: Ref<string | null>
  /** The server copy changed after the stored edits were made: restoring replaces newer data */
  recoveryStale: Ref<boolean>
  lastSaved: Ref<string | null>
  restoreRecovery: () => void
  discardRecovery: () => void
  clearRecovery: () => void
  resumeAutoSave: () => void
  /** The server copy the form shows (call again when it changes); recovery waits for it */
  setBaseline: (saved: unknown, version: string | null) => void
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

/** JSON with sorted keys: the server (JSONB) does not keep key order */
function canonical(data: unknown): string {
  return JSON.stringify(data, (_key, value) =>
    value && typeof value === 'object' && !Array.isArray(value)
      ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)))
      : value
  )
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
  const recoveryStale = ref(false)
  const lastSaved = ref<string | null>(null)
  const isPaused = ref(false) // Pause auto-save after discard
  let baseline: string | null = null // canonical server copy; null until loaded
  let baseVersion: string | null = null

  let saveTimer: ReturnType<typeof setInterval> | null = null

  /**
   * Save form data to localStorage with metadata
   * Uses deep clone to avoid reactivity issues
   * Only saves if form has meaningful data
   */
  function saveToLocalStorage(): void {
    // Skip while paused, before the server copy is known, or while a stored draft awaits a choice
    if (isPaused.value || baseline === null || showRecoveryDialog.value) {
      return
    }

    if (!hasNonEmptyData(formData.value)) {
      logger.debug('Form auto-save skipped - no meaningful data', { formId })
      return
    }

    try {
      // No local edits (or all reverted): the server copy needs no recovery
      if (canonical(formData.value) === baseline) {
        localStorage.removeItem(recoveryKey)
        return
      }
      const snapshot: RecoverySnapshot = {
        data: JSON.parse(JSON.stringify(formData.value)),
        timestamp: new Date().toISOString(),
        url: window.location.href,
        formId,
        baseVersion
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

  onMounted(() => {
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
      // Replace, not merge: a field deleted locally stays deleted
      formData.value = recoveryData.value as T
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

  /**
   * Record the server copy the form shows, then offer a stored draft only if it differs from it.
   * A draft that started from another server version is flagged stale, never restored silently.
   */
  function setBaseline(savedData: unknown, version: string | null): void {
    baseline = canonical(savedData)
    baseVersion = version
    showRecoveryDialog.value = false
    recoveryData.value = null
    recoveryTimestamp.value = null
    try {
      const saved = localStorage.getItem(recoveryKey)
      if (saved) {
        const snapshot: RecoverySnapshot = JSON.parse(saved)
        const age = Date.now() - new Date(snapshot.timestamp).getTime()

        // Check if data is still valid (not expired)
        if (age < maxAge) {
          // Only offer recovery if data has meaningful content the server does not have
          if (hasNonEmptyData(snapshot.data) && canonical(snapshot.data) !== baseline) {
            recoveryData.value = snapshot.data
            recoveryTimestamp.value = snapshot.timestamp
            recoveryStale.value = (snapshot.baseVersion ?? null) !== version
            showRecoveryDialog.value = true
            logger.info('Recovery data found', {
              formId,
              age: Math.floor(age / 1000),
              timestamp: snapshot.timestamp,
              stale: recoveryStale.value
            })
          } else {
            // Empty or already saved - clean up silently
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
  }

  return {
    setBaseline,
    recoveryStale,
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
