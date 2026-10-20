import { defineStore } from 'pinia'
import { genesAPI } from '@/api'
import { toApiError, apiData } from './apiError'
import type { Schema } from '@/types/api'

/** Gene row in the store: API schema plus the scope-assignment list the table filters on. */
export interface GeneRecord extends Schema<'GeneWithAssignments'> {
  assignments?: Array<{ scope_id: string }>
}

export interface GeneSearchParams {
  query: string
  scope_id: string | null
  assignment_status: string | null
  curation_status: string | null
  sort_by: string
  sort_order: 'asc' | 'desc'
}

interface GenesPagination {
  page: number
  per_page: number
  total: number
  pages: number
}

interface GenesState {
  genes: GeneRecord[]
  currentGene: GeneRecord | null
  searchResults: GeneRecord[]
  geneAssignments: Record<string, Schema<'GeneScopeAssignment'>[]>
  geneCurationProgress: Record<string, Schema<'GeneCurationProgress'>>
  loading: boolean
  error: string | null
  pagination: GenesPagination
  searchParams: GeneSearchParams
}

export const useGenesStore = defineStore('genes', {
  state: (): GenesState => ({
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
    getGeneById: state => (id: string) => {
      return state.genes.find(gene => gene.id === id)
    },

    getGenesByScope: state => (scopeId: string) => {
      return state.genes.filter(gene =>
        gene.assignments?.some(assignment => assignment.scope_id === scopeId)
      )
    },

    getGeneAssignments: state => (geneId: string) => {
      return state.geneAssignments[geneId] || []
    },

    getGeneCurationProgress: state => (geneId: string) => {
      return state.geneCurationProgress[geneId] || {}
    },

    getUnassignedGenes: state => {
      return state.genes.filter(gene => !gene.assignments || gene.assignments.length === 0)
    }
  },

  actions: {
    async fetchGenes(params: Partial<GeneSearchParams> = {}) {
      this.loading = true
      this.error = null
      try {
        const response = apiData<
          { genes?: GeneRecord[]; data?: GeneRecord[]; pagination?: GenesPagination } & Record<
            string,
            unknown
          >
        >(
          await genesAPI.getGenes({
            ...this.searchParams,
            ...params
          })
        )

        this.genes = response.genes || response.data || (response as unknown as GeneRecord[])

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

    async fetchGeneById(id: string) {
      this.loading = true
      this.error = null
      try {
        const gene = apiData<GeneRecord>(await genesAPI.getGeneById(id))
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
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async createGene(geneData: Schema<'GeneCreate'>) {
      this.loading = true
      this.error = null
      try {
        const newGene = apiData<GeneRecord>(await genesAPI.createGene(geneData))
        this.genes.push(newGene)
        return newGene
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateGene(id: string, geneData: Schema<'GeneUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updatedGene = apiData<GeneRecord>(await genesAPI.updateGene(id, geneData))
        const index = this.genes.findIndex(g => g.id === id)
        if (index !== -1) {
          this.genes[index] = updatedGene
        }
        if (this.currentGene && this.currentGene.id === id) {
          this.currentGene = updatedGene
        }
        return updatedGene
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteGene(id: string) {
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
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchGeneAssignments(id: string) {
      try {
        const assignments = apiData<Schema<'GeneScopeAssignment'>[]>(
          await genesAPI.getGeneAssignments(id)
        )
        this.geneAssignments[id] = assignments
        return assignments
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchGeneCurationProgress(id: string) {
      try {
        const progress = apiData<Schema<'GeneCurationProgress'>>(
          await genesAPI.getGeneCurationProgress(id)
        )
        this.geneCurationProgress[id] = progress
        return progress
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async searchGenes(searchParams: Record<string, unknown>) {
      this.loading = true
      this.error = null
      try {
        const response = apiData<
          { genes?: GeneRecord[]; data?: GeneRecord[] } & Record<string, unknown>
        >(await genesAPI.searchGenes(searchParams))
        this.searchResults =
          response.genes || response.data || (response as unknown as GeneRecord[])
        return response
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    updateSearchParams(params: Partial<GeneSearchParams>) {
      this.searchParams = { ...this.searchParams, ...params }
    },

    setCurrentGene(gene: GeneRecord | null) {
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
        const stats = apiData<Schema<'GeneStatistics'>>(await genesAPI.getStatistics())
        return stats
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    clearError() {
      this.error = null
    }
  }
})
