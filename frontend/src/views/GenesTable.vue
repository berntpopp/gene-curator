<template>
  <div>
    <!-- Page Header -->
    <v-container>
      <v-row align="center" justify="space-between" class="mb-4">
        <v-col cols="12" md="6">
          <h1 class="text-h4 mb-2">{{ TERMINOLOGY.GENES }}</h1>
          <p class="text-subtitle-1 text-medium-emphasis">Browse and search genetic information</p>
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
                :items="chromosomes"
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
              {{ totalGenes }} genes
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
        <v-data-table-server
          :headers="headers"
          :items="genes"
          :items-length="totalGenes"
          :loading="genesStore.loading"
          :items-per-page="genesStore.pagination.per_page"
          :page="currentPage"
          class="gene-table"
          @update:options="handleOptions"
        >
          <!-- Gene Symbol Column -->
          <template #item.approved_symbol="{ item }">
            <router-link
              :to="{ name: 'GeneDetail', params: { id: item.id } }"
              class="font-weight-bold"
            >
              {{ item.approved_symbol }}
            </router-link>
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
        </v-data-table-server>
      </v-card>
    </v-container>
  </div>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
  import { ref, computed, onMounted, watch } from 'vue'
  import { useAuthStore } from '@/stores/auth'
  import { useGenesStore } from '@/stores/genes'

  const authStore = useAuthStore()
  const genesStore = useGenesStore()

  // Searching shows the search results; otherwise the paged list
  const genes = computed(() => (isSearching.value ? genesStore.searchResults : genesStore.genes))

  // Search and filter state
  const searchQuery = ref('')
  const selectedChromosome = ref<string | null>(null)
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
      sortable: false,
      width: '120px'
    }
  ] as const

  // Computed values
  const isSearching = computed(() => {
    return Boolean(searchQuery.value || selectedChromosome.value)
  })

  // Static list: deriving it from the current page hid chromosomes
  const chromosomes = [...Array.from({ length: 22 }, (_, i) => String(i + 1)), 'X', 'Y', 'MT']

  const totalGenes = computed(() =>
    isSearching.value ? genesStore.searchTotal : genesStore.pagination.total
  )

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

  // Header sort and paging; fires on mount too, so only act on a real change
  const handleOptions = async (o: { page: number; sortBy: { key: string; order?: unknown }[] }) => {
    const sort = o.sortBy[0]
    const order = sort?.order === 'desc' ? 'desc' : 'asc'
    const sortChanged =
      !!sort &&
      (sort.key !== genesStore.searchParams.sort_by || order !== genesStore.searchParams.sort_order)
    if (sortChanged) genesStore.updateSearchParams({ sort_by: sort.key, sort_order: order })
    if (o.page !== currentPage.value || sortChanged) {
      currentPage.value = o.page
      await performSearch()
    }
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
          page: currentPage.value,
          sort_by: genesStore.searchParams.sort_by,
          sort_order: genesStore.searchParams.sort_order
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

  .gene-table :deep(tbody tr:hover) {
    background-color: rgba(var(--v-theme-primary), 0.04);
  }

  .v-chip {
    font-size: 0.75rem;
  }
</style>
