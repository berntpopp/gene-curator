import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAssignmentsStore } from '@/stores/assignments'
import { assignmentsAPI } from '@/api'
import type { Schema } from '@/types/api'

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
    updateAssignment: vi.fn(),
    createAssignment: vi.fn(),
    getAssignment: vi.fn()
  }
}))

const api = vi.mocked(assignmentsAPI)

type Summary = Schema<'GeneScopeAssignmentSummary'>

const summary = (id: string, over: Partial<Summary> = {}): Summary => ({
  id,
  gene_id: 'g1',
  gene_symbol: 'GENE',
  gene_hgnc_id: 'HGNC:1',
  scope_id: 's1',
  scope_name: 'scope',
  assigned_curator_id: null,
  curator_name: null,
  priority: 'medium',
  is_active: true,
  assigned_at: '2026-01-01',
  has_active_work: false,
  ...over
})

const listResponse = (
  assignments: Summary[],
  over: Partial<Schema<'GeneScopeAssignmentListResponse'>> = {}
): Schema<'GeneScopeAssignmentListResponse'> => ({
  assignments,
  total: assignments.length,
  skip: 0,
  limit: 20,
  has_next: false,
  has_prev: false,
  ...over
})

const workload = (total: number) => ({ total_assignments: total }) as Schema<'CuratorWorkload'>

