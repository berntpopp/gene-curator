<template>
  <div>
    <!-- Page Header -->
    <v-container>
      <v-row align="center" justify="space-between" class="mb-4">
        <v-col cols="12" md="6">
          <h1 class="text-h4 mb-2">Gene Database</h1>
          <p class="text-subtitle-1 text-medium-emphasis">Browse and search genetic information</p>
        </v-col>
        <v-col cols="12" md="6" class="text-md-right">
          <v-btn
            v-if="authStore.isCurator"
            :to="{ name: 'GeneAdmin' }"
            color="primary"
            prepend-icon="mdi-plus"
          >
            Add Gene
          </v-btn>
        </v-col>
      </v-row>
    </v-container>

    <!-- Search and Filters -->
    <v-container>
      <v-card class="mb-6">
        <v-card-title>
          <v-icon start>mdi-magnify</v-icon>
          Search & Filters
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="searchQuery"
                label="Search genes..."
                placeholder="Gene symbol, HGNC ID, or keywords"
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                clearable
                @input="debounceSearch"
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="selectedFamily"
                :items="uniqueFamilies"
                label="Gene Family"
                variant="outlined"
                clearable
                @update:model-value="handleFilterChange"
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="selectedChromosome"
                :items="uniqueChromosomes"
                label="Chromosome"
                variant="outlined"
                clearable
                @update:model-value="handleFilterChange"
              />
            </v-col>
            <v-col cols="12" md="2">
              <v-btn color="secondary" variant="outlined" block @click="clearFilters">
                Clear All
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-container>

    <!-- Results Summary -->
    <v-container>
      <v-row align="center" class="mb-4">
        <v-col>
          <div class="d-flex align-center">
            <v-chip color="primary" variant="outlined" class="mr-3">
              {{ genesStore.genes.length }} genes
            </v-chip>
            <v-chip
              v-if="isSearching"
              color="info"
              variant="outlined"
              closable
              @click:close="clearFilters"
            >
              Search active
            </v-chip>
          </div>
        </v-col>
        <v-col class="text-right">
          <v-select
            v-model="sortBy"
            :items="sortOptions"
            label="Sort by"
            variant="outlined"
            density="compact"
            style="width: 200px"
            @update:model-value="handleSortChange"
          />
        </v-col>
      </v-row>
    </v-container>

    <!-- Data Table -->
    <v-container>
      <v-card>
        <v-data-table
          :headers="headers"
          :items="genesStore.genes"
          :loading="genesStore.loading"
          :items-per-page="genesStore.pagination.per_page"
          class="gene-table"
          @click:row="handleRowClick"
        >
          <!-- Gene Symbol Column -->
          <template #item.approved_symbol="{ item }">
            <div class="font-weight-bold">
              {{ item.approved_symbol }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ item.hgnc_id }}
            </div>
          </template>

          <!-- Previous/Alias Symbols -->
          <template #item.previous_symbols="{ item }">
            <div v-if="item.previous_symbols && item.previous_symbols.length">
              <v-chip
                v-for="symbol in item.previous_symbols.slice(0, 2)"
                :key="symbol"
                size="x-small"
                variant="outlined"
                class="ma-1"
              >
                {{ symbol }}
              </v-chip>
              <span v-if="item.previous_symbols.length > 2" class="text-caption">
                +{{ item.previous_symbols.length - 2 }} more
              </span>
            </div>
            <span v-else class="text-medium-emphasis">—</span>
          </template>

          <!-- Gene Family -->
          <template #item.gene_family="{ item }">
            <div v-if="item.gene_family && item.gene_family.length">
              <v-chip
                v-for="family in item.gene_family.slice(0, 1)"
                :key="family"
                size="small"
                color="info"
                variant="tonal"
                class="ma-1"
              >
                {{ family }}
              </v-chip>
              <div v-if="item.gene_family.length > 1" class="text-caption">
                +{{ item.gene_family.length - 1 }} more
              </div>
            </div>
            <span v-else class="text-medium-emphasis">—</span>
          </template>

          <!-- Location -->
          <template #item.location="{ item }">
            <div class="d-flex flex-column">
              <span class="font-weight-medium">{{ item.chromosome || '—' }}</span>
              <span class="text-caption text-medium-emphasis">
                {{ item.location || '' }}
              </span>
            </div>
          </template>

          <!-- ClinGen Score -->
          <template #item.clingen_score="{ item }">
            <v-chip
              v-if="item.details?.clingen_score !== undefined"
              :color="getScoreColor(item.details.clingen_score)"
              size="small"
              variant="tonal"
            >
              {{ item.details.clingen_score }}
            </v-chip>
            <span v-else class="text-medium-emphasis">—</span>
          </template>

          <!-- Actions -->
          <template #item.actions="{ item }">
            <div class="d-flex">
              <v-btn
                :to="{ name: 'GeneDetail', params: { id: item.id } }"
                icon="mdi-eye"
                variant="text"
                size="small"
                title="View Details"
              />
              <v-btn
                v-if="authStore.isCurator"
                icon="mdi-pencil"
                variant="text"
                size="small"
                title="Edit Gene"
                @click.stop="editGene(item)"
              />
            </div>
          </template>

          <!-- Loading -->
          <template #loading>
            <v-skeleton-loader type="table-row@10" />
          </template>

          <!-- No data -->
          <template #no-data>
            <div class="text-center py-8">
              <v-icon size="64" class="mb-4 text-medium-emphasis"> mdi-database-search </v-icon>
              <h3 class="text-h6 mb-2">No genes found</h3>
              <p class="text-body-2 text-medium-emphasis">
                {{
                  isSearching
                    ? 'Try adjusting your search criteria'
                    : 'No genes available in the database'
                }}
              </p>
            </div>
          </template>
        </v-data-table>

        <!-- Pagination -->
        <v-divider />
        <div class="d-flex justify-center pa-4">
          <v-pagination
            v-model="currentPage"
            :length="genesStore.pagination.pages"
            :disabled="genesStore.loading"
            @update:model-value="handlePageChange"
          />
        </div>
      </v-card>
    </v-container>
  </div>
