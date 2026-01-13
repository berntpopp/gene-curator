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
  <v-dialog v-model="isOpen" max-width="600" @keydown.escape="close">
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start color="primary" size="28">mdi-dna</v-icon>
        <span class="text-h6">
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
        <v-btn icon="mdi-close" variant="text" density="compact" @click="close" />
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- Loading State -->
        <div v-if="loading" class="d-flex flex-column align-center py-8">
          <v-progress-circular indeterminate color="primary" size="48" />
          <div class="text-body-2 text-medium-emphasis mt-4">
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
            <div class="text-subtitle-2 text-medium-emphasis mb-3 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-information</v-icon>
              Basic Information
            </div>
            <v-row dense>
              <v-col cols="6" sm="4">
                <div class="text-caption text-medium-emphasis">HGNC ID</div>
                <div class="font-weight-medium">{{ geneData.hgnc_id }}</div>
              </v-col>
              <v-col cols="6" sm="4">
                <div class="text-caption text-medium-emphasis">Symbol</div>
                <div class="font-weight-medium">{{ geneData.symbol }}</div>
              </v-col>
              <v-col cols="12" sm="4">
                <div class="text-caption text-medium-emphasis">Locus Type</div>
                <div class="font-weight-medium">{{ geneData.locus_type || '—' }}</div>
              </v-col>
              <v-col cols="12">
                <div class="text-caption text-medium-emphasis">Full Name</div>
                <div class="font-weight-medium">{{ geneData.name || '—' }}</div>
              </v-col>
            </v-row>
          </div>

          <!-- Location Section -->
          <div class="mb-6">
            <div class="text-subtitle-2 text-medium-emphasis mb-3 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-map-marker</v-icon>
              Genomic Location
            </div>
            <v-row dense>
              <v-col cols="6">
                <div class="text-caption text-medium-emphasis">Chromosome</div>
                <div class="font-weight-medium">{{ geneData.chromosome || '—' }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption text-medium-emphasis">Cytogenetic Band</div>
                <div class="font-weight-medium">{{ geneData.location || '—' }}</div>
              </v-col>
            </v-row>
          </div>

          <!-- Aliases Section -->
          <div v-if="hasAliases" class="mb-6">
            <div class="text-subtitle-2 text-medium-emphasis mb-3 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
              Alternative Names
            </div>
            <v-row dense>
              <v-col v-if="geneData.alias_symbols?.length" cols="12" sm="6">
                <div class="text-caption text-medium-emphasis">Alias Symbols</div>
                <div class="d-flex flex-wrap gap-1 mt-1">
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
                <div class="text-caption text-medium-emphasis">Previous Symbols</div>
                <div class="d-flex flex-wrap gap-1 mt-1">
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
            <div class="text-subtitle-2 text-medium-emphasis mb-3 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
              Alternative Names
            </div>
            <div class="text-body-2 text-medium-emphasis">
              No alias or previous symbols recorded.
            </div>
          </div>
        </template>
      </v-card-text>

      <v-divider />

      <!-- Actions -->
      <v-card-actions class="pa-4">
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
        <v-btn
          v-if="props.geneId"
          variant="text"
          color="secondary"
          :to="`/genes/${props.geneId}`"
          @click="close"
        >
          <v-icon start>mdi-arrow-right</v-icon>
          Full Details
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  /**
   * GeneDetailModal Component
   *
   * Displays comprehensive gene information fetched from HGNC API.
   */

  import { ref, computed, watch } from 'vue'
  import { externalValidationAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'

  const props = defineProps({
    modelValue: {
      type: Boolean,
      default: false
    },
    hgncId: {
      type: String,
      default: ''
    },
    geneSymbol: {
      type: String,
      default: ''
    },
    geneId: {
      type: String,
      default: ''
    }
  })

  const emit = defineEmits(['update:modelValue'])

  const logger = useLogger()

  // State
  const geneData = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Computed v-model binding
  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  // Check if gene has any aliases
  const hasAliases = computed(() => {
    return geneData.value?.alias_symbols?.length > 0 || geneData.value?.previous_symbols?.length > 0
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

      if (response.results && response.results.length > 0) {
        geneData.value = response.results[0]
        logger.debug('Gene data fetched', {
          hgnc_id: props.hgncId,
          symbol: geneData.value.symbol
        })
      } else {
        error.value = 'Gene not found in HGNC database'
      }
    } catch (e) {
      error.value = e.message || 'Failed to fetch gene information'
      logger.error('Failed to fetch gene data', {
        hgnc_id: props.hgncId,
        error: e.message
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

<style scoped>
  .gap-1 {
    gap: 4px;
  }
</style>
