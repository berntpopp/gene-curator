import { defineStore } from 'pinia'
import { workflowAPI } from '@/api'
import { errorMessage } from './apiError'
import type { Schema } from '@/types/api'

/**
 * Static workflow stages configuration
 * These represent the 5-stage curation workflow:
 * Entry → Precuration → Curation → Review → Active
 *
 * @see .planning/milestones/pre-gsd/plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */
export interface WorkflowStage {
  id: string
  stage_type: string
  name: string
  description: string
  order: number
}

export const WORKFLOW_STAGES: WorkflowStage[] = [
  {
    id: 'entry',
    stage_type: 'entry',
    name: 'Entry',
    description: 'Initial gene entry into the curation pipeline',
    order: 1
  },
  {
    id: 'precuration',
    stage_type: 'precuration',
    name: 'Precuration',
    description: 'Preliminary data gathering and evidence collection',
    order: 2
  },
  {
    id: 'curation',
    stage_type: 'curation',
    name: 'Curation',
    description: 'Full curation with classification and scoring',
    order: 3
  },
  {
    id: 'review',
    stage_type: 'review',
    name: 'Peer Review',
    description: 'Four-eyes principle review by another curator',
    order: 4
  },
  {
    id: 'active',
    stage_type: 'active',
    name: 'Active',
    description: 'Approved and active curation record',
    order: 5
  },
  {
    id: 'archived',
    stage_type: 'archived',
    name: 'Archived',
    description: 'Superseded or deleted; terminal',
    order: 6
  }
]

type Stage = Schema<'WorkflowStage'>
export type WorkflowItemType = 'precuration' | 'curation'

/** Payload of the generic stage actions (advance/reject). */
export interface StageActionPayload {
  entity_id: string
  entity_type: WorkflowItemType
  comment?: string
}

const stageOrder = (stage: Stage): number => WORKFLOW_STAGES.find(w => w.id === stage)?.order ?? 0

interface WorkflowState {
  analytics: Schema<'WorkflowAnalytics'> | null
  statistics: Schema<'WorkflowStatistics'> | null
  peerReviewers: Schema<'PeerReviewerResponse'>[]
  curationTransitions: Record<string, Stage[]>
  curationHistory: Record<string, Schema<'WorkflowAuditEntry'>[]>
  itemStates: Record<string, Schema<'WorkflowStateInfo'>>
  loading: boolean
  error: string | null
  currentWorkflowStage: string | null
  _workflowStages: WorkflowStage[]
}