describe('useAssignmentsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('filters assignments by priority and exposes scope lookups', () => {
      const store = useAssignmentsStore()
      store.assignments = [
        summary('a1', { priority: 'high' }),
        summary('a2', { priority: 'low' }),
        summary('a3', { priority: 'high' })
      ]
      store.scopeAssignments = { s1: [summary('a1')] }
      store.curatorWorkloads = { c1: workload(2) }

      expect(store.getAssignmentsByPriority('high').map(a => a.id)).toEqual(['a1', 'a3'])
      expect(store.getHighPriorityAssignments.map(a => a.id)).toEqual(['a1', 'a3'])
      expect(store.getAssignmentsByScope('s1').map(a => a.id)).toEqual(['a1'])
      expect(store.getAssignmentsByScope('missing')).toEqual([])
      expect(store.getCuratorWorkload('c1')).toEqual(workload(2))
      expect(store.getCuratorWorkload('missing')).toBeUndefined()
      expect(store.getAvailableGenesForScope('missing')).toEqual([])
      expect(store.getScopeOverview('missing')).toBeUndefined()
    })
  })

  describe('fetchAssignments', () => {
    it('stores the list and derives page state from skip/limit', async () => {
      const store = useAssignmentsStore()
      const response = listResponse([summary('a1')], { total: 45, skip: 20, limit: 20 })
      api.getAssignments.mockResolvedValue(response)

      const result = await store.fetchAssignments({ skip: 20 })

      expect(api.getAssignments).toHaveBeenCalledWith({ skip: 20 })
      expect(result).toEqual(response)
      expect(store.assignments.map(a => a.id)).toEqual(['a1'])
      expect(store.pagination).toEqual({ page: 2, per_page: 20, total: 45, pages: 3 })
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows on failure', async () => {
      const store = useAssignmentsStore()
      api.getAssignments.mockRejectedValue(new Error('Network error'))

      await expect(store.fetchAssignments()).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchAssignmentById', () => {
    it('returns the assignment with details', async () => {
      const detail = { id: 'a1' } as Schema<'GeneScopeAssignmentWithDetails'>
      api.getAssignment.mockResolvedValue(detail)
      const store = useAssignmentsStore()

      await expect(store.fetchAssignmentById('a1')).resolves.toBe(detail)
      expect(api.getAssignment).toHaveBeenCalledWith('a1')
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows on failure', async () => {
      api.getAssignment.mockRejectedValue(new Error('gone'))
      const store = useAssignmentsStore()

      await expect(store.fetchAssignmentById('a1')).rejects.toThrow('gone')
      expect(store.error).toBe('gone')
    })
  })

  describe('createAssignment', () => {
    const payload: Schema<'GeneScopeAssignmentCreate'> = {
      gene_id: 'g1',
      scope_id: 's1',
      priority_level: 'high'
    }

    it('creates through the API and returns the new assignment', async () => {
      const created = { id: 'new' } as Schema<'GeneScopeAssignment'>
      api.createAssignment.mockResolvedValue(created)
      const store = useAssignmentsStore()

      await expect(store.createAssignment(payload)).resolves.toBe(created)
      expect(api.createAssignment).toHaveBeenCalledWith(payload)
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows on failure', async () => {
      api.createAssignment.mockRejectedValue(new Error('exists'))
      const store = useAssignmentsStore()

      await expect(store.createAssignment(payload)).rejects.toThrow('exists')
      expect(store.error).toBe('exists')
      expect(store.loading).toBe(false)
    })
  })

  describe('bulkAssignGenes', () => {
    const bulk = (scope?: string) =>
      ({ scope_id: scope, gene_ids: ['g1'] }) as unknown as Schema<'BulkGeneScopeAssignmentCreate'>

    it('refreshes global and scope assignments after success', async () => {
      const store = useAssignmentsStore()
      const outcome = {} as Schema<'BulkGeneScopeAssignmentResponse'>
      api.bulkAssignGenes.mockResolvedValue(outcome)
      api.getAssignments.mockResolvedValue(listResponse([]))
      api.getAssignmentsByScope.mockResolvedValue([summary('s')])

      const result = await store.bulkAssignGenes(bulk('s1'))

      expect(result).toBe(outcome)
      expect(api.getAssignments).toHaveBeenCalled()
      expect(api.getAssignmentsByScope).toHaveBeenCalledWith('s1', {})
      expect(store.scopeAssignments.s1?.map(a => a.id)).toEqual(['s'])
    })

    it('skips the scope refresh when no scope_id is given', async () => {
      const store = useAssignmentsStore()
      api.bulkAssignGenes.mockResolvedValue({} as Schema<'BulkGeneScopeAssignmentResponse'>)
      api.getAssignments.mockResolvedValue(listResponse([]))

      await store.bulkAssignGenes(bulk())

      expect(api.getAssignmentsByScope).not.toHaveBeenCalled()
    })

    it('sets the error and rethrows on failure', async () => {
      const store = useAssignmentsStore()
      api.bulkAssignGenes.mockRejectedValue(new Error('conflict'))

      await expect(store.bulkAssignGenes(bulk('s1'))).rejects.toThrow('conflict')
      expect(store.error).toBe('conflict')
    })
  })

  describe('curator workload and assignments', () => {
    it('stores the workload by curator id', async () => {
      const store = useAssignmentsStore()
      api.getCuratorWorkload.mockResolvedValue(workload(4))

      await expect(store.fetchCuratorWorkload('c1')).resolves.toEqual(workload(4))
      expect(store.curatorWorkloads.c1).toEqual(workload(4))
    })

    it('returns curator assignments without touching state', async () => {
      const store = useAssignmentsStore()
      api.getCuratorAssignments.mockResolvedValue([summary('x')])

      const result = await store.fetchCuratorAssignments('c1', { status: 'active' })

      expect(result.map(a => a.id)).toEqual(['x'])
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
      store.assignments = [summary('a1', { priority: 'low' })]
      const updated = { id: 'a1', priority: 'high' } as Schema<'GeneScopeAssignment'>
      api.updateAssignmentPriority.mockResolvedValue(updated)

      await expect(store.updateAssignmentPriority('a1', 'high')).resolves.toBe(updated)

      expect(api.updateAssignmentPriority).toHaveBeenCalledWith('a1', 'high')
      expect(store.assignments[0]?.priority).toBe('high')
      expect(store.loading).toBe(false)
    })

    it('leaves local state untouched when the assignment is not loaded', async () => {
      const store = useAssignmentsStore()
      api.updateAssignmentPriority.mockResolvedValue({} as Schema<'GeneScopeAssignment'>)

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
    it('stores scope assignments', async () => {
      const store = useAssignmentsStore()
      api.getAssignmentsByScope.mockResolvedValueOnce([summary('w')])

      await store.fetchAssignmentsByScope('s1', { limit: 5 })

      expect(api.getAssignmentsByScope).toHaveBeenCalledWith('s1', { limit: 5 })
      expect(store.scopeAssignments.s1?.map(a => a.id)).toEqual(['w'])
    })

    it('stores available genes and scope overviews', async () => {
      const store = useAssignmentsStore()
      const genes = [{ gene_id: 'g1' }] as Schema<'AvailableGene'>[]
      const overview = { total_genes_assigned: 3 } as unknown as Schema<'ScopeAssignmentOverview'>
      api.getAvailableGenesForScope.mockResolvedValue(genes)
      api.getScopeAssignmentOverview.mockResolvedValue(overview)

      await expect(store.fetchAvailableGenesForScope('s1')).resolves.toBe(genes)
      await expect(store.fetchScopeAssignmentOverview('s1')).resolves.toBe(overview)

      expect(store.getAvailableGenesForScope('s1')).toEqual(genes)
      expect(store.getScopeOverview('s1')).toEqual(overview)
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
    it('calls API and mirrors the result into local state', async () => {
      const store = useAssignmentsStore()
      const updated = {
        id: 'a1',
        priority: 'high',
        is_active: true,
        assigned_curator_id: 'c9'
      } as Schema<'GeneScopeAssignment'>
      api.updateAssignment.mockResolvedValue(updated)
      store.assignments = [summary('a1', { priority: 'low' })]

      const result = await store.updateAssignment('a1', { priority_level: 'high' })

      expect(api.updateAssignment).toHaveBeenCalledWith('a1', { priority_level: 'high' })
      expect(result).toBe(updated)
      expect(store.assignments[0]).toMatchObject({ priority: 'high', assigned_curator_id: 'c9' })
      expect(store.loading).toBe(false)
    })

    it('ignores the local list when the assignment is not loaded', async () => {
      const store = useAssignmentsStore()
      api.updateAssignment.mockResolvedValue({ id: 'other' } as Schema<'GeneScopeAssignment'>)

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
  })
})
