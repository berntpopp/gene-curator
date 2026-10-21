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
                        <v-icon>{{
                          summary.has_conflicts ? 'mdi-alert' : 'mdi-check-circle'
                        }}</v-icon>
                        {{ summary.has_conflicts ? 'Conflicting' : 'Consensus' }}
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <!-- Conflicts Alert -->
              <v-alert v-if="summary.has_conflicts" type="warning" variant="tonal" class="mt-4">
                <v-alert-title>
                  <v-icon>mdi-alert</v-icon>
                  Conflicting Classifications
                </v-alert-title>
                Multiple scopes have assigned different classifications to this gene. Review
                individual scope curations below.
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
                    v-for="(scope, index) in scopeSummaries"
                    :key="String(scope.scope_id ?? index)"
                    cols="12"
                    md="6"
                    lg="4"
                  >
                    <ScopeSummaryCard :scope-summary="scope" />
                  </v-col>
                </v-row>
              </div>

              <!-- Last Updated -->
              <div class="text-caption text-grey mt-4">
                <v-icon size="x-small">mdi-clock-outline</v-icon>
                Last updated: {{ formatDate(summary.last_updated) }}
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useGeneSummaryStore } from '@/stores/geneSummary'
  import { useGenesStore } from '@/stores/genes'
  import { useLogger } from '@/composables/useLogger'
  import ScopeSummaryCard from '@/components/clingen/ScopeSummaryCard.vue'

  const route = useRoute()
  const geneSummaryStore = useGeneSummaryStore()
  const genesStore = useGenesStore()
  const logger = useLogger()

  const geneId = computed(() => route.params.geneId as string)
  const geneSymbol = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed summary
  const summary = computed(() => {
    return geneSummaryStore.getPublicSummary(geneId.value)
  })

  // The API types scope summaries as free-form dicts; the card documents the expected shape
  type ScopeSummaryProps = InstanceType<typeof ScopeSummaryCard>['scopeSummary']
  const scopeSummaries = computed(
    () =>
      (summary.value?.scope_summaries ?? []) as unknown as (ScopeSummaryProps & {
        scope_id?: string
      })[]
  )

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
  const getClassificationColor = (classification: string | number) => {
    const cls = String(classification).toLowerCase()
    if (cls === 'definitive') return 'success'
    if (cls === 'strong') return 'info'
    if (cls === 'moderate') return 'warning'
    if (cls === 'limited') return 'grey'
    return 'error'
  }

  // Format date helper
  const formatDate = (dateString: string | null | undefined) => {
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

  async function load(geneId: string) {
    logger.info('GeneSummaryView loading', { geneId })
    loading.value = true
    error.value = null
    geneSymbol.value = ''

    try {
      // Fetch gene summary
      await geneSummaryStore.fetchPublicSummary(geneId)

      // Fetch gene details for symbol
      try {
        const gene = await genesStore.fetchGeneById(geneId)
        geneSymbol.value = gene.approved_symbol
      } catch (geneError) {
        logger.warn('Could not fetch gene details', { geneId, error: (geneError as Error).message })
        // Continue even if gene details fail
      }

      logger.info('Gene summary loaded successfully', { geneId })
    } catch (e) {
      const err = e as Error
      error.value = err.message || 'Failed to load gene summary'
      logger.error('Failed to load gene summary', { geneId, error: err.message })
    } finally {
      loading.value = false
    }
  }

  // Reload when navigating between genes (the component is reused for /genes/:geneId/summary)
  watch(geneId, load, { immediate: true })
</script>

<style scoped>
  .v-card-title {
    background-color: rgb(var(--v-theme-surface-variant));
  }
</style>
