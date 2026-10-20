import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAssignmentsStore } from '@/stores/assignments'
import { assignmentsAPI } from '@/api'
import { logService } from '@/services/logService'

vi.mock('@/api', () => ({
  assignmentsAPI: {
    getAssignments: vi.fn(),
    bulkAssignGenes: vi.fn(),
    getCuratorWorkload: vi.fn(),
    getCuratorAssignments: vi.fn(),
    updateAssignmentPriority: vi.fn(),
    getAssignmentsByScope: vi.fn(),
    getAvailableGenesForScope: vi.fn(),
    getScopeAssignmentOverview: vi.fn(),
    updateAssignment: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(assignmentsAPI)

describe('useAssignmentsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('filters assignments by priority and exposes scope lookups with defaults', () => {
      const store = useAssignmentsStore()
      store.assignments = [
        { id: 'a1', priority_level: 'high' },
        { id: 'a2', priority_level: 'low' },
        { id: 'a3', priority_level: 'high' }
      ]
      store.scopeAssignments = { s1: [{ id: 'a1' }] }
      store.curatorWorkloads = { c1: { total_assignments: 2 } as never }

      expect(store.getAssignmentsByPriority('high').map(a => a.id)).toEqual(['a1', 'a3'])
      expect(store.getHighPriorityAssignments.map(a => a.id)).toEqual(['a1', 'a3'])
      expect(store.getAssignmentsByScope('s1')).toEqual([{ id: 'a1' }])
      expect(store.getAssignmentsByScope('missing')).toEqual([])
      expect(store.getCuratorWorkload('c1')).toEqual({ total_assignments: 2 })
      expect(store.getCuratorWorkload('missing')).toEqual({})
      expect(store.getAvailableGenesForScope('missing')).toEqual([])
      expect(store.getScopeOverview('missing')).toEqual({})
    })
  })

  describe('fetchAssignments', () => {
    it('reads the assignments list and pagination from the response', async () => {
      const store = useAssignmentsStore()
      const response = {
        assignments: [{ id: 'a1' }],
        pagination: { page: 2, per_page: 20, total: 40, pages: 2 }
      }
      api.getAssignments.mockResolvedValue(response)

      const result = await store.fetchAssignments({ page: 2 })

      expect(api.getAssignments).toHaveBeenCalledWith({ page: 2 })
      expect(result).toEqual(response)
      expect(store.assignments).toEqual([{ id: 'a1' }])
      expect(store.pagination.total).toBe(40)
      expect(store.loading).toBe(false)
    })

    it('falls back to data or the raw response when no assignments key exists', async () => {
      const store = useAssignmentsStore()
      api.getAssignments.mockResolvedValueOnce({ data: [{ id: 'd1' }] })
      await store.fetchAssignments()
      expect(store.assignments).toEqual([{ id: 'd1' }])

      api.getAssignments.mockResolvedValueOnce([{ id: 'raw' }])
      await store.fetchAssignments()
      expect(store.assignments).toEqual([{ id: 'raw' }])
    })

    it('records the error and rethrows on failure', async () => {
      const store = useAssignmentsStore()
      api.getAssignments.mockRejectedValue(new Error('Network error'))

      await expect(store.fetchAssignments()).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })
  })

  describe('bulkAssignGenes', () => {
    it('refreshes global and scope assignments after success', async () => {
      const store = useAssignmentsStore()
      api.bulkAssignGenes.mockResolvedValue({ created: 2 })
      api.getAssignments.mockResolvedValue({ assignments: [] })
      api.getAssignmentsByScope.mockResolvedValue({ assignments: [{ id: 's' }] })

      const result = await store.bulkAssignGenes({
        scope_id: 's1',
        gene_ids: ['g1']
      } as never)

      expect(result).toEqual({ created: 2 })
      expect(api.getAssignments).toHaveBeenCalled()
      expect(api.getAssignmentsByScope).toHaveBeenCalledWith('s1', {})
      expect(store.scopeAssignments.s1).toEqual([{ id: 's' }])
    })

    it('skips the scope refresh when no scope_id is given', async () => {
      const store = useAssignmentsStore()
      api.bulkAssignGenes.mockResolvedValue({} as never)
      api.getAssignments.mockResolvedValue({ assignments: [] })

      await store.bulkAssignGenes({ gene_ids: [] } as never)

      expect(api.getAssignmentsByScope).not.toHaveBeenCalled()
    })

    it('sets the error and rethrows on failure', async () => {
      const store = useAssignmentsStore()
      api.bulkAssignGenes.mockRejectedValue(new Error('conflict'))

      await expect(store.bulkAssignGenes({} as never)).rejects.toThrow('conflict')
      expect(store.error).toBe('conflict')
    })
  })

  describe('curator workload and assignments', () => {
    it('stores the workload by curator id', async () => {
      const store = useAssignmentsStore()
      api.getCuratorWorkload.mockResolvedValue({ total_assignments: 4 })

      await expect(store.fetchCuratorWorkload('c1')).resolves.toEqual({ total_assignments: 4 })
      expect(store.curatorWorkloads.c1).toEqual({ total_assignments: 4 })
    })

    it('returns curator assignments without touching state', async () => {
      const store = useAssignmentsStore()
      api.getCuratorAssignments.mockResolvedValue({ assignments: [{ id: 'x' }] })

      await expect(store.fetchCuratorAssignments('c1', { status: 'active' })).resolves.toEqual({
        assignments: [{ id: 'x' }]
      })
      expect(api.getCuratorAssignments).toHaveBeenCalledWith('c1', { status: 'active' })
      expect(store.assignments).toEqual([])
    })

    it('records errors for workload and curator assignment fetches', async () => {
      const store = useAssignmentsStore()
      api.getCuratorWorkload.mockRejectedValue(new Error('w'))
      api.getCuratorAssignments.mockRejectedValue(new Error('a'))

      await expect(store.fetchCuratorWorkload('c1')).rejects.toThrow('w')
      await expect(store.fetchCuratorAssignments('c1')).rejects.toThrow('a')
      expect(store.error).toBe('a')
    })
  })

  describe('updateAssignmentPriority', () => {
    it('updates the priority of the local assignment', async () => {
      const store = useAssignmentsStore()
      store.assignments = [{ id: 'a1', priority_level: 'low' }]
      api.updateAssignmentPriority.mockResolvedValue({ ok: true })

      await expect(store.updateAssignmentPriority('a1', 'high')).resolves.toEqual({ ok: true })

      expect(api.updateAssignmentPriority).toHaveBeenCalledWith('a1', 'high')
      expect(store.assignments[0]?.priority_level).toBe('high')
      expect(store.loading).toBe(false)
    })

    it('leaves local state untouched when the assignment is not loaded', async () => {
      const store = useAssignmentsStore()
      api.updateAssignmentPriority.mockResolvedValue({} as never)

      await store.updateAssignmentPriority('missing', 'high')

      expect(store.assignments).toEqual([])
    })

    it('sets the error and rethrows on failure', async () => {
      const store = useAssignmentsStore()
      api.updateAssignmentPriority.mockRejectedValue(new Error('denied'))

      await expect(store.updateAssignmentPriority('a1', 'high')).rejects.toThrow('denied')
      expect(store.error).toBe('denied')
      expect(store.loading).toBe(false)
    })
  })

  describe('scope assignment fetches', () => {
    it('stores scope assignments from either response shape', async () => {
      const store = useAssignmentsStore()
      api.getAssignmentsByScope.mockResolvedValueOnce({ assignments: [{ id: 'w' }] })
      await store.fetchAssignmentsByScope('s1', { limit: 5 })
      expect(api.getAssignmentsByScope).toHaveBeenCalledWith('s1', { limit: 5 })
      expect(store.scopeAssignments.s1).toEqual([{ id: 'w' }])

      api.getAssignmentsByScope.mockResolvedValueOnce([{ id: 'bare' }])
      await store.fetchAssignmentsByScope('s2')
      expect(store.scopeAssignments.s2).toEqual([{ id: 'bare' }])
    })

    it('stores available genes and scope overviews', async () => {
      const store = useAssignmentsStore()
      api.getAvailableGenesForScope.mockResolvedValue([{ gene_id: 'g1' }])
      api.getScopeAssignmentOverview.mockResolvedValue({ total: 3 })

      await expect(store.fetchAvailableGenesForScope('s1')).resolves.toEqual([{ gene_id: 'g1' }])
      await expect(store.fetchScopeAssignmentOverview('s1')).resolves.toEqual({ total: 3 })

      expect(store.getAvailableGenesForScope('s1')).toEqual([{ gene_id: 'g1' }])
      expect(store.getScopeOverview('s1')).toEqual({ total: 3 })
    })

    it('records errors from every scope fetch and rethrows', async () => {
      const store = useAssignmentsStore()
      api.getAssignmentsByScope.mockRejectedValue(new Error('e1'))
      api.getAvailableGenesForScope.mockRejectedValue(new Error('e2'))
      api.getScopeAssignmentOverview.mockRejectedValue(new Error('e3'))

      await expect(store.fetchAssignmentsByScope('s')).rejects.toThrow('e1')
      expect(store.error).toBe('e1')
      await expect(store.fetchAvailableGenesForScope('s')).rejects.toThrow('e2')
      expect(store.error).toBe('e2')
      await expect(store.fetchScopeAssignmentOverview('s')).rejects.toThrow('e3')
      expect(store.error).toBe('e3')
    })
  })

  describe('updateAssignment', () => {
    it('calls API and updates local state', async () => {
      const store = useAssignmentsStore()
      const updated = { id: 'a1', priority_level: 'high', notes: 'urgent' }
      api.updateAssignment.mockResolvedValue(updated)
      store.assignments = [{ id: 'a1', priority_level: 'low', notes: '' }]

      const result = await store.updateAssignment('a1', {
        priority_level: 'high',
        notes: 'urgent'
      })

      expect(api.updateAssignment).toHaveBeenCalledWith('a1', {
        priority_level: 'high',
        notes: 'urgent'
      })
      expect(result).toEqual(updated)
      expect(store.assignments[0]?.priority_level).toBe('high')
      expect(store.loading).toBe(false)
    })

    it('ignores the local list when the assignment is not loaded', async () => {
      const store = useAssignmentsStore()
      api.updateAssignment.mockResolvedValue({ id: 'other' })

      await store.updateAssignment('other', {})

      expect(store.assignments).toEqual([])
    })

    it('sets error on failure', async () => {
      const store = useAssignmentsStore()
      api.updateAssignment.mockRejectedValue(new Error('Network error'))

      await expect(store.updateAssignment('a1', {})).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })
  })

  it('clearError resets the error', () => {
    const store = useAssignmentsStore()
    store.error = 'x'
    store.clearError()
    expect(store.error).toBeNull()
    expect(logService.error).not.toHaveBeenCalled()
  })
})
