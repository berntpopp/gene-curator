/**
 * Form recovery composable - auto-saves to localStorage and offers recovery
 *
 * Prevents data loss from browser crashes, tab closures, or navigation.
 * Follows best practices: KISS (simple save/restore), DRY (reusable), SOLID (single responsibility)
 *
 * Best practices implemented:
 * - Only saves local edits: form data that differs from the server copy (setBaseline), on change
 * - Offers recovery only after the server copy is loaded, and flags a draft that started from
 *   an older server version (restoring it would replace newer data)
 * - A save re-bases the comparison (markSaved); later edits stay protected
 * - Only ever removes the draft this form stored or was offered: other tabs share the key
 *
 * @param formId - Unique form identifier (e.g., 'precuration-p1-...', 'curation-new-<scope>-<gene>-...')
 * @param formData - Reactive form data reference
 * @param options - Configuration options
 * @param options.maxAge - Maximum age of recovery data in milliseconds (default: 24h)
 * @returns Recovery state and methods
 *
 * @example
 * const formData = ref({ gene: '', rationale: '' })
 * const { showRecoveryDialog, lastSaved, restoreRecovery, discardRecovery, clearRecovery, setBaseline } =
 *   useFormRecovery('precuration-new', formData)
 * // once loaded: setBaseline(formData.value, recoveryVersion(record)) (null when new; utils)
 */

import { ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useLogger } from './useLogger'
import { useAuthStore } from '@/stores/auth'
import { FORM_RECOVERY_PREFIX } from '@/utils/formRecoveryStorage'

export interface FormRecoveryOptions {
  maxAge?: number
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
  /** A save reached the server: compare later edits with what was sent, bound to its version */
  markSaved: (saved: unknown, version: string) => void
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

  const showRecoveryDialog = ref(false)
  const recoveryData = ref<unknown>(null)
  const recoveryTimestamp = ref<string | null>(null)
  const recoveryStale = ref(false)
  const lastSaved = ref<string | null>(null)
  const isPaused = ref(false) // after submit or cancel
  let baseline: string | null = null // canonical server copy; null until loaded
  let baseVersion: string | null = null
  // The exact draft this form stored (or was offered): another tab's draft is never removed
  let written: string | null = null

  function forgetOwn(): void {
    if (written !== null && localStorage.getItem(recoveryKey) === written) {
      localStorage.removeItem(recoveryKey)
    }
    written = null
  }

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

    try {
      // No local edits (all reverted or emptied): this form's draft would only offer older text
      if (!hasNonEmptyData(formData.value) || canonical(formData.value) === baseline) {
        forgetOwn()
        return
      }
      const snapshot: RecoverySnapshot = {
        data: JSON.parse(JSON.stringify(formData.value)),
        timestamp: new Date().toISOString(),
        url: window.location.href,
        formId,
        baseVersion
      }
      written = JSON.stringify(snapshot)
      localStorage.setItem(recoveryKey, written)
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
   * Watch for changes and save (only if has meaningful data)
   * Deep watch to catch nested property changes; no timer, so an idle tab never touches storage
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
   * Discard the offered draft and start fresh; edits made from now on are protected again
   */
  function discardRecovery(): void {
    forgetOwn()
    recoveryData.value = null
    recoveryTimestamp.value = null
    showRecoveryDialog.value = false
    logger.info('Recovery data discarded', { formId })
  }

  /**
   * Clear recovery data on submit or cancel (a save calls markSaved instead)
   */
  function clearRecovery(): void {
    forgetOwn()
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
            written = saved // offered here: a discard may remove it, unless another tab replaced it
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

  function markSaved(savedData: unknown, version: string): void {
    baseline = canonical(savedData)
    baseVersion = version
    isPaused.value = false
    saveToLocalStorage() // forgets this form's draft, or re-binds edits made since to the save
  }

  return {
    setBaseline,
    markSaved,
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
