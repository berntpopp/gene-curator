import { defineStore } from 'pinia'
import { workflowAPI } from '@/api'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    analytics: null,
    statistics: null,
    peerReviewers: [],
    curationTransitions: {},
    curationHistory: {},
    loading: false,
    error: null,
    currentWorkflowStage: null
  }),

  getters: {
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
