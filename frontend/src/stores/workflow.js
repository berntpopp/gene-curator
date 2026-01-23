import { defineStore } from 'pinia'
import { workflowAPI } from '@/api'

/**
 * Static workflow stages configuration
 * These represent the 5-stage curation workflow:
 * Entry → Precuration → Curation → Review → Active
 *
 * @see plan/enhancements/tracking/011-IMPROVEMENT-PLAN.md
 */
export const WORKFLOW_STAGES = [
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

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    analytics: null,
    statistics: null,
    peerReviewers: [],
    curationTransitions: {},
    curationHistory: {},
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

    getCurationTransitions: state => curationId => {
      return state.curationTransitions[curationId] || []
    },

    getCurationHistory: state => curationId => {
      return state.curationHistory[curationId] || []
    },

    getAvailableReviewers:
      state =>
      (excludeUserId = null) => {
        return state.peerReviewers.filter(
          reviewer => !excludeUserId || reviewer.id !== excludeUserId
        )
      },

    getWorkflowStageStats: state => stage => {
      return state.statistics?.stages?.[stage] || {}
    }
  },

  actions: {
    async fetchWorkflowAnalytics(params = {}) {
      this.loading = true
      this.error = null
      try {
        const analytics = await workflowAPI.getWorkflowAnalytics(params)
        this.analytics = analytics
        return analytics
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async transitionCuration(curationId, transitionData) {
      this.loading = true
      this.error = null
      try {
        const result = await workflowAPI.transitionCuration(curationId, transitionData)

        // Refresh available transitions after successful transition
        await this.fetchAvailableTransitions(curationId)

        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchAvailableTransitions(curationId) {
      try {
        const transitions = await workflowAPI.getAvailableTransitions(curationId)
        this.curationTransitions[curationId] = transitions
        return transitions
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchPeerReviewers(params = {}) {
      try {
        const reviewers = await workflowAPI.getPeerReviewers(params)
        this.peerReviewers = reviewers
        return reviewers
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async submitPeerReview(curationId, reviewData) {
      this.loading = true
      this.error = null
      try {
        const result = await workflowAPI.submitPeerReview(curationId, reviewData)

        // Refresh curation history after review submission
        await this.fetchCurationWorkflowHistory(curationId)

        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCurationWorkflowHistory(curationId) {
      try {
        const history = await workflowAPI.getCurationWorkflowHistory(curationId)
        this.curationHistory[curationId] = history
        return history
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchWorkflowStatistics(params = {}) {
      try {
        const statistics = await workflowAPI.getWorkflowStatistics(params)
        this.statistics = statistics
        return statistics
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    setCurrentWorkflowStage(stage) {
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
