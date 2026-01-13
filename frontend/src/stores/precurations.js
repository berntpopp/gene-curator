/**
 * Precurations Pinia Store
 *
 * Manages precuration state following the curations.js pattern.
 * Handles CRUD operations, draft auto-save, and workflow transitions.
 */
import { defineStore } from 'pinia'
import { precurationsAPI } from '@/api/precurations'
import { logService } from '@/services/logService'

export const usePrecurationsStore = defineStore('precurations', {
  state: () => ({
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
    getPrecurationById: state => id => {
      return state.precurations.find(precuration => precuration.id === id)
    },

    getPrecurationsByScope: state => scopeId => {
      return state.precurations.filter(precuration => precuration.scope_id === scopeId)
    },

    getPrecurationsByGene: state => geneId => {
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
    async fetchPrecurations(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await precurationsAPI.getPrecurations({
          ...this.filters,
          ...params,
          skip: (this.pagination.page - 1) * this.pagination.per_page,
          limit: this.pagination.per_page
        })

        this.precurations = response.precurations || []
        this.pagination.total = response.total || 0
        this.pagination.pages = Math.ceil(this.pagination.total / this.pagination.per_page)

        return response
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Fetch single precuration by ID
     */
    async fetchPrecurationById(id) {
      this.loading = true
      this.error = null
      try {
        const precuration = await precurationsAPI.getPrecuration(id)
        this.currentPrecuration = precuration

        // Update in list if exists
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = precuration
        }

        return precuration
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new precuration
     */
    async createPrecuration(data) {
      this.loading = true
      this.error = null
      try {
        const newPrecuration = await precurationsAPI.createPrecuration(data)
        this.precurations.unshift(newPrecuration)
        this.pagination.total += 1
        return newPrecuration
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update precuration
     */
    async updatePrecuration(id, data) {
      this.loading = true
      this.error = null
      try {
        const updated = await precurationsAPI.updatePrecuration(id, data)

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
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Save precuration as draft (auto-save)
     * Does NOT set loading state for background operation
     */
    async saveDraft(id, evidenceData) {
      this.error = null
      try {
        const updated = await precurationsAPI.saveDraft(id, {
          evidence_data: evidenceData
        })

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
          error: error.message
        })
        this.error = { message: error.message, isAutoSave: true }
        return null
      }
    },

    /**
     * Submit precuration for review
     */
    async submitForReview(id, notes = null) {
      this.loading = true
      this.error = null
      try {
        const submitted = await precurationsAPI.submitPrecuration(id, { notes })

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
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Approve precuration (may auto-create curation)
     */
    async approvePrecuration(id) {
      this.loading = true
      this.error = null
      try {
        const result = await precurationsAPI.approvePrecuration(id)

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = {
            ...this.precurations[index],
            status: 'approved'
          }
        }

        return result // Contains curation_id if auto-created
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Reject precuration
     */
    async rejectPrecuration(id, reason) {
      this.loading = true
      this.error = null
      try {
        const rejected = await precurationsAPI.rejectPrecuration(id, { reason })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = rejected
        }

        return rejected
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Delete (archive) precuration
     */
    async deletePrecuration(id) {
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
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update filters and reset to first page
     */
    updateFilters(newFilters) {
      this.filters = { ...this.filters, ...newFilters }
      this.pagination.page = 1
    },

    /**
     * Set current page
     */
    setPage(page) {
      this.pagination.page = page
    },

    /**
     * Set current precuration
     */
    setCurrentPrecuration(precuration) {
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
