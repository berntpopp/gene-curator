<!--
  GeneDetailModal Component

  Modal dialog displaying comprehensive HGNC gene information.
  Fetches fresh data from HGNC API via backend proxy.

  **Features**:
  - Displays all available HGNC gene fields
  - Organized into logical sections (Basic Info, Aliases, Location)
  - Loading state while fetching
  - Error handling for failed fetches
  - External link to HGNC website

  **Props**:
  - modelValue: v-model for dialog visibility
  - hgncId: HGNC ID to fetch (e.g., "HGNC:1234")
  - geneSymbol: Gene symbol for display while loading
  - geneId: Optional gene database ID for linking to full details page

  **Events**:
  - update:modelValue: Dialog visibility change

  @example
  <GeneDetailModal
    v-model="showModal"
    :hgnc-id="gene.hgnc_id"
    :gene-symbol="gene.symbol"
  />
-->

<template>
  <BaseDialog v-model="isOpen" @cancel="close" size="md">
    <template #title
      ><v-icon start color="primary" size="28">mdi-dna</v-icon>
      <span class="text-title-large">
        {{ geneData?.symbol || props.geneSymbol || 'Gene Details' }}
      </span>
      <v-chip
        v-if="geneData?.status"
        :color="geneData.status === 'Approved' ? 'success' : 'grey'"
        size="small"
        variant="tonal"
        class="ml-2"
      >
        {{ geneData.status }}
      </v-chip>
      <v-spacer />
      <v-btn aria-label="Close" icon="mdi-close" variant="text" density="compact" @click="close"
    /></template>
    <!-- Loading State -->
    <div v-if="loading" class="d-flex flex-column align-center py-8">
      <v-progress-circular indeterminate color="primary" size="48" />
      <div class="text-body-medium text-medium-emphasis mt-4">
        Loading gene information from HGNC...
      </div>
    </div>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="mb-0">
      <v-alert-title>Failed to load gene information</v-alert-title>
      {{ error }}
    </v-alert>

    <!-- Gene Information -->
    <template v-else-if="geneData">
      <!-- Basic Information Section -->
      <div class="mb-6">
        <div class="text-title-small text-medium-emphasis mb-3 d-flex align-center">
          <v-icon size="small" class="mr-2">mdi-information</v-icon>
          Basic Information
        </div>
        <v-row dense>
          <v-col cols="6" sm="4">
            <div class="text-body-small text-medium-emphasis">HGNC ID</div>
            <div class="font-weight-medium">{{ geneData.hgnc_id }}</div>
          </v-col>
          <v-col cols="6" sm="4">
            <div class="text-body-small text-medium-emphasis">Symbol</div>
            <div class="font-weight-medium">{{ geneData.symbol }}</div>
          </v-col>
          <v-col cols="12" sm="4">
            <div class="text-body-small text-medium-emphasis">Locus Type</div>
            <div class="font-weight-medium">{{ geneData.locus_type || '—' }}</div>
          </v-col>
          <v-col cols="12">
            <div class="text-body-small text-medium-emphasis">Full Name</div>
            <div class="font-weight-medium">{{ geneData.name || '—' }}</div>
          </v-col>
        </v-row>
      </div>

      <!-- Location Section -->
      <div class="mb-6">
        <div class="text-title-small text-medium-emphasis mb-3 d-flex align-center">
          <v-icon size="small" class="mr-2">mdi-map-marker</v-icon>
          Genomic Location
        </div>
        <v-row dense>
          <v-col cols="6">
            <div class="text-body-small text-medium-emphasis">Chromosome</div>
            <div class="font-weight-medium">{{ geneData.chromosome || '—' }}</div>
          </v-col>
          <v-col cols="6">
            <div class="text-body-small text-medium-emphasis">Cytogenetic Band</div>
            <div class="font-weight-medium">{{ geneData.location || '—' }}</div>
          </v-col>
        </v-row>
      </div>

      <!-- Aliases Section -->
      <div v-if="hasAliases" class="mb-6">
        <div class="text-title-small text-medium-emphasis mb-3 d-flex align-center">
          <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
          Alternative Names
        </div>
        <v-row dense>
          <v-col v-if="geneData.alias_symbols?.length" cols="12" sm="6">
            <div class="text-body-small text-medium-emphasis">Alias Symbols</div>
            <div class="d-flex flex-wrap ga-1 mt-1">
              <v-chip
                v-for="alias in geneData.alias_symbols"
                :key="alias"
                size="small"
                variant="outlined"
              >
                {{ alias }}
              </v-chip>
            </div>
          </v-col>
          <v-col v-if="geneData.previous_symbols?.length" cols="12" sm="6">
            <div class="text-body-small text-medium-emphasis">Previous Symbols</div>
            <div class="d-flex flex-wrap ga-1 mt-1">
              <v-chip
                v-for="prev in geneData.previous_symbols"
                :key="prev"
                size="small"
                variant="outlined"
                color="grey"
              >
                {{ prev }}
              </v-chip>
            </div>
          </v-col>
        </v-row>
      </div>

      <!-- No Aliases Message -->
      <div v-else class="mb-6">
        <div class="text-title-small text-medium-emphasis mb-3 d-flex align-center">
          <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
          Alternative Names
        </div>
        <div class="text-body-medium text-medium-emphasis">
          No alias or previous symbols recorded.
        </div>
      </div>
    </template>
    <template #actions>
      <v-btn
        v-if="geneData?.hgnc_id"
        variant="text"
        color="primary"
        :href="hgncUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        <v-icon start>mdi-open-in-new</v-icon>
        HGNC
      </v-btn>
      <v-btn v-if="props.geneId" variant="text" :to="`/genes/${props.geneId}`" @click="close">
        <v-icon start>mdi-arrow-right</v-icon>
        Full details
      </v-btn>
      <v-btn variant="text" @click="close">Close</v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  /**
   * GeneDetailModal Component
   *
   * Displays comprehensive gene information fetched from HGNC API.
   */

  import { ref, computed, watch } from 'vue'
  import { externalValidationAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import type { Schema } from '@/types/api'
  import type { ApiErrorLike } from '@/components/forms/types'
  import BaseDialog from '@/components/BaseDialog.vue'

  type HgncGene = Schema<'HGNCGeneSearchResult'>

  const props = withDefaults(
    defineProps<{
      modelValue?: boolean
      hgncId?: string
      geneSymbol?: string
      geneId?: string
    }>(),
    {
      modelValue: false,
      hgncId: '',
      geneSymbol: '',
      geneId: ''
    }
  )

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
  }>()

  const logger = useLogger()

  // State
  const geneData = ref<HgncGene | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed v-model binding
  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  // Check if gene has any aliases
  const hasAliases = computed(() => {
    return (
      (geneData.value?.alias_symbols?.length ?? 0) > 0 ||
      (geneData.value?.previous_symbols?.length ?? 0) > 0
    )
  })

  // HGNC external URL
  const hgncUrl = computed(() => {
    if (!geneData.value?.hgnc_id) return ''
    const numericId = geneData.value.hgnc_id.replace('HGNC:', '')
    return `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:${numericId}`
  })

  /**
   * Fetch gene data from HGNC API
   */
  async function fetchGeneData() {
    if (!props.hgncId) {
      error.value = 'No HGNC ID provided'
      return
    }

    loading.value = true
    error.value = null
    geneData.value = null

    try {
      const response = await externalValidationAPI.fetchHGNCGene(props.hgncId)

      const [first] = response.results ?? []
      if (first) {
        geneData.value = first
        logger.debug('Gene data fetched', {
          hgnc_id: props.hgncId,
          symbol: first.symbol
        })
      } else {
        error.value = 'Gene not found in HGNC database'
      }
    } catch (e) {
      const message = (e as ApiErrorLike).message
      error.value = message || 'Failed to fetch gene information'
      logger.error('Failed to fetch gene data', {
        hgnc_id: props.hgncId,
        error: message
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Close the modal
   */
  function close() {
    isOpen.value = false
  }

  // Watch for dialog open to fetch data
  watch(
    () => props.modelValue,
    newValue => {
      if (newValue && props.hgncId) {
        fetchGeneData()
      }
    },
    { immediate: true }
  )

  // Watch for hgncId change while dialog is open
  watch(
    () => props.hgncId,
    newHgncId => {
      if (props.modelValue && newHgncId) {
        fetchGeneData()
      }
    }
  )
</script>

<style scoped></style>
