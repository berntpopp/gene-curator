import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkflowStore, WORKFLOW_STAGES } from '@/stores/workflow'
import { workflowAPI, curationsAPI } from '@/api'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api', () => ({
  workflowAPI: {
    getWorkflowAnalytics: vi.fn(),
    transitionCuration: vi.fn(),
    getAvailableTransitions: vi.fn(),
    getPeerReviewers: vi.fn(),
    submitPeerReview: vi.fn(),
    getCurationWorkflowHistory: vi.fn(),
    getWorkflowStatistics: vi.fn()
  },
  curationsAPI: {
    getCurations: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(workflowAPI)
const curations = vi.mocked(curationsAPI)

describe('useWorkflowStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('exposes the five static workflow stages in order', () => {
    const store = useWorkflowStore()
    expect(store.workflowStages).toEqual(WORKFLOW_STAGES)
    expect(WORKFLOW_STAGES.map(s => s.id)).toEqual([
      'entry',
      'precuration',
      'curation',
      'review',
      'active'
    ])
  })

  describe('getters', () => {
    it('returns transitions, history and stage stats with defaults', () => {
      const store = useWorkflowStore()
      store.curationTransitions = { c1: [{ to: 'review' } as never] }
      store.curationHistory = { c1: [{ action: 'x' } as never] }
      store.statistics = { stages: { review: { pending: 2 } } } as never
      store.peerReviewers = [
        { id: 'u1', name: 'A' },
        { id: 'u2', name: 'B' }
      ] as never

      expect(store.getCurationTransitions('c1')).toEqual([{ to: 'review' }])
      expect(store.getCurationTransitions('none')).toEqual([])
      expect(store.getCurationHistory('c1')).toEqual([{ action: 'x' }])
      expect(store.getCurationHistory('none')).toEqual([])
      expect(store.getWorkflowStageStats('review')).toEqual({ pending: 2 })
      expect(store.getWorkflowStageStats('entry')).toEqual({})
      expect(store.getAvailableReviewers().map(r => r.id)).toEqual(['u1', 'u2'])
      expect(store.getAvailableReviewers('u1').map(r => r.id)).toEqual(['u2'])
    })
  })

  describe('fetchWorkflowAnalytics', () => {
    it('stores analytics and returns them', async () => {
      const store = useWorkflowStore()
      api.getWorkflowAnalytics.mockResolvedValue({ completion_rate: 0.5 })

      await expect(store.fetchWorkflowAnalytics({ days: 30 })).resolves.toEqual({
        completion_rate: 0.5
      })
      expect(api.getWorkflowAnalytics).toHaveBeenCalledWith({ days: 30 })
      expect(store.analytics).toEqual({ completion_rate: 0.5 })
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows', async () => {
      const store = useWorkflowStore()
      api.getWorkflowAnalytics.mockRejectedValue(new Error('analytics'))

      await expect(store.fetchWorkflowAnalytics()).rejects.toThrow('analytics')
      expect(store.error).toBe('analytics')
      expect(store.loading).toBe(false)
    })
  })

  describe('transitionCuration', () => {
    it('transitions and refreshes available transitions', async () => {
      const store = useWorkflowStore()
      api.transitionCuration.mockResolvedValue({ ok: true })
      api.getAvailableTransitions.mockResolvedValue([{ to: 'curation' }])

      await expect(
        store.transitionCuration('c1', { target_stage: 'curation' } as never)
      ).resolves.toEqual({ ok: true })

      expect(api.getAvailableTransitions).toHaveBeenCalledWith('c1')
      expect(store.curationTransitions.c1).toEqual([{ to: 'curation' }])
    })

    it('records the error and rethrows without refreshing', async () => {
      const store = useWorkflowStore()
      api.transitionCuration.mockRejectedValue(new Error('invalid transition'))

      await expect(store.transitionCuration('c1', {} as never)).rejects.toThrow(
        'invalid transition'
      )
      expect(store.error).toBe('invalid transition')
      expect(api.getAvailableTransitions).not.toHaveBeenCalled()
    })
  })

  describe('fetchAvailableTransitions / fetchPeerReviewers / fetchWorkflowStatistics', () => {
    it('stores transitions per curation', async () => {
      const store = useWorkflowStore()
      api.getAvailableTransitions.mockResolvedValue([{ to: 'review' }])

      await expect(store.fetchAvailableTransitions('c1')).resolves.toEqual([{ to: 'review' }])
      expect(store.curationTransitions.c1).toEqual([{ to: 'review' }])
    })

    it('stores peer reviewers', async () => {
      const store = useWorkflowStore()
      api.getPeerReviewers.mockResolvedValue([{ id: 'u1' }])

      await expect(store.fetchPeerReviewers({ scope: 's1' })).resolves.toEqual([{ id: 'u1' }])
      expect(api.getPeerReviewers).toHaveBeenCalledWith({ scope: 's1' })
      expect(store.peerReviewers).toEqual([{ id: 'u1' }])
    })

    it('stores workflow statistics', async () => {
      const store = useWorkflowStore()
      api.getWorkflowStatistics.mockResolvedValue({ approval_rate: 0.9 })

      await expect(store.fetchWorkflowStatistics()).resolves.toEqual({ approval_rate: 0.9 })
      expect(store.statistics).toEqual({ approval_rate: 0.9 })
    })

    it('each of these records errors and rethrows', async () => {
      const store = useWorkflowStore()
      api.getAvailableTransitions.mockRejectedValue(new Error('t'))
      api.getPeerReviewers.mockRejectedValue(new Error('p'))
      api.getWorkflowStatistics.mockRejectedValue(new Error('s'))

      await expect(store.fetchAvailableTransitions('c1')).rejects.toThrow('t')
      await expect(store.fetchPeerReviewers()).rejects.toThrow('p')
      await expect(store.fetchWorkflowStatistics()).rejects.toThrow('s')
      expect(store.error).toBe('s')
    })
  })

  describe('submitPeerReview / fetchCurationWorkflowHistory', () => {
    it('submits the review and refreshes history', async () => {
      const store = useWorkflowStore()
      api.submitPeerReview.mockResolvedValue({ recorded: true })
      api.getCurationWorkflowHistory.mockResolvedValue([{ action: 'review' }])

      await expect(store.submitPeerReview('c1', { decision: 'approve' } as never)).resolves.toEqual(
        { recorded: true }
      )

      expect(store.curationHistory.c1).toEqual([{ action: 'review' }])
      expect(store.loading).toBe(false)
    })

    it('records errors from submitPeerReview and rethrows', async () => {
      const store = useWorkflowStore()
      api.submitPeerReview.mockRejectedValue(new Error('self review'))

      await expect(store.submitPeerReview('c1', {} as never)).rejects.toThrow('self review')
      expect(store.error).toBe('self review')
      expect(store.loading).toBe(false)
    })

    it('stores history and records errors', async () => {
      const store = useWorkflowStore()
      api.getCurationWorkflowHistory.mockResolvedValueOnce([{ action: 'a' }])
      await expect(store.fetchCurationWorkflowHistory('c1')).resolves.toEqual([{ action: 'a' }])
      expect(store.curationHistory.c1).toEqual([{ action: 'a' }])

      api.getCurationWorkflowHistory.mockRejectedValueOnce(new Error('h'))
      await expect(store.fetchCurationWorkflowHistory('c1')).rejects.toThrow('h')
      expect(store.error).toBe('h')
    })
  })

  describe('fetchPendingReviewCount', () => {
    it('counts in-review curations not created by the current user', async () => {
      const store = useWorkflowStore()
      const auth = useAuthStore()
      auth.user = { id: 'me' } as never
      curations.getCurations.mockResolvedValue({
        curations: [{ created_by: 'me' }, { created_by: 'other' }, { created_by: 'x' }]
      } as never)

      await expect(store.fetchPendingReviewCount()).resolves.toBe(2)
      expect(curations.getCurations).toHaveBeenCalledWith({
        curation_status: 'in_review',
        limit: 200
      })
      expect(store.pendingReviewCount).toBe(2)
    })

    it('returns 0 when the request fails', async () => {
      const store = useWorkflowStore()
      curations.getCurations.mockRejectedValue(new Error('down'))

      await expect(store.fetchPendingReviewCount()).resolves.toBe(0)
    })
  })

  describe('local state actions', () => {
    it('setCurrentWorkflowStage / clearCurrentWorkflowStage / clearError', () => {
      const store = useWorkflowStore()
      store.setCurrentWorkflowStage('review')
      expect(store.currentWorkflowStage).toBe('review')

      store.clearCurrentWorkflowStage()
      expect(store.currentWorkflowStage).toBeNull()

      store.error = 'x'
      store.clearError()
      expect(store.error).toBeNull()
    })
  })
})
