import { defineStore } from 'pinia'
import { genesAPI } from '@/api'

export const useGenesStore = defineStore('genes', {
  state: () => ({
    genes: [],
    currentGene: null,
    searchResults: [],
    geneAssignments: {},
    geneCurationProgress: {},
    loading: false,
    error: null,
    pagination: {
      page: 1,
      per_page: 20,
      total: 0,
      pages: 0
    },
    searchParams: {
      query: '',
      scope_id: null,
      assignment_status: null,
      curation_status: null,
      sort_by: 'approved_symbol',
      sort_order: 'asc'
    }
  }),

  getters: {
    getGeneById: state => id => {
      return state.genes.find(gene => gene.id === id)
    },

    getGenesByScope: state => scopeId => {
      return state.genes.filter(gene =>
        gene.assignments?.some(assignment => assignment.scope_id === scopeId)
      )
    },

    getGeneAssignments: state => geneId => {
      return state.geneAssignments[geneId] || []
    },

    getGeneCurationProgress: state => geneId => {
      return state.geneCurationProgress[geneId] || {}
    },

    getUnassignedGenes: state => {
      return state.genes.filter(gene => !gene.assignments || gene.assignments.length === 0)
    }
  },

  actions: {
    async fetchGenes(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await genesAPI.getGenes({
          ...this.searchParams,
          ...params
        })

        this.genes = response.genes || response.data || response

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

    async fetchGeneById(id) {
      this.loading = true
      this.error = null
      try {
        const gene = await genesAPI.getGeneById(id)
        this.currentGene = gene

        // Update the gene in the list if it exists
        const index = this.genes.findIndex(g => g.id === id)
        if (index !== -1) {
          this.genes[index] = gene
        } else {
          this.genes.push(gene)
        }

        return gene
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createGene(geneData) {
      this.loading = true
      this.error = null
      try {
        const newGene = await genesAPI.createGene(geneData)
        this.genes.push(newGene)
        return newGene
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateGene(id, geneData) {
      this.loading = true
      this.error = null
      try {
        const updatedGene = await genesAPI.updateGene(id, geneData)
        const index = this.genes.findIndex(g => g.id === id)
        if (index !== -1) {
          this.genes[index] = updatedGene
        }
        if (this.currentGene && this.currentGene.id === id) {
          this.currentGene = updatedGene
        }
        return updatedGene
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteGene(id) {
      this.loading = true
      this.error = null
      try {
        await genesAPI.deleteGene(id)
        this.genes = this.genes.filter(g => g.id !== id)
        if (this.currentGene && this.currentGene.id === id) {
          this.currentGene = null
        }
        return true
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchGeneAssignments(id) {
      try {
        const assignments = await genesAPI.getGeneAssignments(id)
        this.geneAssignments[id] = assignments
        return assignments
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchGeneCurationProgress(id) {
      try {
        const progress = await genesAPI.getGeneCurationProgress(id)
        this.geneCurationProgress[id] = progress
        return progress
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async searchGenes(searchParams) {
      this.loading = true
      this.error = null
      try {
        const response = await genesAPI.searchGenes(searchParams)
        this.searchResults = response.genes || response.data || response
        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    updateSearchParams(params) {
      this.searchParams = { ...this.searchParams, ...params }
    },

    setCurrentGene(gene) {
      this.currentGene = gene
    },

    clearCurrentGene() {
      this.currentGene = null
    },

    clearSearchResults() {
      this.searchResults = []
    },

    async fetchStatistics() {
      try {
        const stats = await genesAPI.getStatistics()
        return stats
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
