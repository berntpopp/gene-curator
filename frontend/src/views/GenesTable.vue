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
            v-if="authStore.isAuthenticated"
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
      <v-alert v-if="genesStore.error" type="error" variant="tonal">
        {{ genesStore.error }}
        <template #append>
          <v-btn class="retry" variant="text" @click="performSearch">Retry</v-btn>
        </template>
      </v-alert>
      <v-card v-else>
        <v-data-table
          :headers="headers"
          :items="genes"
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

          <!-- Location -->
          <template #item.location="{ item }">
            <div class="d-flex flex-column">
              <span class="font-weight-medium">{{ item.chromosome || '—' }}</span>
              <span class="text-caption text-medium-emphasis">
                {{ item.location || '' }}
              </span>
            </div>
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
                v-if="authStore.isAuthenticated"
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

<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '@/stores/auth'
  import { useGenesStore } from '@/stores/genes'

  const router = useRouter()
  const authStore = useAuthStore()
  const genesStore = useGenesStore()

  // Searching shows the search results; otherwise the paged list
  const genes = computed(() => (isSearching.value ? genesStore.searchResults : genesStore.genes))

  // Search and filter state
  const searchQuery = ref('')
  const selectedChromosome = ref<string | null>(null)
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
      title: 'Location',
      key: 'location',
      sortable: true,
      width: '120px'
    },
    {
      title: 'Actions',
      key: 'actions',
      sortable: false,
      width: '100px',
      align: 'center'
    }
  ] as const

  const sortOptions = [
    { title: 'Gene Symbol (A-Z)', value: 'approved_symbol_asc' },
    { title: 'Gene Symbol (Z-A)', value: 'approved_symbol_desc' },
    { title: 'Chromosome', value: 'chromosome_asc' },
    { title: 'Recently Updated', value: 'updated_at_desc' }
  ]

  // Computed values
  const isSearching = computed(() => {
    return Boolean(searchQuery.value || selectedChromosome.value)
  })

  const uniqueChromosomes = computed(() => {
    const chromosomes = new Set<string>()
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
  let searchTimeout: ReturnType<typeof setTimeout> | undefined
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
    // Option values look like "approved_symbol_asc": the last segment is the order
    const cut = sortBy.value.lastIndexOf('_')
    genesStore.updateSearchParams({
      sort_by: sortBy.value.slice(0, cut),
      sort_order: sortBy.value.slice(cut + 1) as 'asc' | 'desc'
    })
    await performSearch()
  }

  const handlePageChange = async (page: number) => {
    currentPage.value = page
    await loadGenes()
  }

  const handleRowClick = (_event: Event, { item }: { item: { id: string } }) => {
    router.push({ name: 'GeneDetail', params: { id: item.id } })
  }

  const editGene = (gene: { id: string }) => {
    router.push({ name: 'GeneAdmin', query: { edit: gene.id } })
  }

  const clearFilters = () => {
    searchQuery.value = ''
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
          chromosome: selectedChromosome.value,
          page: currentPage.value
        })
      } catch {
        // the store keeps the message in genesStore.error, shown with Retry
      }
    } else {
      await loadGenes()
    }
  }

  const loadGenes = async () => {
    try {
      await genesStore.fetchGenes({ page: currentPage.value })
    } catch {
      // the store keeps the message in genesStore.error, shown with Retry
    }
  }

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
