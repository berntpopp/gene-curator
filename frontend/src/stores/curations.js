/**
 * Curations Pinia Store
 *
 * Manages curation state following the genes.js pattern.
 * Handles CRUD operations, optimistic locking conflicts, and draft auto-save.
 */
import { defineStore } from 'pinia'
import { curationsAPI } from '@/api/curations'

export const useCurationsStore = defineStore('curations', {
  state: () => ({
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
    getCurationById: state => id => {
      return state.curations.find(curation => curation.id === id)
    },

    getCurationsByScope: state => scopeId => {
      return state.curations.filter(curation => curation.scope_id === scopeId)
    },

    getCurationsByGene: state => geneId => {
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
    async fetchCurations(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await curationsAPI.getCurations({
          ...this.filters,
          ...params,
          skip: (this.pagination.page - 1) * this.pagination.per_page,
          limit: this.pagination.per_page
        })

        this.curations = response.curations || []
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
     * Fetch single curation by ID
     */
    async fetchCurationById(id) {
      this.loading = true
      this.error = null
      try {
        const curation = await curationsAPI.getCuration(id)
        this.currentCuration = curation

        // Update in list if exists
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = curation
        }

        return curation
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new curation
     */
    async createCuration(data) {
      this.loading = true
      this.error = null
      try {
        const newCuration = await curationsAPI.createCuration(data)
        this.curations.unshift(newCuration)
        this.pagination.total += 1
        return newCuration
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update curation with optimistic locking
     * Handles 409 Conflict by setting isConflict error
     */
    async updateCuration(id, data) {
      this.loading = true
      this.error = null
      try {
        const updated = await curationsAPI.updateCuration(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = updated
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = updated
        }

        return updated
      } catch (error) {
        // Handle 409 Conflict specially
        if (error.response?.status === 409) {
          const conflictData = error.response.data
          this.error = {
            message: 'Another user has modified this curation. Please refresh and try again.',
            isConflict: true,
            currentVersion: conflictData.current_lock_version,
            yourVersion: conflictData.your_lock_version,
            currentState: conflictData.current_state
          }
        } else {
          this.error = { message: error.message }
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
    async saveDraft(id, data) {
      this.error = null
      try {
        const updated = await curationsAPI.saveDraft(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = updated
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = updated
        }

        return updated
      } catch (error) {
        // Don't throw for auto-save failures, just log
        this.error = { message: error.message, isAutoSave: true }
        return null
      }
    },

    /**
     * Submit curation for review
     */
    async submitCuration(id, data = {}) {
      this.loading = true
      this.error = null
      try {
        const submitted = await curationsAPI.submitCuration(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = submitted
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = submitted
        }

        return submitted
      } catch (error) {
        if (error.response?.status === 409) {
          this.error = {
            message: 'Curation was modified. Please refresh and try again.',
            isConflict: true
          }
        } else {
          this.error = { message: error.message }
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Delete (archive) curation
     */
    async deleteCuration(id) {
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
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Calculate score for curation
     */
    async calculateScore(id) {
      this.loading = true
      this.error = null
      try {
        const scoreResult = await curationsAPI.calculateScore(id)
        return scoreResult
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update filters and refetch
     */
    updateFilters(newFilters) {
      this.filters = { ...this.filters, ...newFilters }
      this.pagination.page = 1 // Reset to first page
    },

    /**
     * Set current page and refetch
     */
    setPage(page) {
      this.pagination.page = page
    },

    /**
     * Set current curation
     */
    setCurrentCuration(curation) {
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
