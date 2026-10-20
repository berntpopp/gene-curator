/**
 * Precurations Pinia Store
 *
 * Manages precuration state following the curations.js pattern.
 * Handles CRUD operations, draft auto-save, and workflow transitions.
 */
import { defineStore } from 'pinia'
import { precurationsAPI } from '@/api/precurations'
import { logService } from '@/services/logService'
import { toApiError, apiData } from './apiError'
import type { Schema } from '@/types/api'

/** A precuration as listed (summary) or opened (full record); both carry the fields the store filters on. */
export type PrecurationRecord = Schema<'PrecurationSummary'> | Schema<'Precuration'>

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
  currentPrecuration: PrecurationRecord | null
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
        const response = apiData<{ precurations?: PrecurationRecord[]; total?: number }>(
          await precurationsAPI.getPrecurations({
            ...this.filters,
            ...params,
            skip: (this.pagination.page - 1) * this.pagination.per_page,
            limit: this.pagination.per_page
          })
        )

        this.precurations = response.precurations || []
        this.pagination.total = response.total || 0
        this.pagination.pages = Math.ceil(this.pagination.total / this.pagination.per_page)

        return response
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        const precuration = apiData<PrecurationRecord>(await precurationsAPI.getPrecuration(id))
        this.currentPrecuration = precuration

        // Update in list if exists
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = precuration
        }

        return precuration
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        const newPrecuration = apiData<PrecurationRecord>(
          await precurationsAPI.createPrecuration(data)
        )
        this.precurations.unshift(newPrecuration)
        this.pagination.total += 1
        return newPrecuration
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        const updated = apiData<PrecurationRecord>(
          await precurationsAPI.updatePrecuration(id, data)
        )

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = updated
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = updated
        }

        return updated
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        const updated = apiData<PrecurationRecord>(
          await precurationsAPI.saveDraft(id, {
            evidence_data: evidenceData
          })
        )

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = updated
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
        this.error = { message: toApiError(error).message, isAutoSave: true }
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
        const submitted = apiData<PrecurationRecord>(
          await precurationsAPI.submitPrecuration(id, { notes })
        )

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = submitted
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = submitted
        }

        return submitted
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        const result = apiData<{ curation_id?: string } & Record<string, unknown>>(
          await precurationsAPI.approvePrecuration(id)
        )

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = {
            ...this.precurations[index],
            status: 'approved'
          } as PrecurationRecord
        }

        return result // Contains curation_id if auto-created
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        const rejected = apiData<PrecurationRecord>(
          await precurationsAPI.rejectPrecuration(id, { reason })
        )

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = rejected
        }

        return rejected
      } catch (error) {
        this.error = { message: toApiError(error).message }
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
        this.error = { message: toApiError(error).message }
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
    setCurrentPrecuration(precuration: PrecurationRecord | null) {
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
