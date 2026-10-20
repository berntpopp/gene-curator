import { defineStore } from 'pinia'
import { toApiError } from './apiError'
import { assignmentsAPI } from '@/api'
import type { Schema } from '@/types/api'

/** Assignment row as rendered by the assignment views (superset of the API schema). */
export interface AssignmentRecord {
  id: string
  priority_level?: string
  notes?: string
  [key: string]: unknown
}

interface AssignmentsPagination {
  page: number
  per_page: number
  total: number
  pages: number
}

interface AssignmentsState {
  assignments: AssignmentRecord[]
  curatorWorkloads: Record<string, Schema<'CuratorWorkload'>>
  scopeAssignments: Record<string, AssignmentRecord[]>
  availableGenes: Record<string, Schema<'AvailableGene'>[]>
  scopeOverviews: Record<string, Schema<'ScopeAssignmentOverview'>>
  loading: boolean
  error: string | null
  pagination: AssignmentsPagination
}

export const useAssignmentsStore = defineStore('assignments', {
  state: (): AssignmentsState => ({
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
    getAssignmentsByScope: state => (scopeId: string) => {
      return state.scopeAssignments[scopeId] || []
    },

    getCuratorWorkload: state => (curatorId: string) => {
      return state.curatorWorkloads[curatorId] || {}
    },

    getAvailableGenesForScope: state => (scopeId: string) => {
      return state.availableGenes[scopeId] || []
    },

    getScopeOverview: state => (scopeId: string) => {
      return state.scopeOverviews[scopeId] || {}
    },

    getAssignmentsByPriority: state => (priority: string) => {
      return state.assignments.filter(assignment => assignment.priority_level === priority)
    },

    getHighPriorityAssignments: state => {
      return state.assignments.filter(assignment => assignment.priority_level === 'high')
    }
  },

  actions: {
    async fetchAssignments(params: Record<string, unknown> = {}) {
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
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async bulkAssignGenes(assignmentData: Schema<'BulkGeneScopeAssignmentCreate'>) {
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
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCuratorWorkload(curatorId: string) {
      try {
        const workload = await assignmentsAPI.getCuratorWorkload(curatorId)
        this.curatorWorkloads[curatorId] = workload
        return workload
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchCuratorAssignments(curatorId: string, params: Record<string, unknown> = {}) {
      try {
        const assignments = await assignmentsAPI.getCuratorAssignments(curatorId, params)
        return assignments
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async updateAssignmentPriority(assignmentId: string, priority: string) {
      this.loading = true
      this.error = null
      try {
        const result = await assignmentsAPI.updateAssignmentPriority(assignmentId, priority)

        // Update the assignment in the local state
        const assignment = this.assignments.find(a => a.id === assignmentId)
        if (assignment) {
          assignment.priority_level = priority
        }

        return result
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchAssignmentsByScope(scopeId: string, params: Record<string, unknown> = {}) {
      try {
        const assignments = await assignmentsAPI.getAssignmentsByScope(scopeId, params)
        this.scopeAssignments[scopeId] = assignments.assignments || assignments
        return assignments
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchAvailableGenesForScope(scopeId: string) {
      try {
        const genes = await assignmentsAPI.getAvailableGenesForScope(scopeId)
        this.availableGenes[scopeId] = genes
        return genes
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchScopeAssignmentOverview(scopeId: string) {
      try {
        const overview = await assignmentsAPI.getScopeAssignmentOverview(scopeId)
        this.scopeOverviews[scopeId] = overview
        return overview
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async updateAssignment(assignmentId: string, updateData: Record<string, unknown>) {
      this.loading = true
      this.error = null
      try {
        const result = await assignmentsAPI.updateAssignment(assignmentId, updateData)
        const index = this.assignments.findIndex(a => a.id === assignmentId)
        if (index !== -1) {
          this.assignments[index] = { ...this.assignments[index], ...result }
        }
        return result
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    clearError() {
      this.error = null
    }
  }
})
