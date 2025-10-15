import { defineStore } from 'pinia'
import { evidenceAPI } from '@/api/evidence.js'
import { logService } from '@/services/logService'

/**
 * Evidence store for managing ClinGen SOP v11 evidence items
 */
export const useEvidenceStore = defineStore('evidence', {
  state: () => ({
    evidence: new Map(),
    loading: false,
    error: null
  }),

  getters: {
    /**
     * Get all evidence items for a curation, sorted by creation date (newest first)
     */
    getEvidenceByCuration: state => curationId => {
      return Array.from(state.evidence.values())
        .filter(item => item.curation_id === curationId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    },

    /**
     * Get evidence items by category for a curation
     */
    getEvidenceByCategory: state => (curationId, category) => {
      return Array.from(state.evidence.values())
        .filter(item => item.curation_id === curationId && item.evidence_category === category)
    },

    /**
     * Count genetic evidence items for a curation
     */
    geneticEvidenceCount: state => curationId => {
      return Array.from(state.evidence.values())
        .filter(item => item.curation_id === curationId && item.evidence_type === 'genetic')
        .length
    },

    /**
     * Count experimental evidence items for a curation
     */
    experimentalEvidenceCount: state => curationId => {
      return Array.from(state.evidence.values())
        .filter(item => item.curation_id === curationId && item.evidence_type === 'experimental')
        .length
    }
  },

  actions: {
    /**
     * Fetch all evidence items for a curation
     */
    async fetchEvidenceForCuration(curationId) {
      this.loading = true
      this.error = null

      try {
        const items = await evidenceAPI.getEvidenceItems(curationId)
        items.forEach(item => this.evidence.set(item.id, item))
        logService.info('Evidence items fetched', { curationId, count: items.length })
        return items
      } catch (error) {
        this.error = error.message || 'Failed to fetch evidence'
        logService.error('Failed to fetch evidence', { curationId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new evidence item
     */
    async createEvidence(curationId, data) {
      this.loading = true
      this.error = null

      try {
        const created = await evidenceAPI.createEvidenceItem(curationId, data)
        this.evidence.set(created.id, created)
        logService.info('Evidence item created', { curationId, itemId: created.id })
        return created
      } catch (error) {
        this.error = error.message || 'Failed to create evidence'
        logService.error('Failed to create evidence', { curationId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update evidence item
     */
    async updateEvidence(curationId, itemId, data) {
      this.loading = true
      this.error = null

      try {
        const updated = await evidenceAPI.updateEvidenceItem(curationId, itemId, data)
        this.evidence.set(updated.id, updated)
        logService.info('Evidence item updated', { curationId, itemId })
        return updated
      } catch (error) {
        this.error = error.message || 'Failed to update evidence'
        logService.error('Failed to update evidence', { curationId, itemId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Delete evidence item (soft delete)
     */
    async deleteEvidence(curationId, itemId) {
      this.loading = true
      this.error = null

      try {
        await evidenceAPI.deleteEvidenceItem(curationId, itemId)
        this.evidence.delete(itemId)
        logService.info('Evidence item deleted', { curationId, itemId })
      } catch (error) {
        this.error = error.message || 'Failed to delete evidence'
        logService.error('Failed to delete evidence', { curationId, itemId, error: error.message })
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Clear all evidence from store
     */
    clearEvidence() {
      this.evidence.clear()
      this.error = null
    },

    /**
     * Clear error state
     */
    clearError() {
      this.error = null
    }
  }
})
