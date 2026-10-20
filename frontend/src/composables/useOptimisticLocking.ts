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
import type { Ref } from 'vue'
import { useLogger } from './useLogger'

/** Body of a 409 Conflict response from the backend. */
export interface ConflictResponse {
  current_state?: Record<string, unknown>
  lock_version?: number
  conflicted_fields?: string[]
  updated_at?: string
}

export interface ConflictData {
  yourChanges: unknown
  theirChanges: Record<string, unknown>
  theirVersion: number
  conflictedFields: string[]
  timestamp: string
}

export type ConflictResolution = 'discard-mine' | 'overwrite-theirs' | 'merge'

export interface ResolvedConflict extends ConflictData {
  resolution: ConflictResolution
  resolvedAt: string
  data: ConflictData
}

export type SaveWithLockCheck = <T extends object, R extends { lock_version?: number }>(
  apiCall: (payload: T & { lock_version: number }) => Promise<R>,
  data: T,
  currentVersion: number
) => Promise<R>

export interface UseOptimisticLockingReturn {
  conflictDetected: Ref<boolean>
  conflictData: Ref<ConflictData | null>
  saveWithLockCheck: SaveWithLockCheck
  resolveConflict: (resolution: ConflictResolution) => ResolvedConflict | null
  cancelConflictResolution: () => void
  hasFieldConflict: (fieldName: string) => boolean
}

/** Pull the HTTP response off an axios-style error, if there is one. */
function responseOf(error: unknown): { status?: number; data: ConflictResponse } | undefined {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    return (error as { response?: { status?: number; data: ConflictResponse } }).response
  }
  return undefined
}

export function useOptimisticLocking(): UseOptimisticLockingReturn {
  const logger = useLogger()

  const conflictDetected = ref(false)
  const conflictData = ref<ConflictData | null>(null)

  /**
   * Save data with optimistic lock check
   *
   * @param apiCall - API function that accepts data (e.g., (data) => api.update(id, data))
   * @param data - Data to save
   * @param currentVersion - Current lock_version from loaded data
   * @returns API response
   * @throws Throws on conflict (409) or other errors
   */
  const saveWithLockCheck: SaveWithLockCheck = async (apiCall, data, currentVersion) => {
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
      const httpResponse = responseOf(error)
      if (httpResponse?.status === 409) {
        // Extract conflict information from backend response
        const backendData = httpResponse.data

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
   * @param resolution - Resolution strategy:
   *   - 'discard-mine': Discard user's changes, use server's version
   *   - 'overwrite-theirs': Overwrite server's version with user's changes
   *   - 'merge': User will manually merge (returned for manual handling)
   * @returns Conflict data with resolution, or null when there is no conflict
   */
  function resolveConflict(resolution: ConflictResolution): ResolvedConflict | null {
    if (!conflictData.value) {
      logger.warn('Resolve conflict called but no conflict data')
      return null
    }

    const data = conflictData.value
    const resolved = {
      ...data,
      resolution,
      resolvedAt: new Date().toISOString()
    }

    logger.info('Conflict resolved', {
      resolution,
      theirVersion: data.theirVersion
    })

    // Clear conflict state
    conflictDetected.value = false
    conflictData.value = null

    return { ...resolved, data }
  }

  /**
   * Cancel conflict resolution (close dialog without action)
   */
  function cancelConflictResolution(): void {
    logger.debug('Conflict resolution cancelled')
    conflictDetected.value = false
    conflictData.value = null
  }

  /**
   * Check if a specific field has conflicts
   */
  function hasFieldConflict(fieldName: string): boolean {
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
