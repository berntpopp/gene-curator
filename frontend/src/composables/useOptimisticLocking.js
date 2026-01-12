/**
 * Optimistic Locking composable - handles concurrent edit conflicts
 *
 * Implements optimistic locking pattern with conflict detection and resolution UI.
 * Follows SOLID principles: Single responsibility for conflict management.
 *
 * Design pattern: Optimistic Locking with lock_version field
 * - Backend increments lock_version on every update
 * - Frontend sends current lock_version with update request
 * - 409 Conflict if versions don't match (someone else edited)
 *
 * @example
 * const { conflictDetected, conflictData, saveWithLockCheck, resolveConflict } =
 *   useOptimisticLocking()
 *
 * // Save with conflict check
 * try {
 *   await saveWithLockCheck(
 *     (data) => api.updateCuration(id, data),
 *     formData,
 *     currentLockVersion
 *   )
 * } catch (error) {
 *   if (error.response?.status === 409) {
 *     // conflictDetected will be true, show UI
 *   }
 * }
 */

import { ref } from 'vue'
import { useLogger } from './useLogger'

export function useOptimisticLocking() {
  const logger = useLogger()

  const conflictDetected = ref(false)
  const conflictData = ref(null)

  /**
   * Save data with optimistic lock check
   *
   * @param {Function} apiCall - API function that accepts data (e.g., (data) => api.update(id, data))
   * @param {Object} data - Data to save
   * @param {number} currentVersion - Current lock_version from loaded data
   * @returns {Promise<*>} API response
   * @throws {Error} Throws on conflict (409) or other errors
   */
  async function saveWithLockCheck(apiCall, data, currentVersion) {
    try {
      // Add lock_version to payload for backend validation
      const payload = {
        ...data,
        lock_version: currentVersion
      }

      logger.debug('Attempting save with lock check', {
        lockVersion: currentVersion,
        hasData: !!data
      })

      const response = await apiCall(payload)

      logger.info('Save successful', {
        lockVersion: currentVersion,
        newLockVersion: response.lock_version
      })

      return response
    } catch (error) {
      // Check for 409 Conflict response
      if (error.response?.status === 409) {
        // Extract conflict information from backend response
        const backendData = error.response.data

        conflictDetected.value = true
        conflictData.value = {
          yourChanges: data,
          theirChanges: backendData.current_state || {},
          theirVersion: backendData.lock_version || currentVersion + 1,
          conflictedFields: backendData.conflicted_fields || [],
          timestamp: backendData.updated_at || new Date().toISOString()
        }

        logger.warn('Optimistic lock conflict detected', {
          yourVersion: currentVersion,
          theirVersion: conflictData.value.theirVersion,
          conflictedFields: conflictData.value.conflictedFields
        })
      }

      // Re-throw error for caller to handle
      throw error
    }
  }

  /**
   * Resolve conflict and clear state
   *
   * @param {string} resolution - Resolution strategy:
   *   - 'discard-mine': Discard user's changes, use server's version
   *   - 'overwrite-theirs': Overwrite server's version with user's changes
   *   - 'merge': User will manually merge (returned for manual handling)
   * @returns {Object} Conflict data with resolution
   */
  function resolveConflict(resolution) {
    if (!conflictData.value) {
      logger.warn('Resolve conflict called but no conflict data')
      return null
    }

    const resolved = {
      ...conflictData.value,
      resolution,
      resolvedAt: new Date().toISOString()
    }

    logger.info('Conflict resolved', {
      resolution,
      theirVersion: conflictData.value.theirVersion
    })

    // Clear conflict state
    conflictDetected.value = false
    const data = conflictData.value
    conflictData.value = null

    return { ...resolved, data }
  }

  /**
   * Cancel conflict resolution (close dialog without action)
   */
  function cancelConflictResolution() {
    logger.debug('Conflict resolution cancelled')
    conflictDetected.value = false
    conflictData.value = null
  }

  /**
   * Check if a specific field has conflicts
   *
   * @param {string} fieldName - Field name to check
   * @returns {boolean}
   */
  function hasFieldConflict(fieldName) {
    return conflictData.value?.conflictedFields?.includes(fieldName) || false
  }

  return {
    // State
    conflictDetected,
    conflictData,

    // Methods
    saveWithLockCheck,
    resolveConflict,
    cancelConflictResolution,
    hasFieldConflict
  }
}
