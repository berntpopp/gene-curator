import { defineStore } from 'pinia'
import { genesAPI } from '@/api'
import { errorMessage } from './apiError'
import { pageStateFrom, type PageState } from './pagination'
import type { Schema } from '@/types/api'

/** Gene row as listed by the API. */
export type GeneRecord = Schema<'GeneSummary'>
export type GeneDetail = Schema<'GeneWithAssignments'>

/** Client-side list state; `sort_*` and `scope_id` are sent to GET /genes/, the rest is UI filter state. */
export interface GeneSearchParams {
  query: string
  scope_id: string | null
  assignment_status: string | null
  curation_status: string | null
  sort_by: string
  sort_order: 'asc' | 'desc'
}

/** Parameters accepted by `fetchGenes` / `searchGenes`; `page` is 1-based and converted to skip/limit. */
export interface GeneListParams {
  page?: number
  skip?: number
  limit?: number
  scope_id?: string | null
  assigned_only?: boolean
  has_active_work?: boolean | null
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  query?: string | null
  chromosome?: string | null
  hgnc_id?: string | null
}

interface GenesState {
  genes: GeneRecord[]
  currentGene: GeneDetail | null
  searchResults: GeneRecord[]
  /** Server total for the active search (results are paged) */
  searchTotal: number
  geneAssignments: Record<string, Schema<'GeneAssignmentStatus'>>
  geneCurationProgress: Record<string, Schema<'GeneCurationProgress'>>
  loading: boolean
  error: string | null
  pagination: PageState
  searchParams: GeneSearchParams
}

/** Collapse a detail/created gene into the list-row shape. */
function toRecord(gene: Schema<'Gene'> | GeneDetail, previous?: GeneRecord): GeneRecord {
  return {
    id: gene.id,
    hgnc_id: gene.hgnc_id,
    approved_symbol: gene.approved_symbol,
    chromosome: gene.chromosome ?? null,
    location: gene.location ?? null,
    is_assigned: 'is_assigned_to_any_scope' in gene ? gene.is_assigned_to_any_scope : false,
    has_active_work: previous?.has_active_work ?? false
  }
}

/** Translate UI params (1-based page) to the backend's skip/limit query. */
function toQuery(params: GeneListParams, perPage: number): Record<string, unknown> {
  const { page, ...rest } = params
  const limit = rest.limit ?? perPage
  const skip = rest.skip ?? (page ? (page - 1) * limit : 0)
  return Object.fromEntries(
    Object.entries({ ...rest, skip, limit }).filter(([, v]) => v !== null && v !== undefined)
  )
}

export const useGenesStore = defineStore('genes', {
  state: (): GenesState => ({
    genes: [],
    currentGene: null,
    searchResults: [],
    searchTotal: 0,
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

    getGeneAssignments: state => (geneId: string) => {
      return state.geneAssignments[geneId]
    },

    getGeneCurationProgress: state => (geneId: string) => {
      return state.geneCurationProgress[geneId]
    },

    getUnassignedGenes: state => {
      return state.genes.filter(gene => !gene.is_assigned)
    }
  },

  actions: {
    async fetchGenes(params: GeneListParams = {}) {
      this.loading = true
      this.error = null
      try {
        const { sort_by, sort_order, scope_id } = this.searchParams
        const response = await genesAPI.getGenes(
          toQuery({ sort_by, sort_order, scope_id, ...params }, this.pagination.per_page)
        )

        this.genes = response.genes
        this.pagination = pageStateFrom(response)

        return response
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    /** Check a stored gene annotation against HGNC. Callers handle errors; nothing is cached. */
    validateGene(id: string) {
      return genesAPI.validateGene(id)
    },

    async fetchGeneById(id: string) {
      this.loading = true
      this.error = null
      try {
        const gene = await genesAPI.getGeneById(id)
        this.currentGene = gene

        // Update the gene in the list if it exists
        const index = this.genes.findIndex(g => g.id === id)
        if (index !== -1) {
          this.genes[index] = toRecord(gene, this.genes[index])
        } else {
          this.genes.push(toRecord(gene))
        }

        return gene
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async createGene(geneData: Schema<'GeneCreate'>) {
      this.loading = true
      this.error = null
      try {
        const newGene = await genesAPI.createGene(geneData)
        this.genes.push(toRecord(newGene))
        return newGene
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateGene(id: string, geneData: Schema<'GeneUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updatedGene = await genesAPI.updateGene(id, geneData)
        const index = this.genes.findIndex(g => g.id === id)
        if (index !== -1) {
          this.genes[index] = toRecord(updatedGene, this.genes[index])
        }
        if (this.currentGene && this.currentGene.id === id) {
          this.currentGene = { ...this.currentGene, ...updatedGene }
        }
        return updatedGene
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
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
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchGeneAssignments(id: string) {
      try {
        const assignments = await genesAPI.getGeneAssignments(id)

        this.geneAssignments[id] = assignments
        return assignments
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async fetchGeneCurationProgress(id: string) {
      try {
        const progress = await genesAPI.getGeneCurationProgress(id)

        this.geneCurationProgress[id] = progress
        return progress
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async searchGenes(searchParams: GeneListParams) {
      this.loading = true
      this.error = null
      try {
        const { query, chromosome, hgnc_id } = searchParams
        const [response, total] = await Promise.all([
          genesAPI.searchGenes(toQuery(searchParams, this.pagination.per_page)),
          genesAPI.countSearchGenes(
            Object.fromEntries(Object.entries({ query, chromosome, hgnc_id }).filter(([, v]) => v))
          )
        ])
        this.searchResults = response
        this.searchTotal = total
        return response
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    updateSearchParams(params: Partial<GeneSearchParams>) {
      this.searchParams = { ...this.searchParams, ...params }
    },

    setCurrentGene(gene: GeneDetail | null) {
      this.currentGene = gene
    },

    clearCurrentGene() {
      this.currentGene = null
    },

    clearSearchResults() {
      this.searchResults = []
      this.searchTotal = 0
    },

    clearError() {
      this.error = null
    }
  }
})
