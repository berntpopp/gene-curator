import { defineStore } from 'pinia'
import { toApiError } from './apiError'
import { assignmentsAPI } from '@/api'
import type { Schema } from '@/types/api'
import { pageStateFrom, type PageState } from './pagination'

/** Assignment row as listed by the API. */
export type AssignmentRecord = Schema<'GeneScopeAssignmentSummary'>

interface AssignmentsState {
  assignments: AssignmentRecord[]
  curatorWorkloads: Record<string, Schema<'CuratorWorkload'>>
  scopeAssignments: Record<string, AssignmentRecord[]>
  availableGenes: Record<string, Schema<'AvailableGene'>[]>
  scopeOverviews: Record<string, Schema<'ScopeAssignmentOverview'>>
  loading: boolean
  error: string | null
  pagination: PageState
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
      return state.curatorWorkloads[curatorId]
    },

    getAvailableGenesForScope: state => (scopeId: string) => {
      return state.availableGenes[scopeId] || []
    },

    getScopeOverview: state => (scopeId: string) => {
      return state.scopeOverviews[scopeId]
    },

    getAssignmentsByPriority: state => (priority: string) => {
      return state.assignments.filter(assignment => assignment.priority === priority)
    },

    getHighPriorityAssignments: state => {
      return state.assignments.filter(assignment => assignment.priority === 'high')
    }
  },

  actions: {
    async fetchAssignments(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await assignmentsAPI.getAssignments(params)

        this.assignments = response.assignments
        this.pagination = pageStateFrom(response)

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

    async fetchAssignmentById(assignmentId: string) {
      this.loading = true
      this.error = null
      try {
        return await assignmentsAPI.getAssignment(assignmentId)
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async createAssignment(assignmentData: Schema<'GeneScopeAssignmentCreate'>) {
      this.loading = true
      this.error = null
      try {
        return await assignmentsAPI.createAssignment(assignmentData)
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
          assignment.priority = priority
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
        this.scopeAssignments[scopeId] = assignments
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

    async updateAssignment(assignmentId: string, updateData: Schema<'GeneScopeAssignmentUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const result = await assignmentsAPI.updateAssignment(assignmentId, updateData)
        const existing = this.assignments.find(a => a.id === assignmentId)
        if (existing) {
          existing.assigned_curator_id = result.assigned_curator_id ?? null
          existing.priority = result.priority
          existing.is_active = result.is_active
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
