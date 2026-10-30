/**
 * Curations Pinia Store
 *
 * Manages curation state following the genes.js pattern.
 * Handles CRUD operations, optimistic locking conflicts, and draft auto-save.
 */
import { defineStore } from 'pinia'
import { errorMessage, toApiError } from './apiError'
import { curationsAPI } from '@/api/curations'
import type { Schema } from '@/types/api'

/** A curation row as listed by the API. */
export type CurationRecord = Schema<'CurationSummary'>
/** A curation opened for viewing/editing. */
export type CurationDetail = Schema<'CurationDetail'>

/** Row for a just-created curation; names are unknown until the list is refetched. */
function toSummary(c: Schema<'Curation'>): CurationRecord {
  return {
    id: c.id,
    gene_id: c.gene_id,
    gene_symbol: '',
    scope_id: c.scope_id,
    scope_name: '',
    status: c.status,
    workflow_stage: c.workflow_stage,
    computed_verdict: c.computed_verdict,
    final_classification: c.final_classification,
    computed_scores: c.computed_scores,
    relationship_type: 'mendelian', // like the names: correct once the list is refetched
    is_draft: c.is_draft,
    created_at: c.created_at,
    updated_at: c.updated_at,
    curator_name: null,
    created_by: c.created_by,
    lock_version: c.lock_version
  }
}

/** Copy the mutable server-side fields of a saved curation onto a list row. */
function refreshRow(row: CurationRecord, c: Schema<'Curation'>): CurationRecord {
  return {
    ...row,
    status: c.status,
    workflow_stage: c.workflow_stage,
    computed_verdict: c.computed_verdict,
    final_classification: c.final_classification,
    computed_scores: c.computed_scores,
    is_draft: c.is_draft,
    updated_at: c.updated_at,
    lock_version: c.lock_version
  }
}

/** Error state: plain message, or extra data for optimistic-lock conflicts (409). */
export interface CurationError {
  message?: string
  isConflict?: boolean
  isAutoSave?: boolean
  currentVersion?: number
  yourVersion?: number
  currentState?: string
  /** A create was refused (409) for this open curation of the same entity or gene */
  openCurationId?: string
}

interface CurationsFilters {
  scope_id: string | null
  gene_id: string | null
  status: string | null
  curator_id: string | null
}

interface CurationsPagination {
  page: number
  per_page: number
  total: number
  pages: number
}

interface CurationsState {
  curations: CurationRecord[]
  currentCuration: CurationDetail | null
  loading: boolean
  error: CurationError | null
  pagination: CurationsPagination
  filters: CurationsFilters
}