</template>

<script setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '@/stores/auth.js'
  import { useGenesStore } from '@/stores/genes.js'
  import { showError } from '@/composables/useNotifications.js'

  const router = useRouter()
  const authStore = useAuthStore()
  const genesStore = useGenesStore()

  // Search and filter state
  const searchQuery = ref('')
  const selectedFamily = ref(null)
  const selectedChromosome = ref(null)
  const sortBy = ref('approved_symbol_asc')
  const currentPage = ref(1)

  // Table configuration
  const headers = [
    {
      title: 'Gene Symbol',
      key: 'approved_symbol',
      sortable: true,
      width: '200px'
    },
    {
      title: 'Previous/Alias',
      key: 'previous_symbols',
      sortable: false,
      width: '180px'
    },
    {
      title: 'Gene Family',
      key: 'gene_family',
      sortable: false,
      width: '160px'
    },
    {
      title: 'Location',
      key: 'location',
      sortable: true,
      width: '120px'
    },
    {
      title: 'ClinGen Score',
      key: 'clingen_score',
      sortable: false,
      width: '120px'
    },
    {
      title: 'Actions',
      key: 'actions',
      sortable: false,
      width: '100px',
      align: 'center'
    }
  ]

  const sortOptions = [
    { title: 'Gene Symbol (A-Z)', value: 'approved_symbol_asc' },
    { title: 'Gene Symbol (Z-A)', value: 'approved_symbol_desc' },
    { title: 'Chromosome', value: 'chromosome_asc' },
    { title: 'Recently Updated', value: 'updated_at_desc' }
  ]

  // Computed values
  const isSearching = computed(() => {
    return searchQuery.value || selectedFamily.value || selectedChromosome.value
  })

  const uniqueFamilies = computed(() => {
    const families = new Set()
    genesStore.genes.forEach(gene => {
      if (gene.gene_family) {
        gene.gene_family.forEach(family => families.add(family))
      }
    })
    return Array.from(families).sort()
  })

  const uniqueChromosomes = computed(() => {
    const chromosomes = new Set()
    genesStore.genes.forEach(gene => {
      if (gene.chromosome) {
        chromosomes.add(gene.chromosome)
      }
    })
    return Array.from(chromosomes).sort((a, b) => {
      // Sort chromosomes numerically, with X and Y at the end
      if (a === 'X') return b === 'Y' ? -1 : 1
      if (a === 'Y') return 1
      if (b === 'X' || b === 'Y') return -1
      return parseInt(a) - parseInt(b)
    })
  })

  // Debounced search
  let searchTimeout = null
  const debounceSearch = () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
      handleFilterChange()
    }, 300)
  }

  // Event handlers
  const handleFilterChange = async () => {
    currentPage.value = 1
    await performSearch()
  }

  const handleSortChange = async () => {
    const [field, order] = sortBy.value.split('_')
    // Update search params instead of calling non-existent method
    genesStore.updateSearchParams({ sort_by: field, sort_order: order })
    await performSearch()
  }

  const handlePageChange = async page => {
    currentPage.value = page
    // Update pagination and fetch new page
    await genesStore.fetchGenes({ page })
  }

  const handleRowClick = (event, { item }) => {
    router.push({ name: 'GeneDetail', params: { id: item.id } })
  }

  const editGene = gene => {
    router.push({ name: 'GeneAdmin', query: { edit: gene.id } })
  }

  const clearFilters = () => {
    searchQuery.value = ''
    selectedFamily.value = null
    selectedChromosome.value = null
    currentPage.value = 1
    genesStore.clearSearchResults()
    loadGenes()
  }

  const performSearch = async () => {
    if (isSearching.value) {
      try {
        await genesStore.searchGenes({
          query: searchQuery.value,
          gene_family: selectedFamily.value,
          chromosome: selectedChromosome.value,
          page: currentPage.value
        })
      } catch (error) {
        showError('Search failed. Please try again.')
      }
    } else {
      await loadGenes()
    }
  }

  const loadGenes = async () => {
    try {
      await genesStore.fetchGenes({
        page: currentPage.value
      })
    } catch (error) {
      showError('Failed to load genes. Please try again.')
    }
  }

  const getScoreColor = score => {
    if (score >= 8) return 'success'
    if (score >= 5) return 'warning'
    if (score >= 2) return 'info'
    return 'error'
  }

  // Watchers
  watch(currentPage, newPage => {
    genesStore.pagination.page = newPage
  })

  // Lifecycle
  onMounted(async () => {
    // Wait for authentication to initialize before loading genes
    if (!authStore.isAuthenticated) {
      // Watch for auth initialization
      const unwatch = watch(
        () => authStore.isAuthenticated,
        async isAuthenticated => {
          if (isAuthenticated) {
            await loadGenes()
            unwatch() // Stop watching once loaded
          }
        },
        { immediate: true }
      )
    } else {
      // Already authenticated, load immediately
      await loadGenes()
    }
  })
</script>

<style scoped>
  .gene-table {
    border-radius: 8px;
  }

  .gene-table :deep(.v-data-table__wrapper) {
    border-radius: 8px;
  }

  .gene-table :deep(tbody tr) {
    cursor: pointer;
  }

  .gene-table :deep(tbody tr:hover) {
    background-color: rgba(var(--v-theme-primary), 0.04);
  }

  .v-chip {
    font-size: 0.75rem;
  }
</style>
