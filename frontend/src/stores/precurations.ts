/**
 * Precurations Pinia Store
 *
 * Manages precuration state following the curations.js pattern.
 * Handles CRUD operations, draft auto-save, and workflow transitions.
 */
import { defineStore } from 'pinia'
import { precurationsAPI } from '@/api/precurations'
import { logService } from '@/services/logService'
import { errorMessage, toApiError } from './apiError'
import type { Schema } from '@/types/api'

/** A precuration row as listed by the API. */
export type PrecurationRecord = Schema<'PrecurationSummary'>
/** A precuration opened for viewing/editing. */
export type PrecurationDetail = Schema<'Precuration'>

/** Row for a just-created precuration; names are unknown until the list is refetched. */
function toSummary(p: PrecurationDetail): PrecurationRecord {
  return {
    id: p.id,
    gene_id: p.gene_id,
    gene_symbol: '',
    scope_id: p.scope_id,
    scope_name: '',
    status: p.status,
    workflow_stage: p.workflow_stage,
    mondo_id: null,
    disease_name: null,
    mode_of_inheritance: null,
    is_draft: p.is_draft,
    created_at: p.created_at,
    updated_at: p.updated_at,
    curator_name: null
  }
}

/** Copy the mutable server-side fields of a saved precuration onto a list row. */
function refreshRow(row: PrecurationRecord, p: PrecurationDetail): PrecurationRecord {
  return {
    ...row,
    status: p.status,
    workflow_stage: p.workflow_stage,
    is_draft: p.is_draft,
    updated_at: p.updated_at
  }
}

interface PrecurationsFilters {
  scope_id: string | null
  gene_id: string | null
  status: string | null
}

interface PrecurationsPagination {
  page: number
  per_page: number
  total: number
  pages: number
}

interface PrecurationsState {
  precurations: PrecurationRecord[]
  currentPrecuration: PrecurationDetail | null
  loading: boolean
  error: { message?: string; isAutoSave?: boolean } | null
  pagination: PrecurationsPagination
  filters: PrecurationsFilters
}

export const usePrecurationsStore = defineStore('precurations', {
  state: (): PrecurationsState => ({
    precurations: [],
    currentPrecuration: null,
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
      status: null
    }
  }),

  getters: {
    getPrecurationById: state => (id: string) => {
      return state.precurations.find(precuration => precuration.id === id)
    },

    getPrecurationsByScope: state => (scopeId: string) => {
      return state.precurations.filter(precuration => precuration.scope_id === scopeId)
    },

    getPrecurationsByGene: state => (geneId: string) => {
      return state.precurations.filter(precuration => precuration.gene_id === geneId)
    },

    draftPrecurations: state => {
      return state.precurations.filter(precuration => precuration.status === 'draft')
    },

    submittedPrecurations: state => {
      return state.precurations.filter(precuration => precuration.status === 'submitted')
    },

    approvedPrecurations: state => {
      return state.precurations.filter(precuration => precuration.status === 'approved')
    },

    hasError: state => state.error !== null
  },

  actions: {
    /**
     * Fetch precurations with optional filters
     */
    async fetchPrecurations(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        // The API names the status filter `precuration_status`; `status` would be ignored
        const { status, ...filters } = { ...this.filters, ...params }
        const response = await precurationsAPI.getPrecurations({
          ...filters,
          precuration_status: status,
          skip: (this.pagination.page - 1) * this.pagination.per_page,
          limit: this.pagination.per_page
        })

        this.precurations = response.precurations
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
     * Fetch single precuration by ID
     */
    async fetchPrecurationById(id: string) {
      this.loading = true
      this.error = null
      try {
        const precuration = await precurationsAPI.getPrecuration(id)
        this.currentPrecuration = precuration

        // Update in list if exists
        const index = this.precurations.findIndex(p => p.id === id)
        const row = this.precurations[index]
        if (row) {
          this.precurations[index] = refreshRow(row, precuration)
        }

        return precuration
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new precuration
     */
    async createPrecuration(data: Parameters<typeof precurationsAPI.createPrecuration>[0]) {
      this.loading = true
      this.error = null
      try {
        const newPrecuration = await precurationsAPI.createPrecuration(data)

        this.precurations.unshift(toSummary(newPrecuration))
        this.pagination.total += 1
        return newPrecuration
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update precuration
     */
    async updatePrecuration(
      id: string,
      data: Parameters<typeof precurationsAPI.updatePrecuration>[1]
    ) {
      this.loading = true
      this.error = null
      try {
        const updated = await precurationsAPI.updatePrecuration(id, data)

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        const row = this.precurations[index]
        if (row) {
          this.precurations[index] = refreshRow(row, updated)
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = updated
        }

        return updated
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Save precuration as draft (auto-save)
     * Does NOT set loading state for background operation
     */
    async saveDraft(id: string, evidenceData: Record<string, unknown>) {
      this.error = null
      try {
        const updated = await precurationsAPI.saveDraft(id, {
          evidence_data: evidenceData
        })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        const row = this.precurations[index]
        if (row) {
          this.precurations[index] = refreshRow(row, updated)
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = updated
        }

        return updated
      } catch (error) {
        // Use logService instead of console.error (per CLAUDE.md)
        logService.error('Auto-save failed', {
          precuration_id: id,
          error: toApiError(error).message
        })
        this.error = { message: errorMessage(error, 'Request failed'), isAutoSave: true }
        return null
      }
    },

    /**
     * Submit precuration for review
     */
    async submitForReview(id: string, notes: string | null = null) {
      this.loading = true
      this.error = null
      try {
        const submitted = await precurationsAPI.submitPrecuration(id, { notes })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        const row = this.precurations[index]
        if (row) {
          this.precurations[index] = refreshRow(row, submitted)
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = submitted
        }

        return submitted
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Approve precuration (may auto-create curation)
     */
    async approvePrecuration(id: string) {
      this.loading = true
      this.error = null
      try {
        const result = await precurationsAPI.approvePrecuration(id)

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        const row = this.precurations[index]
        if (row) {
          this.precurations[index] = { ...row, status: 'approved' }
        }

        return result // Contains curation_id if auto-created
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Reject precuration
     */
    async rejectPrecuration(id: string, reason: string) {
      this.loading = true
      this.error = null
      try {
        const rejected = await precurationsAPI.rejectPrecuration(id, { reason })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        const row = this.precurations[index]
        if (row) {
          this.precurations[index] = refreshRow(row, rejected)
        }

        return rejected
      } catch (error) {
        this.error = { message: errorMessage(error, 'Request failed') }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Delete (archive) precuration
     */
    async deletePrecuration(id: string) {
      this.loading = true
      this.error = null
      try {
        await precurationsAPI.deletePrecuration(id)

        // Remove from list
        this.precurations = this.precurations.filter(p => p.id !== id)
        this.pagination.total = Math.max(0, this.pagination.total - 1)

        // Clear current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = null
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
     * Update filters and reset to first page
     */
    updateFilters(newFilters: Partial<PrecurationsFilters>) {
      this.filters = { ...this.filters, ...newFilters }
      this.pagination.page = 1
    },

    /**
     * Set current page
     */
    setPage(page: number) {
      this.pagination.page = page
    },

    /**
     * Set current precuration
     */
    setCurrentPrecuration(precuration: PrecurationDetail | null) {
      this.currentPrecuration = precuration
    },

    /**
     * Clear current precuration
     */
    clearCurrentPrecuration() {
      this.currentPrecuration = null
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
      this.precurations = []
      this.currentPrecuration = null
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
        status: null
      }
    }
  }
})
