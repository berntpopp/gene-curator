<template>
  <div>
    <!-- Page Header -->
    <v-container>
      <v-row align="center" justify="space-between" class="mb-4">
        <v-col cols="12" md="6">
          <h1 class="text-h4 mb-2">Gene Catalogue</h1>
          <p class="text-subtitle-1 text-medium-emphasis">
            Browse curated genes across all clinical scopes
          </p>
        </v-col>
        <v-col cols="12" md="6">
          <!-- Summary Stats Cards -->
          <v-row dense>
            <v-col cols="4">
              <v-card variant="tonal" color="primary" class="text-center pa-2">
                <v-icon size="24" class="mb-1">mdi-dna</v-icon>
                <div class="text-h5 font-weight-bold">
                  {{ catalogueStore.summary.totalGenesCurated }}
                </div>
                <div class="text-caption">Curated Genes</div>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card variant="tonal" color="secondary" class="text-center pa-2">
                <v-icon size="24" class="mb-1">mdi-clipboard-check</v-icon>
                <div class="text-h5 font-weight-bold">
                  {{ catalogueStore.summary.totalCurations }}
                </div>
                <div class="text-caption">Active Curations</div>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card variant="tonal" color="info" class="text-center pa-2">
                <v-icon size="24" class="mb-1">mdi-folder-multiple</v-icon>
                <div class="text-h5 font-weight-bold">
                  {{ catalogueStore.summary.totalScopes }}
                </div>
                <div class="text-caption">Clinical Scopes</div>
              </v-card>
            </v-col>
          </v-row>
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
            <div class="d-flex align-center">
              <v-avatar size="32" color="primary" variant="tonal" class="mr-2">
                <v-icon size="small">mdi-dna</v-icon>
              </v-avatar>
              <div>
                <div class="font-weight-bold">{{ item.approved_symbol }}</div>
                <div class="text-caption text-medium-emphasis">{{ item.hgnc_id }}</div>
              </div>
            </div>
          </template>

          <!-- Location Column -->
          <template #item.location="{ item }">
            <div v-if="item.chromosome" class="d-flex align-center">
              <v-icon size="x-small" color="info" class="mr-1">mdi-map-marker</v-icon>
              <div>
                <span class="font-weight-medium">{{ item.chromosome }}</span>
                <div v-if="item.location" class="text-caption text-medium-emphasis">
                  {{ item.location }}
                </div>
              </div>
            </div>
            <span v-else class="text-medium-emphasis">
              <v-icon size="x-small" class="mr-1">mdi-help-circle-outline</v-icon>
              Unknown
            </span>
          </template>

          <!-- Best Score Column -->
          <template #item.best_score="{ item }">
            <div v-if="getBestScore(item)" class="text-center">
              <div class="text-h6 font-weight-bold" :class="getScoreColorClass(getBestScore(item))">
                {{ formatScore(getBestScore(item)) }}
              </div>
              <div class="text-caption text-medium-emphasis">points</div>
            </div>
            <div v-else class="text-center text-medium-emphasis">
              <v-icon size="small">mdi-minus</v-icon>
            </div>
          </template>

          <!-- Classifications Column -->
          <template #item.classifications="{ item }">
            <div v-if="Object.keys(item.classifications || {}).length > 0">
              <v-chip
                v-if="getBestClassification(item)"
                :color="getClassificationColor(getBestClassification(item))"
                size="small"
                variant="tonal"
              >
                <v-icon start size="x-small">{{
                  getClassificationIcon(getBestClassification(item))
                }}</v-icon>
                {{ formatClassification(getBestClassification(item)) }}
              </v-chip>
              <div
                v-if="Object.keys(item.classifications).length > 1"
                class="text-caption text-medium-emphasis mt-1"
              >
                +{{ Object.keys(item.classifications).length - 1 }} more
              </div>
            </div>
            <span v-else class="text-medium-emphasis">
              <v-icon size="x-small">mdi-help-circle-outline</v-icon>
              Pending
            </span>
          </template>

          <!-- Scopes Column -->
          <template #item.total_curations="{ item }">
            <div class="text-center">
              <v-chip color="info" size="small" variant="tonal">
                <v-icon start size="x-small">mdi-folder-multiple</v-icon>
                {{ item.scope_count }}
              </v-chip>
              <div class="text-caption text-medium-emphasis mt-1">
                {{ item.total_curations }} curation{{ item.total_curations !== 1 ? 's' : '' }}
              </div>
            </div>
          </template>

          <!-- Diseases Column -->
          <template #item.diseases="{ item }">
            <div v-if="item.diseases.length > 0">
              <v-tooltip v-if="item.diseases.length > 1" location="top">
                <template #activator="{ props }">
                  <div v-bind="props" class="disease-cell">
                    <v-icon size="x-small" color="warning" class="mr-1">mdi-virus</v-icon>
                    <span class="text-truncate">{{ item.diseases[0] }}</span>
                    <v-chip v-if="item.diseases.length > 1" size="x-small" class="ml-1">
                      +{{ item.diseases.length - 1 }}
                    </v-chip>
                  </div>
                </template>
                <div class="pa-2">
                  <div v-for="disease in item.diseases" :key="disease" class="mb-1">
                    <v-icon size="x-small" class="mr-1">mdi-chevron-right</v-icon>
                    {{ disease }}
                  </div>
                </div>
              </v-tooltip>
              <div v-else class="d-flex align-center">
                <v-icon size="x-small" color="warning" class="mr-1">mdi-virus</v-icon>
                <span class="text-truncate">{{ item.diseases[0] }}</span>
              </div>
            </div>
            <span v-else class="text-medium-emphasis d-flex align-center">
              <v-icon size="x-small" class="mr-1">mdi-help-circle-outline</v-icon>
              No disease
            </span>
          </template>

          <!-- Actions Column -->
          <template #item.actions="{ item }">
            <div class="d-flex justify-center ga-1">
              <v-btn
                icon
                size="x-small"
                variant="text"
                color="primary"
                @click.stop="showQuickInfo(item)"
              >
                <v-icon size="small">mdi-eye</v-icon>
                <v-tooltip activator="parent" location="top">Quick View</v-tooltip>
              </v-btn>
              <v-btn
                icon
                size="x-small"
                variant="text"
                color="info"
                @click.stop="navigateToGene(item)"
              >
                <v-icon size="small">mdi-open-in-new</v-icon>
                <v-tooltip activator="parent" location="top">Gene Details</v-tooltip>
              </v-btn>
            </div>
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

    <!-- Quick Info Dialog -->
    <v-dialog v-model="quickInfoDialog" max-width="700px">
      <v-card v-if="selectedGene">
        <v-card-title class="d-flex align-center">
          <v-avatar size="40" color="primary" variant="tonal" class="mr-3">
            <v-icon>mdi-dna</v-icon>
          </v-avatar>
          <div>
            <span class="text-h5">{{ selectedGene.approved_symbol }}</span>
            <div class="text-caption text-medium-emphasis">{{ selectedGene.hgnc_id }}</div>
          </div>
          <v-spacer />
          <v-btn icon variant="text" @click="quickInfoDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4">
          <!-- Gene Info Summary -->
          <v-row class="mb-4">
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Location</div>
              <div class="font-weight-medium">
                {{ selectedGene.chromosome || 'Unknown' }}
                <span v-if="selectedGene.location" class="text-caption">
                  ({{ selectedGene.location }})
                </span>
              </div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Curations</div>
              <div class="font-weight-medium">{{ selectedGene.total_curations }}</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Scopes</div>
              <div class="font-weight-medium">{{ selectedGene.scope_count }}</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Best Score</div>
              <div class="font-weight-bold" :class="getScoreColorClass(getBestScore(selectedGene))">
                {{ formatScore(getBestScore(selectedGene)) || '-' }}
              </div>
            </v-col>
          </v-row>

          <!-- Scope Curations List -->
          <div class="text-subtitle-2 mb-2">
            <v-icon start size="small">mdi-folder-multiple-outline</v-icon>
            Curations by Scope
          </div>

          <v-list density="compact" class="rounded border">
            <v-list-item
              v-for="curation in selectedGene.scope_curations"
              :key="curation.scope_id"
              :class="{ 'border-b': true }"
            >
              <template #prepend>
                <v-avatar
                  size="32"
                  :color="getClassificationColor(curation.classification)"
                  variant="tonal"
                >
                  <v-icon size="small">
                    {{ curation.is_public ? 'mdi-earth' : 'mdi-lock' }}
                  </v-icon>
                </v-avatar>
              </template>

              <v-list-item-title class="d-flex align-center flex-wrap ga-2">
                <span class="font-weight-medium">{{ curation.scope_display_name }}</span>
                <v-chip
                  v-if="curation.classification"
                  :color="getClassificationColor(curation.classification)"
                  size="x-small"
                  variant="tonal"
                >
                  <v-icon start size="x-small">{{
                    getClassificationIcon(curation.classification)
                  }}</v-icon>
                  {{ formatClassification(curation.classification) }}
                </v-chip>
              </v-list-item-title>

              <v-list-item-subtitle class="mt-1">
                <div class="d-flex flex-wrap ga-4 text-caption">
                  <!-- Score -->
                  <span v-if="curation.total_score !== null" class="d-flex align-center">
                    <v-icon size="x-small" class="mr-1" color="primary">mdi-chart-bar</v-icon>
                    <strong>{{ formatScore(curation.total_score) }}</strong>
                    <span class="text-medium-emphasis ml-1">
                      (G: {{ formatScore(curation.genetic_score) }}, E:
                      {{ formatScore(curation.experimental_score) }})
                    </span>
                  </span>

                  <!-- Disease -->
                  <span v-if="curation.disease_name" class="d-flex align-center">
                    <v-icon size="x-small" class="mr-1" color="warning">mdi-virus</v-icon>
                    {{ curation.disease_name }}
                  </span>

                  <!-- MOI -->
                  <span v-if="curation.mode_of_inheritance" class="d-flex align-center">
                    <v-icon size="x-small" class="mr-1" color="info">mdi-family-tree</v-icon>
                    {{ curation.mode_of_inheritance }}
                  </span>

                  <!-- Date -->
                  <span class="d-flex align-center text-medium-emphasis">
                    <v-icon size="x-small" class="mr-1">mdi-calendar</v-icon>
                    {{ formatDate(curation.activated_at) }}
                  </span>
                </div>
              </v-list-item-subtitle>

              <template #append>
                <v-btn
                  icon
                  size="x-small"
                  variant="text"
                  color="primary"
                  @click="navigateToScope(curation)"
                >
                  <v-icon size="small">mdi-arrow-right</v-icon>
                  <v-tooltip activator="parent" location="left">View Scope</v-tooltip>
                </v-btn>
              </template>
            </v-list-item>
          </v-list>

          <!-- Diseases Summary -->
          <div v-if="selectedGene.diseases.length > 0" class="mt-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon start size="small">mdi-virus</v-icon>
              Associated Diseases ({{ selectedGene.diseases.length }})
            </div>
            <div class="d-flex flex-wrap ga-1">
              <v-chip
                v-for="disease in selectedGene.diseases"
                :key="disease"
                size="small"
                variant="outlined"
                color="warning"
              >
                {{ disease }}
              </v-chip>
            </div>
          </div>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="quickInfoDialog = false">Close</v-btn>
          <v-btn color="primary" variant="elevated" @click="navigateToGene(selectedGene)">
            <v-icon start>mdi-open-in-new</v-icon>
            View Gene Details
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { useGeneCatalogueStore } from '@/stores/geneCatalogue'

  const catalogueStore = useGeneCatalogueStore()
  const router = useRouter()

  // Local state for filters
  const searchQuery = ref('')
  const selectedClassification = ref(null)
  const selectedDisease = ref(null)
  const selectedScope = ref(null)
  const currentPage = ref(1)

  // Expanded rows tracking
  const expandedItems = ref([])

  // Quick info dialog
  const quickInfoDialog = ref(false)
  const selectedGene = ref(null)

  // Table headers
  const headers = [
    { title: '', key: 'data-table-expand', width: '40px' },
    { title: 'Gene', key: 'approved_symbol', sortable: true, width: '160px' },
    { title: 'Location', key: 'location', sortable: true, width: '100px' },
    { title: 'Best Score', key: 'best_score', sortable: false, width: '100px' },
    { title: 'Classification', key: 'classifications', sortable: false, width: '160px' },
    { title: 'Scopes', key: 'total_curations', sortable: true, width: '90px' },
    { title: 'Diseases', key: 'diseases', sortable: false, width: '180px' },
    { title: 'Actions', key: 'actions', sortable: false, width: '100px', align: 'center' }
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

  // Get best (highest) score from all scope curations
  const getBestScore = item => {
    if (!item.scope_curations || item.scope_curations.length === 0) return null
    const scores = item.scope_curations
      .map(c => c.total_score)
      .filter(s => s !== null && s !== undefined)
    if (scores.length === 0) return null
    return Math.max(...scores)
  }

  // Get best (highest priority) classification
  const getBestClassification = item => {
    const priorityOrder = [
      'definitive',
      'strong',
      'moderate',
      'limited',
      'no_known',
      'disputed',
      'refuted'
    ]
    const classifications = Object.keys(item.classifications || {})
    if (classifications.length === 0) return null

    // Sort by priority and return the best one
    classifications.sort((a, b) => {
      const aIndex = priorityOrder.indexOf(a.toLowerCase())
      const bIndex = priorityOrder.indexOf(b.toLowerCase())
      return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex)
    })
    return classifications[0]
  }

  // Get score color class based on value
  const getScoreColorClass = score => {
    if (score === null || score === undefined) return 'text-medium-emphasis'
    if (score >= 12) return 'text-success'
    if (score >= 9) return 'text-primary'
    if (score >= 6) return 'text-warning'
    return 'text-secondary'
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

  // Classification icon mapping
  const getClassificationIcon = classification => {
    const iconMap = {
      definitive: 'mdi-check-circle',
      strong: 'mdi-check-circle-outline',
      moderate: 'mdi-alert-circle',
      limited: 'mdi-help-circle',
      no_known: 'mdi-minus-circle',
      disputed: 'mdi-alert-triangle',
      refuted: 'mdi-close-circle'
    }
    return iconMap[classification?.toLowerCase()] || 'mdi-help-circle-outline'
  }

  // Show quick info dialog
  const showQuickInfo = item => {
    selectedGene.value = item
    quickInfoDialog.value = true
  }

  // Navigation helpers
  const navigateToGene = item => {
    router.push({ name: 'GeneDetail', params: { id: item.gene_id } })
  }

  const navigateToScope = curation => {
    router.push({ name: 'ScopeDashboard', params: { scopeId: curation.scope_id } })
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

  .disease-cell {
    display: flex;
    align-items: center;
    max-width: 160px;
  }

  .disease-cell .text-truncate {
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .border {
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .border-b:not(:last-child) {
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .ga-1 {
    gap: 4px;
  }

  .ga-2 {
    gap: 8px;
  }

  .ga-4 {
    gap: 16px;
  }
</style>
