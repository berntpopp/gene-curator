import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAssignmentsStore } from '@/stores/assignments'

vi.mock('@/api', () => ({
  assignmentsAPI: {
    getAssignments: vi.fn(),
    updateAssignment: vi.fn(),
    assignCurator: vi.fn(),
  },
}))

import { assignmentsAPI } from '@/api'

describe('useAssignmentsStore', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAssignmentsStore()
    vi.clearAllMocks()
  })

  describe('updateAssignment', () => {
    it('calls API and updates local state', async () => {
      const updated = { id: 'a1', priority_level: 'high', notes: 'urgent' }
      assignmentsAPI.updateAssignment.mockResolvedValue(updated)
      store.assignments = [{ id: 'a1', priority_level: 'low', notes: '' }]

      const result = await store.updateAssignment('a1', { priority_level: 'high', notes: 'urgent' })

      expect(assignmentsAPI.updateAssignment).toHaveBeenCalledWith('a1', { priority_level: 'high', notes: 'urgent' })
      expect(result).toEqual(updated)
      expect(store.assignments[0].priority_level).toBe('high')
    })

    it('sets error on failure', async () => {
      assignmentsAPI.updateAssignment.mockRejectedValue(new Error('Network error'))
      await expect(store.updateAssignment('a1', {})).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
    })
  })
})
