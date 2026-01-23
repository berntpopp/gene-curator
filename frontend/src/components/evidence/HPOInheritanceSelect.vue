<template>
  <v-select
    v-model="selectedValue"
    :items="inheritanceItems"
    :loading="isLoading"
    :label="label"
    :hint="hint"
    :error-messages="errorMessages"
    :required="required"
    :disabled="disabled"
    :clearable="clearable"
    item-title="displayText"
    item-value="hpo_id"
    variant="outlined"
    :prepend-inner-icon="prependIcon"
    return-object
    @update:model-value="handleSelect"
  >
    <template #item="{ item, props: itemProps }">
      <v-list-subheader v-if="item.raw.isHeader">
        {{ item.raw.displayText }}
      </v-list-subheader>
      <v-list-item v-else v-bind="itemProps" :subtitle="item.raw.definition" class="py-2">
        <template #prepend>
          <v-icon :color="item.raw.category === 'mendelian' ? 'primary' : 'secondary'" size="small">
            mdi-family-tree
          </v-icon>
        </template>
        <template #title>
          <div class="d-flex align-center">
            <span class="font-weight-medium">{{ item.raw.name }}</span>
            <v-chip
              v-if="item.raw.shortcode"
              size="x-small"
              color="info"
              variant="tonal"
              class="ml-2"
            >
              {{ item.raw.shortcode }}
            </v-chip>
          </div>
        </template>
        <template #append>
          <v-chip size="x-small" variant="outlined">
            {{ item.raw.hpo_id }}
          </v-chip>
        </template>
      </v-list-item>
    </template>

    <template #selection="{ item }">
      <v-chip v-if="item.raw.shortcode" color="primary" variant="tonal" size="small">
        {{ item.raw.shortcode }}
      </v-chip>
      <span class="ml-2">{{ item.raw.name }}</span>
    </template>

    <template #no-data>
      <v-list-item v-if="isLoading">
        <v-list-item-title>
          <v-progress-circular size="16" width="2" indeterminate class="mr-2" />
          Loading inheritance patterns...
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-else-if="loadError">
        <v-list-item-title class="text-error">
          Failed to load inheritance patterns
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-select>
</template>

