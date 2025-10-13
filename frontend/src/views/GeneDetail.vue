<template>
  <div>
    <v-container v-if="loading" class="loading-container">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="mt-4 text-h6">Loading gene details...</p>
    </v-container>

    <v-container v-else-if="error" class="error-container">
      <v-alert type="error" variant="tonal" class="mb-4">
        {{ error }}
      </v-alert>
      <v-btn :to="{ name: 'Genes' }" color="primary"> Back to Genes </v-btn>
    </v-container>

    <v-container v-else-if="gene">
      <!-- Header -->
      <v-row class="mb-6">
        <v-col cols="12">
          <div class="d-flex align-center mb-4">
            <v-btn :to="{ name: 'Genes' }" icon="mdi-arrow-left" variant="text" class="mr-3" />
            <div class="flex-grow-1">
              <h1 class="text-h3 mb-2">{{ gene.approved_symbol }}</h1>
              <p class="text-subtitle-1 text-medium-emphasis">
                {{ gene.hgnc_id }} •
                {{ gene.details?.gene_description || 'No description available' }}
              </p>
            </div>
            <div v-if="authStore.isCurator">
              <v-btn color="primary" prepend-icon="mdi-pencil" @click="editGene"> Edit Gene </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Basic Information -->
      <v-row class="mb-6">
        <v-col cols="12" lg="8">
          <v-card class="mb-4">
            <v-card-title>
              <v-icon start>mdi-information</v-icon>
              Basic Information
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <InfoField label="HGNC ID" :value="gene.hgnc_id" />
                  <InfoField label="Approved Symbol" :value="gene.approved_symbol" />
                  <InfoField
                    label="Previous Symbols"
                    :value="gene.previous_symbols?.join(', ') || 'None'"
                  />
                  <InfoField
                    label="Alias Symbols"
                    :value="gene.alias_symbols?.join(', ') || 'None'"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <InfoField label="Chromosome" :value="gene.chromosome || 'Unknown'" />
                  <InfoField label="Location" :value="gene.location || 'Unknown'" />
                  <InfoField
                    label="Gene Families"
                    :value="gene.gene_family?.join(', ') || 'None'"
                  />
                  <InfoField
                    label="Current Dyadic Name"
                    :value="gene.current_dyadic_name || 'Not assigned'"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Quick Stats -->
        <v-col cols="12" lg="4">
          <v-card class="mb-4">
            <v-card-title>
              <v-icon start>mdi-chart-line</v-icon>
              ClinGen Metrics
            </v-card-title>
            <v-card-text>
              <div class="text-center">
                <div
                  class="text-h2 font-weight-bold mb-2"
                  :class="getScoreColorClass(gene.details?.clingen_score)"
                >
                  {{ gene.details?.clingen_score ?? 'N/A' }}
                </div>
                <p class="text-body-1 mb-4">ClinGen Score</p>

                <v-divider class="my-4" />

                <div class="d-flex justify-space-between text-body-2">
                  <span>pLI Score:</span>
                  <span class="font-weight-medium">
                    {{ gene.details?.pli_score ?? 'N/A' }}
                  </span>
                </div>
                <div class="d-flex justify-space-between text-body-2">
                  <span>Constraint Score:</span>
                  <span class="font-weight-medium">
                    {{ gene.details?.constraint_score ?? 'N/A' }}
                  </span>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Extended Details -->
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon start>mdi-details</v-icon>
              Extended Details
            </v-card-title>
            <v-card-text>
              <v-expansion-panels variant="accordion">
                <!-- Gene Details -->
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <v-icon start>mdi-dna</v-icon>
                    Gene Details
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-row>
                      <v-col cols="12" md="6">
                        <InfoField
                          label="Gene Type"
                          :value="gene.details?.gene_type || 'Unknown'"
                        />
                        <InfoField label="OMIM ID" :value="gene.details?.omim_id || 'None'" />
                        <InfoField label="Ensembl ID" :value="gene.details?.ensembl_id || 'None'" />
                      </v-col>
                      <v-col cols="12" md="6">
                        <InfoField label="RefSeq ID" :value="gene.details?.refseq_id || 'None'" />
                        <InfoField label="UniProt ID" :value="gene.details?.uniprot_id || 'None'" />
                      </v-col>
                    </v-row>
                  </v-expansion-panel-text>
                </v-expansion-panel>

                <!-- Panels -->
                <v-expansion-panel v-if="gene.details?.panelapp_panels">
                  <v-expansion-panel-title>
                    <v-icon start>mdi-view-dashboard</v-icon>
                    PanelApp Panels
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-chip
                      v-for="panel in gene.details.panelapp_panels"
                      :key="panel"
                      class="ma-1"
                      color="info"
                      variant="tonal"
                    >
                      {{ panel }}
                    </v-chip>
                  </v-expansion-panel-text>
                </v-expansion-panel>

                <!-- Metadata -->
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <v-icon start>mdi-information-outline</v-icon>
                    Metadata
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-row>
                      <v-col cols="12" md="6">
                        <InfoField label="Record Hash" :value="gene.record_hash" monospace />
                        <InfoField label="Created" :value="formatDate(gene.created_at)" />
                      </v-col>
                      <v-col cols="12" md="6">
                        <InfoField label="Last Updated" :value="formatDate(gene.updated_at)" />
                        <InfoField label="Created By" :value="gene.created_by_email || 'Unknown'" />
                      </v-col>
                    </v-row>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, onMounted, computed } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useAuthStore } from '@/stores/auth.js'
  import { useGenesStore } from '@/stores/genes.js'
  import { showError } from '@/composables/useNotifications.js'
  import InfoField from '@/components/InfoField.vue'

  const route = useRoute()
  const router = useRouter()
  const authStore = useAuthStore()
  const genesStore = useGenesStore()

  const loading = ref(true)
  const error = ref(null)

  const gene = computed(() => genesStore.currentGene)

  const getScoreColorClass = score => {
    if (score === null || score === undefined) return 'text-medium-emphasis'
    if (score >= 8) return 'text-success'
    if (score >= 5) return 'text-warning'
    if (score >= 2) return 'text-info'
    return 'text-error'
  }

  const formatDate = dateString => {
    if (!dateString) return 'Unknown'
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  const editGene = () => {
    router.push({
      name: 'GeneAdmin',
      query: { edit: gene.value.id }
    })
  }

  onMounted(async () => {
    try {
      loading.value = true
      error.value = null

      const geneId = route.params.id
      await genesStore.fetchGeneById(geneId)

      if (!gene.value) {
        error.value = 'Gene not found'
      }
    } catch (err) {
      logger.error('Failed to load gene:', { error: err.message, stack: err.stack })
      error.value = 'Failed to load gene details'
      showError('Failed to load gene details')
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 400px;
  }

  .error-container {
    text-align: center;
    padding: 2rem;
  }

  .font-monospace {
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
  }

  .v-expansion-panels {
    border-radius: 8px;
  }
</style>