export const useWorkflowStore = defineStore('workflow', {
  state: (): WorkflowState => ({
    analytics: null,
    statistics: null,
    peerReviewers: [],
    curationTransitions: {},
    curationHistory: {},
    itemStates: {},
    loading: false,
    error: null,
    currentWorkflowStage: null,
    // Static workflow stages - exposed via getter for consistency
    _workflowStages: WORKFLOW_STAGES
  }),

  getters: {
    /**
     * Get static workflow stages configuration
     * @returns {Array} Array of workflow stage objects
     */
    workflowStages: state => state._workflowStages,

    getCurationTransitions: state => (curationId: string) => {
      return state.curationTransitions[curationId] || []
    },

    getCurationHistory: state => (curationId: string) => {
      return state.curationHistory[curationId] || []
    },

    getAvailableReviewers:
      state =>
      (excludeUserId: string | null = null) => {
        return state.peerReviewers.filter(
          reviewer => !excludeUserId || reviewer.id !== excludeUserId
        )
      },

    /** Number of items currently in `stage` (from the last fetched statistics). */
    getWorkflowStageStats: state => (stage: string) => {
      return state.statistics?.stage_counts[stage]
    },

    /** Workflow state (current stage, available transitions) fetched by `fetchCurrentStage`. */
    getCurrentStage: state => (entityId: string) => {
      return state.itemStates[entityId]
    },

    /** Stage-transition history fetched by `fetchStageHistory` / `fetchCurationWorkflowHistory`. */
    getStageHistory: state => (entityId: string) => {
      return state.curationHistory[entityId] || []
    }
  },

  actions: {
    async fetchWorkflowAnalytics(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const analytics = await workflowAPI.getWorkflowAnalytics(params)

        this.analytics = analytics
        return analytics
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async transitionCuration(
      curationId: string,
      transitionData: Schema<'WorkflowTransitionRequest'>
    ) {
      this.loading = true
      this.error = null
      try {
        const result = await workflowAPI.transitionCuration(curationId, transitionData)

        // Refresh available transitions after successful transition
        await this.fetchAvailableTransitions(curationId)

        return result
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    /** Dry-run a transition (no state change): errors and missing required fields. */
    validateTransition(
      itemType: string,
      itemId: string,
      targetStage: Schema<'WorkflowTransitionRequest'>['target_stage']
    ) {
      return workflowAPI.validateTransition(itemType, itemId, targetStage)
    },

    async fetchAvailableTransitions(curationId: string) {
      try {
        const transitions = await workflowAPI.getAvailableTransitions(curationId)

        this.curationTransitions[curationId] = transitions
        return transitions
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async fetchPeerReviewers(params: Record<string, unknown> = {}) {
      try {
        const reviewers = await workflowAPI.getPeerReviewers(params)

        this.peerReviewers = reviewers
        return reviewers
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async submitPeerReview(reviewId: string, reviewData: Schema<'PeerReviewSubmission'>) {
      this.loading = true
      this.error = null
      try {
        return await workflowAPI.submitPeerReview(reviewId, reviewData)
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    /** Load the workflow state of a precuration/curation (GET /workflow/{type}/{id}/state). */
    async fetchCurrentStage(entityId: string, entityType: WorkflowItemType = 'curation') {
      try {
        const state = await workflowAPI.getWorkflowState(entityType, entityId)
        this.itemStates[entityId] = state
        return state
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    /** Load the stage-transition history of a precuration/curation (GET .../audit-trail). */
    async fetchStageHistory(entityId: string, entityType: WorkflowItemType = 'curation') {
      try {
        const trail = await workflowAPI.getWorkflowAuditTrail(entityType, entityId)
        this.curationHistory[entityId] = trail.entries
        return trail.entries
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    /** Move an item to the nearest later stage the backend currently allows. */
    async advanceStage(payload: StageActionPayload) {
      return this.moveStage(payload, 'forward')
    },

    /** Send an item back to the nearest earlier stage the backend currently allows. */
    async rejectStage(payload: StageActionPayload) {
      return this.moveStage(payload, 'backward')
    },

    async moveStage(payload: StageActionPayload, direction: 'forward' | 'backward') {
      this.loading = true
      this.error = null
      try {
        const state = await workflowAPI.getWorkflowState(payload.entity_type, payload.entity_id)
        const current = stageOrder(state.current_stage)
        const inDirection = (t: Stage) =>
          direction === 'forward' ? stageOrder(t) > current : stageOrder(t) < current
        const candidates = state.available_transitions
          .filter(inDirection)
          .sort((a, b) => stageOrder(a) - stageOrder(b))
        const target = direction === 'forward' ? candidates[0] : candidates[candidates.length - 1]
        if (!target) {
          // The backend says why the caller cannot move (e.g. 4-eyes on their own work)
          const reasons = (state.blocked ?? []).filter(b => inDirection(b.stage))
          throw new Error(
            reasons.map(b => b.reason).join('; ') ||
              `No ${direction} transition available from ${state.current_stage}`
          )
        }
        const result = await workflowAPI.transitionItem(payload.entity_type, payload.entity_id, {
          target_stage: target,
          notes: payload.comment
        })
        await this.fetchCurrentStage(payload.entity_id, payload.entity_type)
        return result
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCurationWorkflowHistory(curationId: string) {
      try {
        const trail = await workflowAPI.getCurationWorkflowHistory(curationId)

        this.curationHistory[curationId] = trail.entries
        return trail.entries
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async fetchWorkflowStatistics(params: Record<string, unknown> = {}) {
      try {
        const statistics = await workflowAPI.getWorkflowStatistics(params)

        this.statistics = statistics
        return statistics
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    setCurrentWorkflowStage(stage: string | null) {
      this.currentWorkflowStage = stage
    },

    clearCurrentWorkflowStage() {
      this.currentWorkflowStage = null
    },

    clearError() {
      this.error = null
    }
  }
})