<script setup>
  /**
   * HPOInheritanceSelect Component
   *
   * Dropdown for selecting HPO inheritance patterns.
   * Fetches patterns from the ontology API and displays them categorized
   * as Mendelian and Non-Mendelian.
   *
   * @example
   * <HPOInheritanceSelect
   *   v-model="formData.mode_of_inheritance"
   *   v-model:hpo-id="formData.inheritance_hpo_id"
   *   label="Mode of Inheritance"
   *   @select="handleInheritanceSelect"
   * />
   */

  import { ref, computed, onMounted, watch } from 'vue'
  import { ontologyAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'

  const props = defineProps({
    modelValue: {
      type: String,
      default: ''
    },
    hpoId: {
      type: String,
      default: ''
    },
    label: {
      type: String,
      default: 'Mode of Inheritance'
    },
    hint: {
      type: String,
      default: 'Select the inheritance pattern'
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
      default: 'mdi-family-tree'
    }
  })

  const emit = defineEmits(['update:modelValue', 'update:hpoId', 'select'])

  const logger = useLogger()

  // HPO ID to shortcode mapping for common patterns
  const HPO_SHORTCODES = {
    'HP:0000006': 'AD', // Autosomal dominant
    'HP:0000007': 'AR', // Autosomal recessive
    'HP:0001417': 'XLD', // X-linked dominant
    'HP:0001419': 'XLR', // X-linked recessive
    'HP:0001423': 'XL', // X-linked
    'HP:0001427': 'MT', // Mitochondrial
    'HP:0001428': 'SN', // Somatic mutation
    'HP:0001450': 'YL', // Y-linked
    'HP:0032113': 'SD', // Semidominant
    'HP:0010984': 'DI', // Digenic
    'HP:0010983': 'OL', // Oligogenic
    'HP:0010982': 'PG' // Polygenic
  }

  // State
  const isLoading = ref(false)
  const loadError = ref(null)
  const mendelianPatterns = ref([])
  const nonMendelianPatterns = ref([])
  const selectedItem = ref(null)

  // Compute items for v-select with headers
  const inheritanceItems = computed(() => {
    const items = []

    // Mendelian patterns
    if (mendelianPatterns.value.length > 0) {
      items.push({
        displayText: 'Mendelian Inheritance',
        isHeader: true,
        hpo_id: 'header_mendelian'
      })
      items.push(
        ...mendelianPatterns.value.map(p => ({
          ...p,
          displayText: `${p.name}${p.shortcode ? ` (${p.shortcode})` : ''}`
        }))
      )
    }

    // Non-Mendelian patterns
    if (nonMendelianPatterns.value.length > 0) {
      items.push({
        displayText: 'Non-Mendelian Inheritance',
        isHeader: true,
        hpo_id: 'header_non_mendelian'
      })
      items.push(
        ...nonMendelianPatterns.value.map(p => ({
          ...p,
          displayText: `${p.name}${p.shortcode ? ` (${p.shortcode})` : ''}`
        }))
      )
    }

    return items
  })

  // Selected value for v-select
  const selectedValue = computed({
    get: () => selectedItem.value,
    set: val => {
      selectedItem.value = val
    }
  })

  /**
   * Fetch inheritance patterns from API
   */
  async function fetchPatterns() {
    isLoading.value = true
    loadError.value = null

    try {
      const response = await ontologyAPI.getInheritancePatterns()

      // Add shortcodes to patterns
      mendelianPatterns.value = response.mendelian.map(p => ({
        ...p,
        shortcode: HPO_SHORTCODES[p.hpo_id] || null
      }))

      nonMendelianPatterns.value = response.non_mendelian.map(p => ({
        ...p,
        shortcode: HPO_SHORTCODES[p.hpo_id] || null
      }))

      logger.debug('Inheritance patterns loaded', {
        mendelian: mendelianPatterns.value.length,
        nonMendelian: nonMendelianPatterns.value.length,
        cached: response.cached
      })

      // If we have a modelValue, find the matching item
      if (props.modelValue || props.hpoId) {
        findAndSelectItem(props.hpoId || props.modelValue)
      }
    } catch (e) {
      loadError.value = e.message
      logger.error('Failed to load inheritance patterns', { error: e.message })
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Find and select an item by HPO ID or shortcode
   */
  function findAndSelectItem(value) {
    if (!value) return

    // First try to find by HPO ID
    let found = [...mendelianPatterns.value, ...nonMendelianPatterns.value].find(
      p => p.hpo_id === value
    )

    // If not found, try by shortcode
    if (!found) {
      found = [...mendelianPatterns.value, ...nonMendelianPatterns.value].find(
        p => p.shortcode === value
      )
    }

    if (found) {
      selectedItem.value = {
        ...found,
        displayText: `${found.name}${found.shortcode ? ` (${found.shortcode})` : ''}`
      }
    }
  }

  /**
   * Handle item selection
   */
  function handleSelect(item) {
    if (item && !item.isHeader) {
      selectedItem.value = item
      // Emit shortcode if available, otherwise HPO ID
      emit('update:modelValue', item.shortcode || item.hpo_id)
      emit('update:hpoId', item.hpo_id)
      emit('select', item)
      logger.info('Inheritance pattern selected', { hpo_id: item.hpo_id, name: item.name })
    } else {
      selectedItem.value = null
      emit('update:modelValue', '')
      emit('update:hpoId', '')
      emit('select', null)
    }
  }

  // Watch for external modelValue changes
  watch(
    () => [props.modelValue, props.hpoId],
    ([newValue, newHpoId]) => {
      const value = newHpoId || newValue
      if (value && (!selectedItem.value || selectedItem.value.hpo_id !== value)) {
        // Only search if patterns are loaded
        if (mendelianPatterns.value.length > 0 || nonMendelianPatterns.value.length > 0) {
          findAndSelectItem(value)
        }
      }
    }
  )

  // Error messages for form validation
  const errorMessages = computed(() => {
    if (loadError.value) return ['Failed to load options']
    if (props.required && !props.modelValue) {
      return ['Mode of inheritance is required']
    }
    return []
  })

  // Fetch patterns on mount
  onMounted(fetchPatterns)
</script>

<style scoped>
  /* Ensure proper chip styling */
  :deep(.v-chip) {
    font-family: 'Roboto Mono', monospace;
  }
</style>