export const useCurationsStore = defineStore('curations', {
  state: (): CurationsState => ({
    curations: [],
    currentCuration: null,
    loading: false,
    error: null,
    pagination: {
      page: 1,
      per_page: 50,
      total: 0,
      pages: 0
    },
    filters: {
      scope_id: null,
      gene_id: null,
      status: null,
      curator_id: null
    }
  }),

  getters: {
    getCurationById: state => (id: string) => {
      return state.curations.find(curation => curation.id === id)
    },

    getCurationsByScope: state => (scopeId: string) => {
      return state.curations.filter(curation => curation.scope_id === scopeId)
    },

    getCurationsByGene: state => (geneId: string) => {
      return state.curations.filter(curation => curation.gene_id === geneId)
    },

    getDraftCurations: state => {
      return state.curations.filter(curation => curation.is_draft === true)
    },

    getSubmittedCurations: state => {
      return state.curations.filter(curation => curation.status === 'submitted')
    },

    hasError: state => state.error !== null,

    isConflictError: state => state.error?.isConflict === true
  },

  actions: {
    /**
     * Fetch curations with optional filters
     */
    async fetchCurations(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        // The API names the status filter `curation_status`; `status` would be ignored
        const { status, ...filters } = { ...this.filters, ...params }
        const response = await curationsAPI.getCurations({
          ...filters,
          curation_status: status,
          skip: (this.pagination.page - 1) * this.pagination.per_page,
          limit: this.pagination.per_page
        })

        this.curations = response.curations
        this.pagination.total = response.total
        this.pagination.pages = Math.ceil(this.pagination.total / this.pagination.per_page)

        return response
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Fetch single curation by ID
     */
    async fetchCurationById(id: string) {
      this.loading = true
      this.error = null
      try {
        const curation = await curationsAPI.getCuration(id)
        this.currentCuration = curation

        // Update in list if exists
        const index = this.curations.findIndex(c => c.id === id)
        const row = this.curations[index]
        if (row) {
          this.curations[index] = refreshRow(row, curation)
        }

        return curation
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new curation
     */
    async createCuration(data: Parameters<typeof curationsAPI.createCuration>[0]) {
      this.loading = true
      this.error = null
      try {
        const newCuration = await curationsAPI.createCuration(data)
        this.curations.unshift(toSummary(newCuration))
        this.pagination.total += 1
        return newCuration
      } catch (error) {
        const detail = toApiError(error).response?.data?.detail as
          { message?: string; curation_id?: string } | undefined
        this.error = detail?.curation_id
          ? { message: detail.message, openCurationId: detail.curation_id }
          : { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update curation with optimistic locking
     * Handles 409 Conflict by setting isConflict error
     */
    async updateCuration(id: string, data: Schema<'CurationUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updated = await curationsAPI.updateCuration(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        const row = this.curations[index]
        if (row) {
          this.curations[index] = refreshRow(row, updated)
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = { ...this.currentCuration, ...updated }
        }

        return updated
      } catch (error) {
        // Handle 409 Conflict specially
        const apiError = toApiError(error)
        if (apiError.response?.status === 409) {
          const conflictData = apiError.response.data ?? {}
          this.error = {
            message: 'Another user has modified this curation. Please refresh and try again.',
            isConflict: true,
            currentVersion: conflictData.current_lock_version as number | undefined,
            yourVersion: conflictData.your_lock_version as number | undefined,
            currentState: conflictData.current_state as string | undefined
          }
        } else {
          this.error = { message: errorMessage(error, 'Request failed') }
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Save curation as draft (auto-save)
     * Does NOT set loading state for background operation
     */
    async saveDraft(id: string, data: Schema<'CurationDraftSave'>) {
      this.error = null
      try {
        const updated = await curationsAPI.saveDraft(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        const row = this.curations[index]
        if (row) {
          this.curations[index] = refreshRow(row, updated)
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = { ...this.currentCuration, ...updated }
        }

        return updated
      } catch (error) {
        const apiError = toApiError(error)
        if (apiError.response?.status === 409) {
          // Another tab saved first: never overwrite it; the workspace shows the conflict
          const data = apiError.response.data ?? {}
          this.error = {
            message: 'Another user or tab has modified this curation. Reload to see their version.',
            isConflict: true,
            currentVersion: data.current_lock_version as number | undefined,
            yourVersion: data.your_lock_version as number | undefined
          }
        } else {
          // Don't throw for auto-save failures, just log
          this.error = { message: errorMessage(error, 'Request failed'), isAutoSave: true }
        }
        return null
      }
    },

    /**
     * Submit curation for review
     */
    async submitCuration(id: string, data: Partial<Schema<'CurationSubmit'>> = {}) {
      this.loading = true
      this.error = null
      try {
        const submitted = await curationsAPI.submitCuration(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        const row = this.curations[index]
        if (row) {
          this.curations[index] = refreshRow(row, submitted)
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = { ...this.currentCuration, ...submitted }
        }

        return submitted
      } catch (error) {
        const apiError = toApiError(error)
        if (apiError.response?.status === 409) {
          this.error = {
            message: 'Curation was modified. Please refresh and try again.',
            isConflict: true
          }
        } else {
          this.error = { message: errorMessage(error, 'Request failed') }
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Delete (archive) curation
     */
    async deleteCuration(id: string) {
      this.loading = true
      this.error = null
      try {
        await curationsAPI.deleteCuration(id)

        // Remove from list
        this.curations = this.curations.filter(c => c.id !== id)
        this.pagination.total = Math.max(0, this.pagination.total - 1)

        // Clear current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = null
        }

        return true
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Calculate score for curation
     */
    async calculateScore(id: string) {
      this.loading = true
      this.error = null
      try {
        const scoreResult = await curationsAPI.calculateScore(id)
        return scoreResult
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update filters and refetch
     */
    updateFilters(newFilters: Partial<CurationsFilters>) {
      this.filters = { ...this.filters, ...newFilters }
      this.pagination.page = 1 // Reset to first page
    },

    /**
     * Set current page and refetch
     */
    setPage(page: number) {
      this.pagination.page = page
    },

    /**
     * Set current curation
     */
    setCurrentCuration(curation: CurationDetail | null) {
      this.currentCuration = curation
    },

    /**
     * Clear current curation
     */
    clearCurrentCuration() {
      this.currentCuration = null
    },

    /**
     * Clear error
     */
    clearError() {
      this.error = null
    },

    /**
     * Reset store to initial state
     */
    $reset() {
      this.curations = []
      this.currentCuration = null
      this.loading = false
      this.error = null
      this.pagination = {
        page: 1,
        per_page: 50,
        total: 0,
        pages: 0
      }
      this.filters = {
        scope_id: null,
        gene_id: null,
        status: null,
        curator_id: null
      }
    }
  }
})
