import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkflowStore, WORKFLOW_STAGES } from '@/stores/workflow'
import { workflowAPI } from '@/api'
import type { Schema } from '@/types/api'

vi.mock('@/api', () => ({
  workflowAPI: {
    getWorkflowAnalytics: vi.fn(),
    transitionCuration: vi.fn(),
    transitionItem: vi.fn(),
    getWorkflowState: vi.fn(),
    getWorkflowAuditTrail: vi.fn(),
    getAvailableTransitions: vi.fn(),
    getPeerReviewers: vi.fn(),
    submitPeerReview: vi.fn(),
    getCurationWorkflowHistory: vi.fn(),
    getWorkflowStatistics: vi.fn()
  }
}))

const api = vi.mocked(workflowAPI)

type Stage = Schema<'WorkflowStage'>

const entry = (id: string, to: Stage): Schema<'WorkflowAuditEntry'> =>
  ({ id, to_stage: to }) as Schema<'WorkflowAuditEntry'>

const trail = (entries: Schema<'WorkflowAuditEntry'>[]): Schema<'WorkflowAuditTrail'> =>
  ({ item_id: 'c1', item_type: 'curation', entries }) as Schema<'WorkflowAuditTrail'>

const stateAt = (current: Stage, available: Stage[]): Schema<'WorkflowStateInfo'> =>
  ({ current_stage: current, available_transitions: available }) as Schema<'WorkflowStateInfo'>

const transition = { success: true } as Schema<'WorkflowTransition'>

const reviewer = (id: string) => ({ id, name: id }) as Schema<'PeerReviewerResponse'>

