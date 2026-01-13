<template>
  <v-autocomplete
    v-model="selectedItems"
    v-model:search="searchQuery"
    :items="searchResults"
    :loading="isSearching"
    :label="label"
    :hint="hint"
    :error-messages="errorMessages"
    :required="required"
    :disabled="disabled"
    :multiple="multiple"
    :clearable="clearable"
    item-title="displayText"
    item-value="omim_id"
    variant="outlined"
    :prepend-inner-icon="prependIcon"
    no-filter
    return-object
    chips
    closable-chips
    @update:search="handleSearch"
    @update:model-value="handleSelect"
  >
    <template #item="{ item, props: itemProps }">
      <v-list-item v-bind="itemProps" class="py-2">
        <template #prepend>
          <v-icon color="warning" size="small">mdi-flask</v-icon>
        </template>
        <template #title>
          <div class="d-flex align-center">
            <span class="font-weight-medium">{{ item.raw.name }}</span>
          </div>
        </template>
        <template #subtitle>
          <div class="d-flex align-center ga-2 mt-1">
            <v-chip size="x-small" color="warning" variant="tonal">
              {{ item.raw.omim_id }}
            </v-chip>
            <v-chip v-if="item.raw.mondo_id" size="x-small" color="info" variant="outlined">
              {{ item.raw.mondo_id }}
            </v-chip>
            <span v-if="item.raw.gene_symbols?.length" class="text-caption">
              Genes: {{ item.raw.gene_symbols.join(', ') }}
            </span>
          </div>
        </template>
        <template #append>
          <v-btn
            icon="mdi-information"
            variant="text"
            size="x-small"
            @click.stop="loadOMIMDetails(item.raw.omim_id)"
          />
        </template>
      </v-list-item>
    </template>

    <template #chip="{ item, props: chipProps }">
      <v-chip v-bind="chipProps" color="warning" variant="tonal" size="small">
        <v-icon start size="small">mdi-flask</v-icon>
        {{ item.raw.omim_id }}
        <v-tooltip v-if="item.raw.name" location="top" activator="parent">
          <div class="text-caption" style="max-width: 400px">
            <strong>{{ item.raw.name }}</strong>
            <div v-if="item.raw.mondo_id" class="mt-1">MONDO: {{ item.raw.mondo_id }}</div>
            <div v-if="item.raw.gene_symbols?.length" class="mt-1">
              Genes: {{ item.raw.gene_symbols.join(', ') }}
            </div>
          </div>
        </v-tooltip>
      </v-chip>
    </template>

    <template #no-data>
      <v-list-item v-if="searchQuery && searchQuery.length >= minSearchLength">
        <v-list-item-title>
          <span v-if="isSearching">Searching OMIM...</span>
          <span v-else>No OMIM diseases found for "{{ searchQuery }}"</span>
        </v-list-item-title>
        <v-list-item-subtitle>
          Try searching by OMIM number (e.g., 300855) or disease name
        </v-list-item-subtitle>
      </v-list-item>
      <v-list-item v-else>
        <v-list-item-title class="text-medium-emphasis">
          Type at least {{ minSearchLength }} characters to search
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-autocomplete>

  <!-- Detail Dialog -->
  <v-dialog v-model="showDetailDialog" max-width="700">
    <v-card v-if="detailDisease" :loading="isLoadingDetails">
      <v-card-title class="d-flex align-center">
        <v-icon start color="warning">mdi-flask</v-icon>
        {{ detailDisease.name }}
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="showDetailDialog = false" />
      </v-card-title>

      <v-card-subtitle>
        <v-chip size="small" color="warning" variant="tonal" class="mr-2">
          {{ detailDisease.omim_id }}
        </v-chip>
        <v-chip v-if="detailDisease.mondo_id" size="small" color="info" variant="outlined">
          {{ detailDisease.mondo_id }}
        </v-chip>
      </v-card-subtitle>

      <v-card-text>
        <div v-if="detailDisease.description" class="mb-4">
          <strong>Description:</strong>
          <p class="text-body-2 mt-1">{{ detailDisease.description }}</p>
        </div>

        <div v-if="detailDisease.genes?.length" class="mb-4">
          <strong>Associated Genes:</strong>
          <div class="d-flex flex-wrap ga-1 mt-1">
            <v-chip
              v-for="gene in detailDisease.genes"
              :key="gene.gene_id"
              size="small"
              color="primary"
              variant="tonal"
            >
              {{ gene.symbol }}
            </v-chip>
          </div>
        </div>

        <div v-if="Object.keys(detailDisease.phenotypes || {}).length">
          <strong>Phenotypes by Category:</strong>
          <v-expansion-panels class="mt-2" variant="accordion">
            <v-expansion-panel
              v-for="(phenos, category) in detailDisease.phenotypes"
              :key="category"
            >
              <v-expansion-panel-title>
                {{ category }}
                <v-chip size="x-small" class="ml-2">{{ phenos.length }}</v-chip>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-list density="compact">
                  <v-list-item v-for="pheno in phenos" :key="pheno.hpo_id" class="px-0">
                    <template #prepend>
                      <v-chip size="x-small" color="success" variant="tonal">
                        {{ pheno.hpo_id }}
                      </v-chip>
                    </template>
                    <v-list-item-title>{{ pheno.name }}</v-list-item-title>
                    <template #append>
                      <span v-if="pheno.frequency" class="text-caption">
                        {{ pheno.frequency }}
                      </span>
                    </template>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn
          color="warning"
          variant="text"
          :href="`https://omim.org/entry/${detailDisease.omim_id.replace('OMIM:', '')}`"
          target="_blank"
        >
          <v-icon start>mdi-open-in-new</v-icon>
          View on OMIM
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="showDetailDialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  /**
   * OMIMAutocomplete Component
   *
   * Searchable autocomplete for selecting OMIM (Online Mendelian Inheritance in Man) diseases.
   * Uses the ontology API to search for diseases by name or OMIM number.
   * Supports single or multiple selection.
   *
   * @example
   * <omim-autocomplete
   *   v-model="formData.included_mim_phenotypes"
   *   label="Included OMIM Phenotypes"
   *   multiple
   *   @select="handleOMIMSelect"
   * />
   */

  import { ref, computed, watch } from 'vue'
  import { ontologyAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { useDebounceFn } from '@vueuse/core'

  const props = defineProps({
    modelValue: {
      type: [String, Array],
      default: () => []
    },
    label: {
      type: String,
      default: 'OMIM Disease'
    },
    hint: {
      type: String,
      default: 'Search by disease name or OMIM number'
    },
    required: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    },
    multiple: {
      type: Boolean,
      default: false
    },
    clearable: {
      type: Boolean,
      default: true
    },
    prependIcon: {
      type: String,
      default: 'mdi-flask'
    },
    minSearchLength: {
      type: Number,
      default: 2
    },
    maxResults: {
      type: Number,
      default: 15
    }
  })

  const emit = defineEmits(['update:modelValue', 'select'])

  const logger = useLogger()

  // State
  const searchQuery = ref('')
  const searchResults = ref([])
  const isSearching = ref(false)
  const error = ref(null)
  const selectedItems = ref(props.multiple ? [] : null)

  // Detail dialog state
  const showDetailDialog = ref(false)
  const detailDisease = ref(null)
  const isLoadingDetails = ref(false)

  /**
   * Perform search against OMIM API
   */
  async function performSearch(query) {
    if (!query || query.length < props.minSearchLength) {
      searchResults.value = []
      return
    }

    isSearching.value = true
    error.value = null

    try {
      const response = await ontologyAPI.searchOMIM(query, props.maxResults)

      // Map results with display text
      searchResults.value = response.results.map(r => ({
        ...r,
        displayText: `${r.name} (${r.omim_id})`
      }))

      logger.debug('OMIM search complete', {
        query,
        results: response.results.length,
        total: response.total_results
      })
    } catch (e) {
      error.value = 'Search failed'
      logger.error('OMIM search error', { query, error: e.message })
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }

  // Debounced search
  const debouncedSearch = useDebounceFn(performSearch, 300)

  /**
   * Handle search input change
   */
  function handleSearch(query) {
    if (query) {
      debouncedSearch(query)
    }
  }

  /**
   * Handle item selection
   */
  function handleSelect(items) {
    if (props.multiple) {
      const omimIds = items ? items.map(i => i.omim_id) : []
      emit('update:modelValue', omimIds)
      emit('select', items)
      logger.info('OMIM terms selected', { count: omimIds.length })
    } else {
      const item = items
      emit('update:modelValue', item ? item.omim_id : '')
      emit('select', item)
      if (item) {
        logger.info('OMIM term selected', { omim_id: item.omim_id, name: item.name })
      }
    }
  }

  /**
   * Load full OMIM disease details
   */
  async function loadOMIMDetails(omimId) {
    showDetailDialog.value = true
    isLoadingDetails.value = true

    try {
      detailDisease.value = await ontologyAPI.getOMIMDisease(omimId)
      logger.debug('OMIM details loaded', { omim_id: omimId })
    } catch (e) {
      logger.error('Failed to load OMIM details', { omim_id: omimId, error: e.message })
      detailDisease.value = { omim_id: omimId, name: 'Failed to load', error: e.message }
    } finally {
      isLoadingDetails.value = false
    }
  }

  // Watch for external modelValue changes
  watch(
    () => props.modelValue,
    async newValue => {
      if (props.multiple) {
        if (Array.isArray(newValue) && newValue.length > 0) {
          // Load details for each OMIM ID
          const items = []
          for (const omimId of newValue) {
            if (!selectedItems.value?.find(i => i.omim_id === omimId)) {
              try {
                const response = await ontologyAPI.searchOMIM(omimId, 1)
                if (response.results.length > 0) {
                  items.push({
                    ...response.results[0],
                    displayText: `${response.results[0].name} (${response.results[0].omim_id})`
                  })
                } else {
                  // Use placeholder if not found
                  items.push({
                    omim_id: omimId,
                    name: omimId,
                    displayText: omimId
                  })
                }
              } catch {
                items.push({ omim_id: omimId, name: omimId, displayText: omimId })
              }
            }
          }
          if (items.length > 0) {
            selectedItems.value = [...(selectedItems.value || []), ...items]
          }
        }
      } else {
        if (newValue && (!selectedItems.value || selectedItems.value.omim_id !== newValue)) {
          try {
            const response = await ontologyAPI.searchOMIM(newValue, 1)
            if (response.results.length > 0) {
              selectedItems.value = {
                ...response.results[0],
                displayText: `${response.results[0].name} (${response.results[0].omim_id})`
              }
            }
          } catch {
            // Silently fail
          }
        }
      }
    },
    { immediate: true }
  )

  // Error messages for form validation
  const errorMessages = computed(() => {
    if (error.value) return [error.value]
    if (props.required) {
      if (props.multiple && (!props.modelValue || props.modelValue.length === 0)) {
        return ['At least one OMIM disease is required']
      }
      if (!props.multiple && !props.modelValue) {
        return ['OMIM disease is required']
      }
    }
    return []
  })
</script>

<style scoped>
  /* Ensure proper chip styling */
  :deep(.v-chip) {
    font-family: 'Roboto Mono', monospace;
  }
</style>
