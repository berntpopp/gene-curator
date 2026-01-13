<template>
  <div>
    <!-- Page Header -->
    <v-container>
      <v-row align="center" justify="space-between" class="mb-4">
        <v-col cols="12" md="8">
          <h1 class="text-h4 mb-2">Gene Catalogue</h1>
          <p class="text-subtitle-1 text-medium-emphasis">
            Browse curated genes across all clinical scopes
          </p>
        </v-col>
        <v-col cols="12" md="4" class="text-md-right">
          <!-- Summary chips -->
          <div class="d-flex flex-wrap justify-end ga-2">
            <v-chip color="primary" variant="tonal">
              <v-icon start size="small">mdi-dna</v-icon>
              {{ catalogueStore.summary.totalGenesCurated }} genes
            </v-chip>
            <v-chip color="secondary" variant="tonal">
              <v-icon start size="small">mdi-clipboard-check</v-icon>
              {{ catalogueStore.summary.totalCurations }} curations
            </v-chip>
            <v-chip color="info" variant="tonal">
              <v-icon start size="small">mdi-folder-multiple</v-icon>
              {{ catalogueStore.summary.totalScopes }} scopes
            </v-chip>
          </div>
        </v-col>
      </v-row>
    </v-container>

    <!-- Search and Filters -->
    <v-container>
      <v-card class="mb-6">
        <v-card-title>
          <v-icon start>mdi-filter</v-icon>
          Search & Filters
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="3">
              <v-text-field
                v-model="searchQuery"
                label="Search genes"
                placeholder="Gene symbol, HGNC ID..."
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                clearable
                @update:model-value="debounceSearch"
              />
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="selectedClassification"
                :items="classificationOptions"
                label="Classification"
                variant="outlined"
                clearable
                @update:model-value="handleFilterChange"
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-combobox
                v-model="selectedDisease"
                :items="catalogueStore.filterOptions.diseases"
                label="Disease"
                variant="outlined"
                clearable
                @update:model-value="handleFilterChange"
              />
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="selectedScope"
                :items="scopeOptions"
                label="Scope"
                variant="outlined"
                clearable
                @update:model-value="handleFilterChange"
              />
            </v-col>
            <v-col cols="12" md="2">
              <v-btn
                color="secondary"
                variant="outlined"
                block
                :disabled="!catalogueStore.hasActiveFilters"
                @click="clearFilters"
              >
                Clear All
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-container>

    <!-- Classification Summary -->
    <v-container v-if="Object.keys(catalogueStore.summary.classificationSummary).length > 0">
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex flex-wrap ga-2">
            <v-chip
              v-for="(count, classification) in catalogueStore.summary.classificationSummary"
              :key="classification"
              :color="getClassificationColor(classification)"
              variant="tonal"
              size="small"
            >
              {{ formatClassification(classification) }}: {{ count }}
            </v-chip>
          </div>
        </v-col>
      </v-row>
    </v-container>

    <!-- Catalogue Table -->
    <v-container>
      <v-card>
        <v-data-table
          :headers="headers"
          :items="catalogueStore.entries"
          :loading="catalogueStore.loading"
          :items-per-page="catalogueStore.pagination.perPage"
          :expanded="expandedItems"
          item-value="gene_id"
          class="catalogue-table"
          show-expand
          @update:expanded="handleExpand"
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

          <!-- Location Column -->
          <template #item.location="{ item }">
            <div class="d-flex flex-column">
              <span class="font-weight-medium">{{ item.chromosome || '-' }}</span>
              <span class="text-caption text-medium-emphasis">
                {{ item.location || '' }}
              </span>
            </div>
          </template>

          <!-- Curations Column -->
          <template #item.total_curations="{ item }">
            <v-chip color="primary" size="small" variant="tonal">
              {{ item.total_curations }} curation{{ item.total_curations !== 1 ? 's' : '' }}
            </v-chip>
            <div class="text-caption text-medium-emphasis mt-1">
              {{ item.scope_count }} scope{{ item.scope_count !== 1 ? 's' : '' }}
            </div>
          </template>

          <!-- Classifications Column -->
          <template #item.classifications="{ item }">
            <div class="d-flex flex-wrap ga-1">
              <v-chip
                v-for="(count, classification) in item.classifications"
                :key="classification"
                :color="getClassificationColor(classification)"
                size="x-small"
                variant="tonal"
              >
                {{ formatClassification(classification) }}
                <span v-if="count > 1" class="ml-1">({{ count }})</span>
              </v-chip>
            </div>
          </template>

          <!-- Diseases Column -->
          <template #item.diseases="{ item }">
            <div v-if="item.diseases.length > 0">
              <v-tooltip v-if="item.diseases.length > 2" location="top">
                <template #activator="{ props }">
                  <span v-bind="props">
                    {{ item.diseases.slice(0, 2).join(', ') }}
                    <span class="text-caption">+{{ item.diseases.length - 2 }} more</span>
                  </span>
                </template>
                <div class="pa-2">
                  <div v-for="disease in item.diseases" :key="disease">
                    {{ disease }}
                  </div>
                </div>
              </v-tooltip>
              <span v-else>{{ item.diseases.join(', ') }}</span>
            </div>
            <span v-else class="text-medium-emphasis">-</span>
          </template>

          <!-- Expanded Row - Per-Scope Curations -->
          <template #expanded-row="{ columns, item }">
            <tr>
              <td :colspan="columns.length" class="pa-0">
                <v-card flat color="grey-lighten-4" class="ma-2">
                  <v-card-title class="text-subtitle-1">
                    <v-icon start size="small">mdi-folder-multiple-outline</v-icon>
                    Curations by Scope
                  </v-card-title>
                  <v-card-text class="pa-0">
                    <v-list density="compact" class="bg-grey-lighten-4">
                      <v-list-item
                        v-for="curation in item.scope_curations"
                        :key="curation.scope_id"
                        class="mb-2"
                      >
                        <template #prepend>
                          <v-icon size="small" color="primary">
                            {{ curation.is_public ? 'mdi-earth' : 'mdi-lock' }}
                          </v-icon>
                        </template>

                        <v-list-item-title class="font-weight-medium">
                          {{ curation.scope_display_name }}
                          <v-chip
                            v-if="curation.classification"
                            :color="getClassificationColor(curation.classification)"
                            size="x-small"
                            variant="tonal"
                            class="ml-2"
                          >
                            {{ formatClassification(curation.classification) }}
                          </v-chip>
                        </v-list-item-title>

                        <v-list-item-subtitle>
                          <div class="d-flex flex-wrap align-center ga-3 mt-1">
                            <!-- Disease -->
                            <span v-if="curation.disease_name">
                              <v-icon size="x-small" class="mr-1">mdi-virus</v-icon>
                              {{ curation.disease_name }}
                              <span
                                v-if="curation.mondo_id"
                                class="text-caption text-medium-emphasis"
                              >
                                ({{ curation.mondo_id }})
                              </span>
                            </span>

                            <!-- Mode of Inheritance -->
                            <span v-if="curation.mode_of_inheritance">
                              <v-icon size="x-small" class="mr-1">mdi-family-tree</v-icon>
                              {{ curation.mode_of_inheritance }}
                            </span>

                            <!-- Score -->
                            <span v-if="curation.total_score !== null">
                              <v-icon size="x-small" class="mr-1">mdi-chart-bar</v-icon>
                              Score: {{ formatScore(curation.total_score) }}
                              <span
                                v-if="curation.genetic_score || curation.experimental_score"
                                class="text-caption text-medium-emphasis"
                              >
                                (G: {{ formatScore(curation.genetic_score) }}, E:
                                {{ formatScore(curation.experimental_score) }})
                              </span>
                            </span>

                            <!-- Curator -->
                            <span v-if="curation.curator_name">
                              <v-icon size="x-small" class="mr-1">mdi-account</v-icon>
                              {{ curation.curator_name }}
                            </span>

                            <!-- Activated date -->
                            <span class="text-caption text-medium-emphasis">
                              <v-icon size="x-small" class="mr-1">mdi-calendar-check</v-icon>
                              {{ formatDate(curation.activated_at) }}
                            </span>
                          </div>
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-list>
                  </v-card-text>
                </v-card>
              </td>
            </tr>
          </template>

          <!-- Loading -->
          <template #loading>
            <v-skeleton-loader type="table-row@10" />
          </template>

          <!-- No data -->
          <template #no-data>
            <div class="text-center py-8">
              <v-icon size="64" class="mb-4 text-medium-emphasis"> mdi-clipboard-search </v-icon>
              <h3 class="text-h6 mb-2">No curated genes found</h3>
              <p class="text-body-2 text-medium-emphasis">
                {{
                  catalogueStore.hasActiveFilters
                    ? 'Try adjusting your search criteria'
                    : 'No genes have active curations yet'
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
            :length="catalogueStore.totalPages"
            :disabled="catalogueStore.loading"
            @update:model-value="handlePageChange"
          />
        </div>
      </v-card>
    </v-container>
  </div>
</template>

<script setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { useGeneCatalogueStore } from '@/stores/geneCatalogue'

  const catalogueStore = useGeneCatalogueStore()

  // Local state for filters
  const searchQuery = ref('')
  const selectedClassification = ref(null)
  const selectedDisease = ref(null)
  const selectedScope = ref(null)
  const currentPage = ref(1)

  // Expanded rows tracking
  const expandedItems = ref([])

  // Table headers
  const headers = [
    { title: '', key: 'data-table-expand', width: '50px' },
    { title: 'Gene', key: 'approved_symbol', sortable: true, width: '180px' },
    { title: 'Location', key: 'location', sortable: true, width: '120px' },
    { title: 'Curations', key: 'total_curations', sortable: true, width: '120px' },
    { title: 'Classifications', key: 'classifications', sortable: false, width: '200px' },
    { title: 'Diseases', key: 'diseases', sortable: false }
  ]

  // Classification options for filter dropdown
  const classificationOptions = computed(() => {
    return catalogueStore.filterOptions.classifications.map(c => ({
      title: formatClassification(c),
      value: c
    }))
  })

  // Scope options for filter dropdown
  const scopeOptions = computed(() => {
    return catalogueStore.filterOptions.scopes.map(s => ({
      title: s.scope_display_name,
      value: s.scope_id
    }))
  })

  // Debounced search
  let searchTimeout = null
  const debounceSearch = () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
      handleFilterChange()
    }, 300)
  }

  // Handle filter changes
  const handleFilterChange = async () => {
    catalogueStore.updateFilters({
      search: searchQuery.value || null,
      classification: selectedClassification.value || null,
      disease: selectedDisease.value || null,
      scopeId: selectedScope.value || null
    })
    currentPage.value = 1
    await catalogueStore.fetchCatalogue({ page: 1 })
  }

  // Handle page change
  const handlePageChange = async page => {
    catalogueStore.setPage(page)
    await catalogueStore.fetchCatalogue({ page })
  }

  // Handle row expansion
  const handleExpand = expanded => {
    expandedItems.value = expanded
  }

  // Clear all filters
  const clearFilters = async () => {
    searchQuery.value = ''
    selectedClassification.value = null
    selectedDisease.value = null
    selectedScope.value = null
    currentPage.value = 1
    catalogueStore.clearFilters()
    await catalogueStore.fetchCatalogue({ page: 1 })
  }

  // Format helpers
  const formatClassification = classification => {
    if (!classification) return 'Unknown'
    // Capitalize first letter
    return classification.charAt(0).toUpperCase() + classification.slice(1).replace(/_/g, ' ')
  }

  const formatScore = score => {
    if (score === null || score === undefined) return '-'
    return typeof score === 'number' ? score.toFixed(1) : score
  }

  const formatDate = dateString => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  // Classification color mapping
  const getClassificationColor = classification => {
    const colorMap = {
      definitive: 'success',
      strong: 'primary',
      moderate: 'warning',
      limited: 'secondary',
      no_known: 'default',
      disputed: 'error',
      refuted: 'error'
    }
    return colorMap[classification?.toLowerCase()] || 'default'
  }

  // Initialize on mount
  onMounted(async () => {
    // Load filter options and initial data in parallel
    await Promise.all([catalogueStore.loadFilterOptions(), catalogueStore.fetchCatalogue()])
  })

  // Watch for page changes from store
  watch(
    () => catalogueStore.pagination.page,
    newPage => {
      currentPage.value = newPage
    }
  )
</script>

<style scoped>
  .catalogue-table :deep(.v-data-table__wrapper) {
    border-radius: 8px;
  }

  .catalogue-table :deep(tbody tr:not(.v-data-table__expanded__content)) {
    cursor: pointer;
  }

  .catalogue-table :deep(tbody tr:hover:not(.v-data-table__expanded__content)) {
    background-color: rgba(var(--v-theme-primary), 0.04);
  }

  .v-chip {
    font-size: 0.75rem;
  }
</style>
