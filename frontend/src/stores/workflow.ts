import { defineStore } from 'pinia'
import { workflowAPI } from '@/api'
import { toApiError, apiData } from './apiError'
import type { Schema } from '@/types/api'

/**
 * Static workflow stages configuration
 * These represent the 5-stage curation workflow:
 * Entry → Precuration → Curation → Review → Active
 *
 * @see plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */
export interface WorkflowStage {
  id: string
  stage_type: string
  name: string
  description: string
  required_roles: string[]
  order: number
}

export const WORKFLOW_STAGES: WorkflowStage[] = [
  {
    id: 'entry',
    stage_type: 'entry',
    name: 'Entry',
    description: 'Initial gene entry into the curation pipeline',
    required_roles: ['curator', 'scope_admin', 'admin'],
    order: 1
  },
  {
    id: 'precuration',
    stage_type: 'precuration',
    name: 'Precuration',
    description: 'Preliminary data gathering and evidence collection',
    required_roles: ['curator', 'scope_admin', 'admin'],
    order: 2
  },
  {
    id: 'curation',
    stage_type: 'curation',
    name: 'Curation',
    description: 'Full curation with classification and scoring',
    required_roles: ['curator', 'scope_admin', 'admin'],
    order: 3
  },
  {
    id: 'review',
    stage_type: 'review',
    name: 'Peer Review',
    description: 'Four-eyes principle review by another curator',
    required_roles: ['reviewer', 'scope_admin', 'admin'],
    order: 4
  },
  {
    id: 'active',
    stage_type: 'active',
    name: 'Active',
    description: 'Approved and active curation record',
    required_roles: ['admin'],
    order: 5
  }
]

/** Workflow statistics; `stages` is read per stage name but is not declared by the API schema. */
type WorkflowStatisticsRecord = Schema<'WorkflowStatistics'> & {
  stages?: Record<string, Record<string, unknown>>
}

interface WorkflowState {
  analytics: Schema<'WorkflowAnalytics'> | null
  statistics: WorkflowStatisticsRecord | null
  peerReviewers: Schema<'PeerReviewerResponse'>[]
  curationTransitions: Record<string, Schema<'WorkflowTransition'>[]>
  curationHistory: Record<string, Schema<'WorkflowAuditEntry'>[]>
  loading: boolean
  error: string | null
  currentWorkflowStage: string | null
  pendingReviewCount: number
  _workflowStages: WorkflowStage[]
}

export const useWorkflowStore = defineStore('workflow', {
  state: (): WorkflowState => ({
    analytics: null,
    statistics: null,
    peerReviewers: [],
    curationTransitions: {},
    curationHistory: {},
    loading: false,
    error: null,
    currentWorkflowStage: null,
    pendingReviewCount: 0,
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

    getWorkflowStageStats: state => (stage: string) => {
      return state.statistics?.stages?.[stage] || {}
    }
  },

  actions: {
    async fetchWorkflowAnalytics(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const analytics = apiData<Schema<'WorkflowAnalytics'>>(
          await workflowAPI.getWorkflowAnalytics(params)
        )
        this.analytics = analytics
        return analytics
      } catch (error) {
        this.error = toApiError(error).message ?? null
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
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchAvailableTransitions(curationId: string) {
      try {
        const transitions = apiData<Schema<'WorkflowTransition'>[]>(
          await workflowAPI.getAvailableTransitions(curationId)
        )
        this.curationTransitions[curationId] = transitions
        return transitions
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchPeerReviewers(params: Record<string, unknown> = {}) {
      try {
        const reviewers = apiData<Schema<'PeerReviewerResponse'>[]>(
          await workflowAPI.getPeerReviewers(params)
        )
        this.peerReviewers = reviewers
        return reviewers
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async submitPeerReview(curationId: string, reviewData: Schema<'PeerReviewSubmission'>) {
      this.loading = true
      this.error = null
      try {
        const result = await workflowAPI.submitPeerReview(curationId, reviewData)

        // Refresh curation history after review submission
        await this.fetchCurationWorkflowHistory(curationId)

        return result
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCurationWorkflowHistory(curationId: string) {
      try {
        const history = apiData<Schema<'WorkflowAuditEntry'>[]>(
          await workflowAPI.getCurationWorkflowHistory(curationId)
        )
        this.curationHistory[curationId] = history
        return history
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchWorkflowStatistics(params: Record<string, unknown> = {}) {
      try {
        const statistics = apiData<WorkflowStatisticsRecord>(
          await workflowAPI.getWorkflowStatistics(params)
        )
        this.statistics = statistics
        return statistics
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchPendingReviewCount() {
      try {
        // Dynamic imports keep this store free of a static dependency cycle with auth/curations
        const { curationsAPI } = await import('@/api')
        const { useAuthStore } = await import('@/stores/auth')
        const authStore = useAuthStore()

        const response = apiData<{ curations?: { created_by?: string }[] }>(
          await curationsAPI.getCurations({
            curation_status: 'in_review',
            limit: 200
          })
        )
        const userId = authStore.user?.id
        const myReviews = (response.curations || []).filter(c => c.created_by !== userId)
        this.pendingReviewCount = myReviews.length
        return this.pendingReviewCount
      } catch {
        return 0
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
