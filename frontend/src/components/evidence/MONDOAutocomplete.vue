<template>
  <v-autocomplete
    v-model="selectedId"
    v-model:search="searchQuery"
    :items="searchResults"
    :loading="isSearching"
    :label="label"
    :hint="hint"
    :error-messages="errorMessages"
    :required="required"
    :disabled="disabled"
    :clearable="clearable"
    item-title="displayText"
    item-value="mondo_id"
    variant="outlined"
    :prepend-inner-icon="prependIcon"
    no-filter
    return-object
    @update:search="handleSearch"
    @update:model-value="handleSelect"
  >
    <template #item="{ item, props: itemProps }">
      <v-list-item
        v-bind="itemProps"
        :subtitle="item.raw.definition || 'No definition available'"
        class="py-2"
      >
        <template #prepend>
          <v-icon color="primary" size="small">mdi-medical-bag</v-icon>
        </template>
        <template #title>
          <div class="d-flex align-center">
            <span class="font-weight-medium">{{ item.raw.label }}</span>
            <v-chip size="x-small" color="info" variant="tonal" class="ml-2">
              {{ item.raw.mondo_id }}
            </v-chip>
          </div>
        </template>
        <template #append>
          <div v-if="item.raw.xrefs && item.raw.xrefs.length > 0" class="d-flex ga-1">
            <v-chip
              v-for="xref in item.raw.xrefs.slice(0, 2)"
              :key="xref"
              size="x-small"
              variant="outlined"
            >
              {{ xref }}
            </v-chip>
          </div>
        </template>
      </v-list-item>
    </template>

    <template #selection="{ item }">
      <v-chip color="primary" variant="tonal" size="small">
        <v-icon start size="small">mdi-database</v-icon>
        {{ item.raw.mondo_id }}
      </v-chip>
      <span class="ml-2">{{ item.raw.label }}</span>
    </template>

    <template #no-data>
      <v-list-item v-if="searchQuery && searchQuery.length >= minSearchLength">
        <v-list-item-title>
          <span v-if="isSearching">Searching MONDO...</span>
          <span v-else>No diseases found for "{{ searchQuery }}"</span>
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-else>
        <v-list-item-title class="text-medium-emphasis">
          Type at least {{ minSearchLength }} characters to search
        </v-list-item-title>
      </v-list-item>
    </template>

    <template #append-inner>
      <v-tooltip v-if="selectedItem" location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            icon="mdi-information"
            variant="text"
            size="small"
            density="compact"
          />
        </template>
        <div class="text-caption" style="max-width: 400px">
          <strong>{{ selectedItem.label }}</strong>
          <div class="mt-1">{{ selectedItem.definition || 'No definition' }}</div>
          <div v-if="selectedItem.synonyms?.length" class="mt-1">
            <strong>Synonyms:</strong> {{ selectedItem.synonyms.join(', ') }}
          </div>
        </div>
      </v-tooltip>
    </template>
  </v-autocomplete>
</template>

<script setup>
  /**
   * MONDOAutocomplete Component
   *
   * Searchable autocomplete for selecting MONDO (Monarch Disease Ontology) terms.
   * Uses the ontology API to search for diseases by name or ID.
   *
   * @example
   * <mondo-autocomplete
   *   v-model="formData.mondo_id"
   *   v-model:disease-name="formData.disease_name"
   *   label="MONDO Disease"
   *   @select="handleDiseaseSelect"
   * />
   */

  import { ref, computed, watch } from 'vue'
  import { ontologyAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { useDebounceFn } from '@vueuse/core'

  const props = defineProps({
    modelValue: {
      type: String,
      default: ''
    },
    diseaseName: {
      type: String,
      default: ''
    },
    label: {
      type: String,
      default: 'MONDO Disease'
    },
    hint: {
      type: String,
      default: 'Search by disease name or MONDO ID'
    },
    required: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    },
    clearable: {
      type: Boolean,
      default: true
    },
    prependIcon: {
      type: String,
      default: 'mdi-database'
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

  const emit = defineEmits(['update:modelValue', 'update:diseaseName', 'select'])

  const logger = useLogger()

  // State
  const searchQuery = ref('')
  const searchResults = ref([])
  const isSearching = ref(false)
  const selectedItem = ref(null)
  const error = ref(null)

  // Selected ID for v-autocomplete
  const selectedId = computed({
    get: () => {
      if (selectedItem.value) return selectedItem.value
      if (props.modelValue) {
        // If we have a modelValue but no selected item, create a placeholder
        return {
          mondo_id: props.modelValue,
          label: props.diseaseName || props.modelValue,
          displayText: `${props.diseaseName || 'Unknown'} (${props.modelValue})`
        }
      }
      return null
    },
    set: val => {
      selectedItem.value = val
    }
  })

  /**
   * Perform search against MONDO API
   */
  async function performSearch(query) {
    if (!query || query.length < props.minSearchLength) {
      searchResults.value = []
      return
    }

    isSearching.value = true
    error.value = null

    try {
      const response = await ontologyAPI.searchMONDO(query, props.maxResults)

      // Map results with display text
      searchResults.value = response.results.map(r => ({
        ...r,
        displayText: `${r.label} (${r.mondo_id})`
      }))

      logger.debug('MONDO search complete', {
        query,
        results: response.results.length,
        total: response.total_results
      })
    } catch (e) {
      error.value = 'Search failed'
      logger.error('MONDO search error', { query, error: e.message })
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }

  // Debounced search to avoid excessive API calls
  const debouncedSearch = useDebounceFn(performSearch, 300)

  /**
   * Handle search input change
   */
  function handleSearch(query) {
    if (query && query !== selectedItem.value?.label) {
      debouncedSearch(query)
    }
  }

  /**
   * Handle item selection
   */
  function handleSelect(item) {
    if (item) {
      selectedItem.value = item
      emit('update:modelValue', item.mondo_id)
      emit('update:diseaseName', item.label)
      emit('select', item)
      logger.info('MONDO term selected', { mondo_id: item.mondo_id, label: item.label })
    } else {
      selectedItem.value = null
      emit('update:modelValue', '')
      emit('update:diseaseName', '')
      emit('select', null)
    }
  }

  // Watch for external modelValue changes
  watch(
    () => props.modelValue,
    async newValue => {
      if (newValue && (!selectedItem.value || selectedItem.value.mondo_id !== newValue)) {
        // Try to find the term by searching
        try {
          const response = await ontologyAPI.searchMONDO(newValue, 1)
          if (response.results.length > 0) {
            const found = response.results[0]
            selectedItem.value = {
              ...found,
              displayText: `${found.label} (${found.mondo_id})`
            }
          }
        } catch {
          // Silently fail - user can still use the component
        }
      }
    },
    { immediate: true }
  )

  // Error messages for form validation
  const errorMessages = computed(() => {
    if (error.value) return [error.value]
    if (props.required && !props.modelValue) {
      return ['MONDO disease is required']
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
