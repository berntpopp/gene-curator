/**
 * Gene Catalogue Pinia Store
 *
 * Manages state for the Gene Catalogue - a read-only aggregation view
 * of genes with finished curations across all scopes.
 *
 * Key principles:
 * - Read-only: No write operations
 * - Scope-independent: Does not affect scope workflows
 * - Derived data only: All content computed from active curations
 */
import { defineStore } from 'pinia'
import { geneCatalogueAPI } from '@/api/geneCatalogue'
import { toApiError } from './apiError'
import type { Schema } from '@/types/api'

interface CatalogueFilters {
  search: string | null
  classification: string | null
  disease: string | null
  scopeId: string | null
  chromosome: string | null
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

interface CataloguePagination {
  page: number
  perPage: number
  total: number
  hasNext: boolean
  hasPrev: boolean
}

interface CatalogueSummary {
  totalGenesCurated: number
  totalCurations: number
  totalScopes: number
  classificationSummary: Record<string, number>
}

interface CatalogueFilterOptions {
  classifications: string[]
  diseases: string[]
  scopes: Schema<'ScopeFilterOption'>[]
  loaded: boolean
}

interface GeneCatalogueState {
  entries: Schema<'GeneCatalogueEntry'>[]
  loading: boolean
  error: { message: string } | null
  pagination: CataloguePagination
  filters: CatalogueFilters
  summary: CatalogueSummary
  filterOptions: CatalogueFilterOptions
  expandedGeneIds: Set<string>
}

const DEFAULT_FILTERS: CatalogueFilters = {
  search: null,
  classification: null,
  disease: null,
  scopeId: null,
  chromosome: null,
  sortBy: 'approved_symbol',
  sortOrder: 'asc'
}

export const useGeneCatalogueStore = defineStore('geneCatalogue', {
  state: (): GeneCatalogueState => ({
    // Catalogue entries (genes with curations)
    entries: [],

    // Loading and error states
    loading: false,
    error: null,

    // Pagination
    pagination: {
      page: 1,
      perPage: 20,
      total: 0,
      hasNext: false,
      hasPrev: false
    },

    // Active filters
    filters: { ...DEFAULT_FILTERS },

    // Summary statistics
    summary: {
      totalGenesCurated: 0,
      totalCurations: 0,
      totalScopes: 0,
      classificationSummary: {}
    },

    // Available filter options (cached)
    filterOptions: {
      classifications: [],
      diseases: [],
      scopes: [],
      loaded: false
    },

    // Expanded row tracking
    expandedGeneIds: new Set()
  }),

  getters: {
    /**
     * Get catalogue entry by gene ID
     */
    getEntryByGeneId: state => (geneId: string) => {
      return state.entries.find(entry => entry.gene_id === geneId)
    },

    /**
     * Check if a gene row is expanded
     */
    isGeneExpanded: state => (geneId: string) => {
      return state.expandedGeneIds.has(geneId)
    },

    /**
     * Get all expanded gene IDs as array
     */
    expandedGenes: state => {
      return Array.from(state.expandedGeneIds)
    },

    /**
     * Check if any filters are active
     */
    hasActiveFilters: state => {
      return !!(
        state.filters.search ||
        state.filters.classification ||
        state.filters.disease ||
        state.filters.scopeId ||
        state.filters.chromosome
      )
    },

    /**
     * Get total pages based on pagination
     */
    totalPages: state => {
      return Math.ceil(state.pagination.total / state.pagination.perPage)
    }
  },

  actions: {
    /**
     * Fetch catalogue entries with current filters and pagination
     */
    async fetchCatalogue(params: { page?: number } = {}) {
      this.loading = true
      this.error = null

      try {
        const skip = ((params.page || this.pagination.page) - 1) * this.pagination.perPage

        // Empty filters are sent as undefined (omitted by axios)
        const response = await geneCatalogueAPI.getCatalogue({
          skip,
          limit: this.pagination.perPage,
          search: this.filters.search || undefined,
          classification: this.filters.classification || undefined,
          disease: this.filters.disease || undefined,
          scope_id: this.filters.scopeId || undefined,
          chromosome: this.filters.chromosome || undefined,
          sort_by: this.filters.sortBy,
          sort_order: this.filters.sortOrder
        })

        this.entries = response.entries || []
        this.pagination.total = response.total || 0
        this.pagination.hasNext = response.has_next || false
        this.pagination.hasPrev = response.has_prev || false

        // Update summary
        if (response.summary) {
          this.summary = {
            totalGenesCurated: response.summary.total_genes_curated || 0,
            totalCurations: response.summary.total_curations || 0,
            totalScopes: response.summary.total_scopes || 0,
            classificationSummary: response.summary.classification_summary || {}
          }
        }

        return response
      } catch (error) {
        this.error = { message: toApiError(error).message || 'Failed to fetch catalogue' }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Load filter options (classifications, diseases, scopes)
     */
    async loadFilterOptions() {
      if (this.filterOptions.loaded) {
        return this.filterOptions
      }

      try {
        const [classifications, diseases, scopes] = await Promise.all([
          geneCatalogueAPI.getAvailableClassifications(),
          geneCatalogueAPI.getAvailableDiseases(),
          geneCatalogueAPI.getAvailableScopes()
        ])

        this.filterOptions = {
          classifications: classifications || [],
          diseases: diseases || [],
          scopes: scopes || [],
          loaded: true
        }

        return this.filterOptions
      } catch (error) {
        this.error = { message: toApiError(error).message || 'Failed to load filter options' }
        throw error
      }
    },

    /**
     * Update filters and refetch
     */
    updateFilters(newFilters: Partial<CatalogueFilters>) {
      this.filters = { ...this.filters, ...newFilters }
      this.pagination.page = 1 // Reset to first page
    },

    /**
     * Clear all filters
     */
    clearFilters() {
      this.filters = { ...DEFAULT_FILTERS }
      this.pagination.page = 1
    },

    /**
     * Set current page
     */
    setPage(page: number) {
      this.pagination.page = page
    },

    /**
     * Toggle gene row expansion
     */
    toggleGeneExpanded(geneId: string) {
      if (this.expandedGeneIds.has(geneId)) {
        this.expandedGeneIds.delete(geneId)
      } else {
        this.expandedGeneIds.add(geneId)
      }
      // Force reactivity update
      this.expandedGeneIds = new Set(this.expandedGeneIds)
    },

    /**
     * Expand gene row
     */
    expandGene(geneId: string) {
      this.expandedGeneIds.add(geneId)
      this.expandedGeneIds = new Set(this.expandedGeneIds)
    },

    /**
     * Collapse gene row
     */
    collapseGene(geneId: string) {
      this.expandedGeneIds.delete(geneId)
      this.expandedGeneIds = new Set(this.expandedGeneIds)
    },

    /**
     * Collapse all expanded rows
     */
    collapseAll() {
      this.expandedGeneIds = new Set()
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
      this.entries = []
      this.loading = false
      this.error = null
      this.pagination = {
        page: 1,
        perPage: 20,
        total: 0,
        hasNext: false,
        hasPrev: false
      }
      this.filters = { ...DEFAULT_FILTERS }
      this.summary = {
        totalGenesCurated: 0,
        totalCurations: 0,
        totalScopes: 0,
        classificationSummary: {}
      }
      this.filterOptions = {
        classifications: [],
        diseases: [],
        scopes: [],
        loaded: false
      }
      this.expandedGeneIds = new Set()
    }
  }
})
