import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import { useOptimisticLocking } from '../useOptimisticLocking'

const conflictError = (data: Record<string, unknown>) => ({ response: { status: 409, data } })

describe('useOptimisticLocking', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sends the lock_version with the payload and returns the response', async () => {
    const apiCall = vi.fn().mockResolvedValue({ lock_version: 4, id: 'p1' })
    const { saveWithLockCheck, conflictDetected } = useOptimisticLocking()

    const result = await saveWithLockCheck(apiCall, { title: 'x' }, 3)

    expect(apiCall).toHaveBeenCalledWith({ title: 'x', lock_version: 3 })
    expect(result).toEqual({ lock_version: 4, id: 'p1' })
    expect(conflictDetected.value).toBe(false)
  })

  it('on 409 records the conflict and rethrows', async () => {
    const apiCall = vi.fn().mockRejectedValue(
      conflictError({
        current_state: { title: 'theirs' },
        lock_version: 5,
        conflicted_fields: ['title'],
        updated_at: '2026-01-01T00:00:00Z'
      })
    )
    const { saveWithLockCheck, conflictDetected, conflictData, hasFieldConflict } =
      useOptimisticLocking()

    await expect(saveWithLockCheck(apiCall, { title: 'mine' }, 3)).rejects.toBeDefined()

    expect(conflictDetected.value).toBe(true)
    expect(conflictData.value).toEqual({
      yourChanges: { title: 'mine' },
      theirChanges: { title: 'theirs' },
      theirVersion: 5,
      conflictedFields: ['title'],
      timestamp: '2026-01-01T00:00:00Z'
    })
    expect(hasFieldConflict('title')).toBe(true)
    expect(hasFieldConflict('other')).toBe(false)
  })

  it('falls back to defaults when the 409 body is sparse', async () => {
    const apiCall = vi.fn().mockRejectedValue(conflictError({}))
    const { saveWithLockCheck, conflictData } = useOptimisticLocking()

    await expect(saveWithLockCheck(apiCall, {}, 7)).rejects.toBeDefined()

    expect(conflictData.value?.theirChanges).toEqual({})
    expect(conflictData.value?.theirVersion).toBe(8)
    expect(conflictData.value?.conflictedFields).toEqual([])
    expect(typeof conflictData.value?.timestamp).toBe('string')
  })

  it('non-409 errors are rethrown without recording a conflict', async () => {
    const apiCall = vi.fn().mockRejectedValue({ response: { status: 500 } })
    const { saveWithLockCheck, conflictDetected } = useOptimisticLocking()

    await expect(saveWithLockCheck(apiCall, {}, 1)).rejects.toEqual({ response: { status: 500 } })
    expect(conflictDetected.value).toBe(false)
  })

  it('errors without a response object are rethrown untouched', async () => {
    const error = new Error('network')
    const { saveWithLockCheck, conflictDetected } = useOptimisticLocking()

    await expect(saveWithLockCheck(() => Promise.reject(error), {}, 1)).rejects.toBe(error)
    expect(conflictDetected.value).toBe(false)
  })

  it('resolveConflict returns resolution data and clears conflict state', async () => {
    const apiCall = vi.fn().mockRejectedValue(conflictError({ lock_version: 9 }))
    const { saveWithLockCheck, resolveConflict, conflictDetected, conflictData } =
      useOptimisticLocking()
    await expect(saveWithLockCheck(apiCall, { a: 1 }, 2)).rejects.toBeDefined()

    const resolved = resolveConflict('overwrite-theirs')

    expect(resolved).toMatchObject({
      resolution: 'overwrite-theirs',
      theirVersion: 9,
      yourChanges: { a: 1 }
    })
    expect(resolved?.data.theirVersion).toBe(9)
    expect(typeof resolved?.resolvedAt).toBe('string')
    expect(conflictDetected.value).toBe(false)
    expect(conflictData.value).toBeNull()
  })

  it('resolveConflict returns null when there is no conflict', () => {
    const { resolveConflict } = useOptimisticLocking()

    expect(resolveConflict('merge')).toBeNull()
  })

  it('cancelConflictResolution clears conflict state', async () => {
    const apiCall = vi.fn().mockRejectedValue(conflictError({}))
    const { saveWithLockCheck, cancelConflictResolution, conflictDetected, conflictData } =
      useOptimisticLocking()
    await expect(saveWithLockCheck(apiCall, {}, 1)).rejects.toBeDefined()

    cancelConflictResolution()

    expect(conflictDetected.value).toBe(false)
    expect(conflictData.value).toBeNull()
  })
})
