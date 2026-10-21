<!--
  GeneDetail View

  Full page view displaying comprehensive HGNC gene information.
  Fetches fresh data from HGNC API via backend proxy.

  **Features**:
  - Displays all available HGNC gene fields
  - Organized into logical sections matching GeneDetailModal design
  - Loading state while fetching
  - Error handling for failed fetches
  - External link to HGNC website
  - Shows local database metadata (created/updated dates)

  @example
  // Route: /genes/:id
-->

<template>
  <v-container>
    <!-- Loading State -->
    <div v-if="loading" class="d-flex flex-column align-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-large text-medium-emphasis mt-6">Loading gene information...</div>
    </div>

    <!-- Error State -->
    <v-alert v-else-if="notFound" type="warning" variant="tonal" class="mb-4">
      <v-alert-title>Gene not found</v-alert-title>
      This gene does not exist or was removed.
      <template #append>
        <v-btn :to="{ name: 'GeneCatalogue' }" variant="text"> Back to the gene catalogue </v-btn>
      </template>
    </v-alert>
    <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
      <v-alert-title>Failed to load gene information</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn
          class="retry"
          variant="text"
          color="error"
          @click="loadGene(String(route.params.id))"
        >
          Retry
        </v-btn>
        <v-btn :to="{ name: 'GeneCatalogue' }" variant="text" color="error"> Back to genes </v-btn>
      </template>
    </v-alert>

    <!-- Gene Information -->
    <template v-else-if="localGene">
      <!-- Header -->
      <div class="d-flex align-center mb-6">
        <v-btn
          aria-label="Back to genes"
          :to="{ name: 'GeneCatalogue' }"
          icon="mdi-arrow-left"
          variant="text"
          class="mr-3"
        />
        <v-icon size="32" color="primary" class="mr-3">mdi-dna</v-icon>
        <div class="flex-grow-1">
          <div class="d-flex align-center">
            <h1 class="text-headline-large font-weight-bold">
              {{ hgncData?.symbol || localGene.approved_symbol }}
            </h1>
            <v-chip
              v-if="hgncData?.status"
              :color="hgncData.status === 'Approved' ? 'success' : 'grey'"
              size="small"
              variant="tonal"
              class="ml-3"
            >
              {{ hgncData.status }}
            </v-chip>
          </div>
          <p class="text-body-large text-medium-emphasis mt-1">
            {{ hgncData?.name || 'Loading gene details from HGNC...' }}
          </p>
        </div>
      </div>

      <v-row>
        <!-- Main Content -->
        <v-col cols="12" lg="8">
          <!-- Basic Information Section -->
          <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
              <v-icon start size="20">mdi-information</v-icon>
              Basic information
            </v-card-title>
            <v-card-text>
              <v-row dense>
                <v-col cols="6" sm="4">
                  <div class="text-body-small text-medium-emphasis">HGNC ID</div>
                  <div class="font-weight-medium">
                    {{ hgncData?.hgnc_id || localGene.hgnc_id }}
                  </div>
                </v-col>
                <v-col cols="6" sm="4">
                  <div class="text-body-small text-medium-emphasis">Symbol</div>
                  <div class="font-weight-medium">
                    {{ hgncData?.symbol || localGene.approved_symbol }}
                  </div>
                </v-col>
                <v-col cols="12" sm="4">
                  <div class="text-body-small text-medium-emphasis">Locus Type</div>
                  <div class="font-weight-medium">
                    {{ hgncData?.locus_type || '—' }}
                  </div>
                </v-col>
                <v-col cols="12" class="mt-2">
                  <div class="text-body-small text-medium-emphasis">Full Name</div>
                  <div class="font-weight-medium">
                    {{ hgncData?.name || '—' }}
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Location Section -->
          <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
              <v-icon start size="20">mdi-map-marker</v-icon>
              Genomic location
            </v-card-title>
            <v-card-text>
              <v-row dense>
                <v-col cols="6">
                  <div class="text-body-small text-medium-emphasis">Chromosome</div>
                  <div class="font-weight-medium">
                    {{ hgncData?.chromosome || localGene.chromosome || '—' }}
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-body-small text-medium-emphasis">Cytogenetic Band</div>
                  <div class="font-weight-medium">
                    {{ hgncData?.location || localGene.location || '—' }}
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Aliases Section -->
          <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
              <v-icon start size="20">mdi-tag-multiple</v-icon>
              Alternative names
            </v-card-title>
            <v-card-text>
              <template v-if="hasAliases">
                <v-row dense>
                  <v-col v-if="aliasSymbols?.length" cols="12" sm="6">
                    <div class="text-body-small text-medium-emphasis mb-2">Alias Symbols</div>
                    <div class="d-flex flex-wrap ga-1">
                      <v-chip
                        v-for="alias in aliasSymbols"
                        :key="alias"
                        size="small"
                        variant="outlined"
                      >
                        {{ alias }}
                      </v-chip>
                    </div>
                  </v-col>
                  <v-col v-if="previousSymbols?.length" cols="12" sm="6">
                    <div class="text-body-small text-medium-emphasis mb-2">Previous Symbols</div>
                    <div class="d-flex flex-wrap ga-1">
                      <v-chip
                        v-for="prev in previousSymbols"
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
              </template>
              <div v-else class="text-body-medium text-medium-emphasis">
                No alias or previous symbols recorded.
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Sidebar -->
        <v-col cols="12" lg="4">
          <!-- External Links -->
          <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
              <v-icon start size="20">mdi-link-variant</v-icon>
              External links
            </v-card-title>
            <v-card-text>
              <v-btn
                v-if="hgncUrl"
                :href="hgncUrl"
                target="_blank"
                rel="noopener noreferrer"
                variant="outlined"
                color="primary"
                block
                class="mb-2"
              >
                <v-icon start>mdi-open-in-new</v-icon>
                View on HGNC
              </v-btn>
              <div v-else class="text-body-medium text-medium-emphasis text-center py-2">
                No external links available
              </div>
            </v-card-text>
          </v-card>

          <!-- Database Metadata -->
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-icon start size="20">mdi-database</v-icon>
              Database record
            </v-card-title>
            <v-card-text>
              <div class="mb-3">
                <div class="text-body-small text-medium-emphasis">Record ID</div>
                <div class="font-weight-medium text-truncate" :title="localGene.id">
                  {{ localGene.id }}
                </div>
              </div>
              <div class="mb-3">
                <div class="text-body-small text-medium-emphasis">Created</div>
                <div class="font-weight-medium">
                  {{ formatDateTime(localGene.created_at) }}
                </div>
              </div>
              <div>
                <div class="text-body-small text-medium-emphasis">Last Updated</div>
                <div class="font-weight-medium">
                  {{ formatDateTime(localGene.updated_at) }}
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script setup lang="ts">
  import { formatDateTime } from '@/utils/format'
  /**
   * GeneDetail View
   *
   * Displays comprehensive gene information fetched from HGNC API,
   * combined with local database metadata.
   */

  import { ref, computed, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useGenesStore } from '@/stores/genes'
  import { externalValidationAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import type { Schema } from '@/types/api'

  type Gene = Schema<'Gene'>
  type HgncGene = Schema<'HGNCGeneSearchResult'>

  const route = useRoute()
  const genesStore = useGenesStore()
  const logger = useLogger()

  // State
  const loading = ref(true)
  const error = ref<string | null>(null)
  const notFound = ref(false)
  const hgncData = ref<HgncGene | null>(null)

  // Local gene data from database (store is JS, so its currentGene is typed null)
  const localGene = computed(() => genesStore.currentGene as Gene | null)

  // Computed properties for aliases (prefer HGNC data, fallback to local)
  const aliasSymbols = computed<string[]>(() => {
    return hgncData.value?.alias_symbols || localGene.value?.alias_symbols || []
  })

  const previousSymbols = computed<string[]>(() => {
    return hgncData.value?.previous_symbols || localGene.value?.previous_symbols || []
  })

  const hasAliases = computed(() => {
    return aliasSymbols.value?.length > 0 || previousSymbols.value?.length > 0
  })

  // HGNC external URL
  const hgncUrl = computed<string>(() => {
    const hgncId = hgncData.value?.hgnc_id || localGene.value?.hgnc_id
    if (!hgncId) return ''
    const numericId = hgncId.replace('HGNC:', '')
    return `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:${numericId}`
  })

  /**
   * Fetch HGNC data for the gene
   */
  async function fetchHgncData(hgncId: string | null | undefined): Promise<void> {
    if (!hgncId) return

    try {
      const response = await externalValidationAPI.fetchHGNCGene(hgncId)

      if (response.results.length > 0) {
        hgncData.value = response.results[0] ?? null
        logger.debug('HGNC data fetched', {
          hgnc_id: hgncId,
          symbol: hgncData.value?.symbol
        })
      }
    } catch (e) {
      logger.warn('Failed to fetch HGNC data, using local data', {
        hgnc_id: hgncId,
        error: (e as Error).message
      })
      // Don't set error - we can still show local data
    }
  }

  async function loadGene(geneId: string) {
    try {
      loading.value = true
      error.value = null
      notFound.value = false
      hgncData.value = null

      const gene = await genesStore.fetchGeneById(geneId)

      // Fetch HGNC data for enhanced information
      if (gene.hgnc_id) {
        await fetchHgncData(gene.hgnc_id)
      }

      logger.info('Gene details loaded', {
        gene_id: geneId,
        symbol: gene.approved_symbol
      })
    } catch (err) {
      const e = err as Error
      logger.error('Failed to load gene details', {
        error: e.message,
        stack: e.stack
      })
      notFound.value = (err as { response?: { status?: number } }).response?.status === 404
      error.value = 'Failed to load gene details'
    } finally {
      loading.value = false
    }
  }

  // Reload when navigating between genes (the component is reused for /genes/:id)
  watch(() => route.params.id as string, loadGene, { immediate: true })
</script>

<style scoped></style>
