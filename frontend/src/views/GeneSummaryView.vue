<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-dna</v-icon>
            Gene Summary: {{ geneSymbol || geneId }}
          </v-card-title>

          <v-card-text>
            <!-- Loading -->
            <v-progress-linear v-if="loading" indeterminate color="primary" />

            <!-- Error -->
            <v-alert v-else-if="error" type="error" variant="tonal">
              {{ error }}
            </v-alert>

            <!-- No data -->
            <v-alert v-else-if="!summary" type="info" variant="tonal">
              <v-alert-title>No Curations Found</v-alert-title>
              This gene has not been curated in any public scopes yet.
            </v-alert>

            <!-- Summary -->
            <div v-else>
              <!-- Overview Cards -->
              <v-row>
                <v-col cols="12" md="4">
                  <v-card variant="tonal" color="primary">
                    <v-card-text>
                      <div class="text-caption">Scopes Curating</div>
                      <div class="text-h4">{{ summary.public_scopes_count }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>

                <v-col cols="12" md="4">
                  <v-card variant="tonal" :color="consensusColor">
                    <v-card-text>
                      <div class="text-caption">Consensus Classification</div>
                      <div class="text-h6">{{ summary.consensus_classification || 'N/A' }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>

                <v-col cols="12" md="4">
                  <v-card variant="tonal" :color="summary.has_conflicts ? 'warning' : 'success'">
                    <v-card-text>
                      <div class="text-caption">Agreement</div>
                      <div class="text-h6">
                        <v-icon>{{ summary.has_conflicts ? 'mdi-alert' : 'mdi-check-circle' }}</v-icon>
                        {{ summary.has_conflicts ? 'Conflicting' : 'Consensus' }}
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <!-- Conflicts Alert -->
              <v-alert
                v-if="summary.has_conflicts"
                type="warning"
                variant="tonal"
                class="mt-4"
              >
                <v-alert-title>
                  <v-icon>mdi-alert</v-icon>
                  Conflicting Classifications
                </v-alert-title>
                Multiple scopes have assigned different classifications to this gene.
                Review individual scope curations below.
              </v-alert>

              <!-- Classification Distribution -->
              <v-card class="mt-4">
                <v-card-title>Classification Distribution</v-card-title>
                <v-card-text>
                  <v-chip-group>
                    <v-chip
                      v-for="(count, classification) in summary.classification_summary"
                      :key="classification"
                      :color="getClassificationColor(classification)"
                      label
                    >
                      {{ classification }}: {{ count }}
                    </v-chip>
                  </v-chip-group>
                </v-card-text>
              </v-card>

              <!-- Per-Scope Summaries -->
              <div class="mt-4">
                <h3 class="text-h6 mb-3">Scope-Specific Curations</h3>
                <v-row>
                  <v-col
                    v-for="scope in summary.scope_summaries"
                    :key="scope.scope_id"
                    cols="12"
                    md="6"
                    lg="4"
                  >
                    <scope-summary-card :scope-summary="scope" />
                  </v-col>
                </v-row>
              </div>

              <!-- Last Updated -->
              <div class="text-caption text-grey mt-4">
                <v-icon size="x-small">mdi-clock-outline</v-icon>
                Last updated: {{ formatDate(summary.last_updated) }}
                <v-chip size="x-small" class="ml-2">
                  ClinGen SOP v11
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useGeneSummaryStore } from '@/stores/geneSummary.js'
import { useGenesStore } from '@/stores/genes.js'
import { useLogger } from '@/composables/useLogger'
import ScopeSummaryCard from '@/components/clingen/ScopeSummaryCard.vue'

const route = useRoute()
const geneSummaryStore = useGeneSummaryStore()
const genesStore = useGenesStore()
const logger = useLogger()

const geneId = route.params.geneId
const geneSymbol = ref('')
const loading = ref(false)
const error = ref(null)

// Computed summary
const summary = computed(() => {
  return geneSummaryStore.getPublicSummary(geneId)
})

// Consensus color
const consensusColor = computed(() => {
  const cls = summary.value?.consensus_classification?.toLowerCase()
  if (cls === 'definitive') return 'success'
  if (cls === 'strong') return 'info'
  if (cls === 'moderate') return 'warning'
  if (cls === 'limited') return 'grey'
  return 'error'
})

// Get classification color helper
const getClassificationColor = (classification) => {
  const cls = classification?.toLowerCase()
  if (cls === 'definitive') return 'success'
  if (cls === 'strong') return 'info'
  if (cls === 'moderate') return 'warning'
  if (cls === 'limited') return 'grey'
  return 'error'
}

// Format date helper
const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Fetch data on mount
onMounted(async () => {
  logger.info('GeneSummaryView mounted', { geneId })
  loading.value = true

  try {
    // Fetch gene summary
    await geneSummaryStore.fetchPublicSummary(geneId)

    // Fetch gene details for symbol
    try {
      const gene = await genesStore.fetchGeneById(geneId)
      geneSymbol.value = gene.approved_symbol
    } catch (geneError) {
      logger.warn('Could not fetch gene details', { geneId, error: geneError.message })
      // Continue even if gene details fail
    }

    logger.info('Gene summary loaded successfully', { geneId })
  } catch (e) {
    error.value = e.message || 'Failed to load gene summary'
    logger.error('Failed to load gene summary', { geneId, error: e.message })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.v-card-title {
  background-color: rgb(var(--v-theme-surface-variant));
}
</style>
