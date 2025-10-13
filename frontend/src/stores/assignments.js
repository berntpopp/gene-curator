import { defineStore } from 'pinia'
import { assignmentsAPI } from '@/api'

export const useAssignmentsStore = defineStore('assignments', {
  state: () => ({
    assignments: [],
    curatorWorkloads: {},
    scopeAssignments: {},
    availableGenes: {},
    scopeOverviews: {},
    loading: false,
    error: null,
    pagination: {
      page: 1,
      per_page: 20,
      total: 0,
      pages: 0
    }
  }),

  getters: {
    getAssignmentsByScope: state => scopeId => {
      return state.scopeAssignments[scopeId] || []
    },

    getCuratorWorkload: state => curatorId => {
      return state.curatorWorkloads[curatorId] || {}
    },

    getAvailableGenesForScope: state => scopeId => {
      return state.availableGenes[scopeId] || []
    },

    getScopeOverview: state => scopeId => {
      return state.scopeOverviews[scopeId] || {}
    },

    getAssignmentsByPriority: state => priority => {
      return state.assignments.filter(assignment => assignment.priority_level === priority)
    },

    getHighPriorityAssignments: state => {
      return state.assignments.filter(assignment => assignment.priority_level === 'high')
    }
  },

  actions: {
    async fetchAssignments(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await assignmentsAPI.getAssignments(params)

        this.assignments = response.assignments || response.data || response

        if (response.pagination) {
          this.pagination = response.pagination
        }

        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async bulkAssignGenes(assignmentData) {
      this.loading = true
      this.error = null
      try {
        const result = await assignmentsAPI.bulkAssignGenes(assignmentData)

        // Refresh assignments after bulk operation
        await this.fetchAssignments()

        // Refresh scope assignments if scope_id is provided
        if (assignmentData.scope_id) {
          await this.fetchAssignmentsByScope(assignmentData.scope_id)
        }

        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCuratorWorkload(curatorId) {
      try {
        const workload = await assignmentsAPI.getCuratorWorkload(curatorId)
        this.curatorWorkloads[curatorId] = workload
        return workload
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchCuratorAssignments(curatorId, params = {}) {
      try {
        const assignments = await assignmentsAPI.getCuratorAssignments(curatorId, params)
        return assignments
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async updateAssignmentPriority(assignmentId, priority) {
      this.loading = true
      this.error = null
      try {
        const result = await assignmentsAPI.updateAssignmentPriority(assignmentId, priority)

        // Update the assignment in the local state
        const index = this.assignments.findIndex(a => a.id === assignmentId)
        if (index !== -1) {
          this.assignments[index].priority_level = priority
        }

        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchAssignmentsByScope(scopeId, params = {}) {
      try {
        const assignments = await assignmentsAPI.getAssignmentsByScope(scopeId, params)
        this.scopeAssignments[scopeId] = assignments.assignments || assignments
        return assignments
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchAvailableGenesForScope(scopeId) {
      try {
        const genes = await assignmentsAPI.getAvailableGenesForScope(scopeId)
        this.availableGenes[scopeId] = genes
        return genes
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchScopeAssignmentOverview(scopeId) {
      try {
        const overview = await assignmentsAPI.getScopeAssignmentOverview(scopeId)
        this.scopeOverviews[scopeId] = overview
        return overview
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    clearError() {
      this.error = null
    }
  }
})