describe('useWorkflowStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('exposes the static workflow stages in order, archived last', () => {
    const store = useWorkflowStore()
    expect(store.workflowStages).toEqual(WORKFLOW_STAGES)
    expect(WORKFLOW_STAGES.map(s => s.id)).toEqual([
      'entry',
      'precuration',
      'curation',
      'review',
      'active',
      'archived'
    ])
  })

  describe('getters', () => {
    it('returns transitions, history, stage counts and state with defaults', () => {
      const store = useWorkflowStore()
      store.curationTransitions = { c1: ['review'] }
      store.curationHistory = { c1: [entry('e1', 'review')] }
      store.statistics = { stage_counts: { review: 2 } } as unknown as Schema<'WorkflowStatistics'>
      store.itemStates = { c1: stateAt('curation', ['review']) }
      store.peerReviewers = [reviewer('u1'), reviewer('u2')]

      expect(store.getCurationTransitions('c1')).toEqual(['review'])
      expect(store.getCurationTransitions('none')).toEqual([])
      expect(store.getCurationHistory('c1').map(e => e.id)).toEqual(['e1'])
      expect(store.getCurationHistory('none')).toEqual([])
      expect(store.getStageHistory('c1').map(e => e.id)).toEqual(['e1'])
      expect(store.getWorkflowStageStats('review')).toBe(2)
      expect(store.getWorkflowStageStats('entry')).toBeUndefined()
      expect(store.getCurrentStage('c1')?.current_stage).toBe('curation')
      expect(store.getCurrentStage('none')).toBeUndefined()
      expect(store.getAvailableReviewers().map(r => r.id)).toEqual(['u1', 'u2'])
      expect(store.getAvailableReviewers('u1').map(r => r.id)).toEqual(['u2'])
    })
  })

  describe('fetchWorkflowAnalytics', () => {
    it('stores analytics and returns them', async () => {
      const store = useWorkflowStore()
      const analytics = { completion_rate: 0.5 } as Schema<'WorkflowAnalytics'>
      api.getWorkflowAnalytics.mockResolvedValue(analytics)

      await expect(store.fetchWorkflowAnalytics({ days: 30 })).resolves.toEqual(analytics)
      expect(api.getWorkflowAnalytics).toHaveBeenCalledWith({ days: 30 })
      expect(store.analytics).toEqual(analytics)
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
      api.transitionCuration.mockResolvedValue(transition)
      api.getAvailableTransitions.mockResolvedValue(['curation'])

      await expect(store.transitionCuration('c1', { target_stage: 'curation' })).resolves.toEqual(
        transition
      )

      expect(api.getAvailableTransitions).toHaveBeenCalledWith('c1')
      expect(store.curationTransitions.c1).toEqual(['curation'])
    })

    it('records the error and rethrows without refreshing', async () => {
      const store = useWorkflowStore()
      api.transitionCuration.mockRejectedValue(new Error('invalid transition'))

      await expect(store.transitionCuration('c1', { target_stage: 'active' })).rejects.toThrow(
        'invalid transition'
      )
      expect(store.error).toBe('invalid transition')
      expect(api.getAvailableTransitions).not.toHaveBeenCalled()
    })
  })

  describe('fetchAvailableTransitions / fetchPeerReviewers / fetchWorkflowStatistics', () => {
    it('stores transitions per curation', async () => {
      const store = useWorkflowStore()
      api.getAvailableTransitions.mockResolvedValue(['review'])

      await expect(store.fetchAvailableTransitions('c1')).resolves.toEqual(['review'])
      expect(store.curationTransitions.c1).toEqual(['review'])
    })

    it('stores peer reviewers', async () => {
      const store = useWorkflowStore()
      api.getPeerReviewers.mockResolvedValue([reviewer('u1')])

      await expect(store.fetchPeerReviewers({ scope: 's1' })).resolves.toEqual([reviewer('u1')])
      expect(api.getPeerReviewers).toHaveBeenCalledWith({ scope: 's1' })
      expect(store.peerReviewers).toEqual([reviewer('u1')])
    })

    it('stores workflow statistics', async () => {
      const store = useWorkflowStore()
      const stats = { approval_rate: 0.9 } as Schema<'WorkflowStatistics'>
      api.getWorkflowStatistics.mockResolvedValue(stats)

      await expect(store.fetchWorkflowStatistics()).resolves.toEqual(stats)
      expect(store.statistics).toEqual(stats)
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
    it('submits the review decision for a review id', async () => {
      const store = useWorkflowStore()
      const outcome = { review_id: 'r1', decision: 'approve' } as Schema<'PeerReviewResult'>
      api.submitPeerReview.mockResolvedValue(outcome)

      await expect(store.submitPeerReview('r1', { decision: 'approve' })).resolves.toEqual(outcome)

      expect(api.submitPeerReview).toHaveBeenCalledWith('r1', { decision: 'approve' })
      expect(store.loading).toBe(false)
    })

    it('records errors from submitPeerReview and rethrows', async () => {
      const store = useWorkflowStore()
      api.submitPeerReview.mockRejectedValue(new Error('self review'))

      await expect(store.submitPeerReview('r1', { decision: 'approve' })).rejects.toThrow(
        'self review'
      )
      expect(store.error).toBe('self review')
      expect(store.loading).toBe(false)
    })

    it('stores history entries and records errors', async () => {
      const store = useWorkflowStore()
      api.getCurationWorkflowHistory.mockResolvedValueOnce(trail([entry('a', 'review')]))
      const entries = await store.fetchCurationWorkflowHistory('c1')
      expect(entries.map(e => e.id)).toEqual(['a'])
      expect(store.curationHistory.c1?.map(e => e.id)).toEqual(['a'])

      api.getCurationWorkflowHistory.mockRejectedValueOnce(new Error('h'))
      await expect(store.fetchCurationWorkflowHistory('c1')).rejects.toThrow('h')
      expect(store.error).toBe('h')
    })
  })

  describe('item stage state and history', () => {
    it('fetchCurrentStage stores the workflow state by entity id', async () => {
      const store = useWorkflowStore()
      const state = stateAt('precuration', ['curation'])
      api.getWorkflowState.mockResolvedValue(state)

      await expect(store.fetchCurrentStage('p1', 'precuration')).resolves.toEqual(state)

      expect(api.getWorkflowState).toHaveBeenCalledWith('precuration', 'p1')
      expect(store.getCurrentStage('p1')).toEqual(state)
    })

    it('fetchStageHistory stores the audit entries and defaults to curations', async () => {
      const store = useWorkflowStore()
      api.getWorkflowAuditTrail.mockResolvedValue(trail([entry('e1', 'curation')]))

      await store.fetchStageHistory('c1')

      expect(api.getWorkflowAuditTrail).toHaveBeenCalledWith('curation', 'c1')
      expect(store.getStageHistory('c1').map(e => e.id)).toEqual(['e1'])
    })

    it('records errors from both fetches and rethrows', async () => {
      const store = useWorkflowStore()
      api.getWorkflowState.mockRejectedValue(new Error('state'))
      api.getWorkflowAuditTrail.mockRejectedValue(new Error('trail'))

      await expect(store.fetchCurrentStage('c1')).rejects.toThrow('state')
      expect(store.error).toBe('state')
      await expect(store.fetchStageHistory('c1')).rejects.toThrow('trail')
      expect(store.error).toBe('trail')
    })
  })

  describe('advanceStage / rejectStage', () => {
    const payload = { entity_id: 'c1', entity_type: 'curation', comment: 'ok' } as const

    it('advances to the nearest later allowed stage and refreshes the state', async () => {
      const store = useWorkflowStore()
      api.getWorkflowState.mockResolvedValue(
        stateAt('curation', ['precuration', 'active', 'review'])
      )
      api.transitionItem.mockResolvedValue(transition)

      await expect(store.advanceStage(payload)).resolves.toEqual(transition)

      expect(api.transitionItem).toHaveBeenCalledWith('curation', 'c1', {
        target_stage: 'review',
        notes: 'ok'
      })
      expect(api.getWorkflowState).toHaveBeenCalledTimes(2)
      expect(store.loading).toBe(false)
    })

    it('rejects to the nearest earlier allowed stage', async () => {
      const store = useWorkflowStore()
      api.getWorkflowState.mockResolvedValue(stateAt('review', ['entry', 'curation']))
      api.transitionItem.mockResolvedValue(transition)

      await store.rejectStage(payload)

      expect(api.transitionItem).toHaveBeenCalledWith(
        'curation',
        'c1',
        expect.objectContaining({ target_stage: 'curation' })
      )
    })

    it('archived is the terminal stage: it sorts after active and never moves on', async () => {
      const store = useWorkflowStore()
      api.getWorkflowState.mockResolvedValue(stateAt('active', ['archived', 'review']))
      api.transitionItem.mockResolvedValue(transition)
      await store.advanceStage(payload)
      expect(api.transitionItem).toHaveBeenLastCalledWith(
        'curation',
        'c1',
        expect.objectContaining({ target_stage: 'archived' })
      )

      api.getWorkflowState.mockResolvedValue(stateAt('archived', ['review']))
      await store.rejectStage(payload)
      expect(api.transitionItem).toHaveBeenLastCalledWith(
        'curation',
        'c1',
        expect.objectContaining({ target_stage: 'review' })
      )
      api.getWorkflowState.mockResolvedValue(stateAt('archived', ['review']))
      await expect(store.advanceStage(payload)).rejects.toThrow('No forward transition')
    })

    it('fails without calling the backend when no matching transition is allowed', async () => {
      const store = useWorkflowStore()
      api.getWorkflowState.mockResolvedValue(stateAt('active', []))

      await expect(store.advanceStage(payload)).rejects.toThrow('No forward transition')
      expect(api.transitionItem).not.toHaveBeenCalled()
      expect(store.error).toContain('No forward transition')
      expect(store.loading).toBe(false)
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
