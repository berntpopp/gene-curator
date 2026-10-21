<template>
  <v-card class="curation-header mb-4" variant="outlined">
    <v-card-text class="pa-4">
      <v-row align="center">
        <!-- Gene Info -->
        <v-col cols="12" md="3">
          <div class="d-flex align-center">
            <v-icon size="32" color="primary" class="mr-3">mdi-dna</v-icon>
            <div>
              <div class="text-body-small text-medium-emphasis">Gene</div>
              <div class="text-headline-small font-weight-bold">
                {{ gene?.approved_symbol || gene?.symbol || 'Unknown' }}
              </div>
              <div v-if="gene?.hgnc_id" class="text-body-small">{{ gene.hgnc_id }}</div>
            </div>
          </div>
        </v-col>

        <!-- Disease Info -->
        <v-col cols="12" md="3">
          <div class="d-flex align-center">
            <v-icon size="32" class="mr-3">mdi-hospital</v-icon>
            <div>
              <div class="text-body-small text-medium-emphasis">Disease</div>
              <div class="text-body-large font-weight-medium">
                {{ disease?.name || 'Not specified' }}
              </div>
              <div v-if="disease?.mondo_id" class="text-body-small">
                <a
                  :href="`https://monarchinitiative.org/disease/${disease.mondo_id}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-decoration-none"
                >
                  {{ disease.mondo_id }}
                  <v-icon size="x-small">mdi-open-in-new</v-icon>
                </a>
              </div>
            </div>
          </div>
        </v-col>

        <!-- MOI -->
        <v-col cols="12" md="2">
          <div class="d-flex align-center">
            <v-icon size="32" color="info" class="mr-3">mdi-family-tree</v-icon>
            <div>
              <div class="text-body-small text-medium-emphasis">Mode of Inheritance</div>
              <v-chip size="small" variant="outlined">
                {{ moiDisplay }}
              </v-chip>
            </div>
          </div>
        </v-col>

        <!-- Classification -->
        <v-col cols="12" md="2">
          <div class="d-flex align-center">
            <div>
              <div class="text-body-small text-medium-emphasis">Classification</div>
              <ClassificationMark :classification="classification" />
            </div>
          </div>
        </v-col>

        <!-- Status & SOP Version -->
        <v-col cols="12" md="2">
          <div class="text-right">
            <v-chip :color="statusColor" size="small" variant="outlined" class="mb-1">
              {{ statusDisplay }}
            </v-chip>
            <div v-if="schemaLabel" class="text-body-small text-medium-emphasis">
              {{ schemaLabel }}
            </div>
            <div v-if="curationId" class="text-body-small">ID: {{ curationId.slice(0, 8) }}...</div>
          </div>
        </v-col>
      </v-row>

      <!-- Expert Panel (if applicable) -->
      <v-row v-if="expertPanel && expertPanel !== 'Not specified'">
        <v-col cols="12">
          <v-divider class="my-2" />
          <div class="d-flex align-center text-body-small text-medium-emphasis">
            <v-icon size="small" class="mr-2">mdi-account-group</v-icon>
            Expert Panel: {{ expertPanel }}
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  /**
   * CurationHeader
   *
   * Displays gene, disease, MOI, classification, and status information
   * at the top of the ClinGen curation form.
   */

  import { computed } from 'vue'
  import { curationStatusColor, curationStatusLabel } from '@/config/status'
  import { humanize } from '@/components/dynamic/fieldLabels'
  import type { DiseaseInfo, GeneInfo } from './types'

  const props = withDefaults(
    defineProps<{
      gene?: GeneInfo
      disease?: DiseaseInfo
      classification?: string | null
      moi?: string
      schema?: { name: string; version: string } | null
      expertPanel?: string | null
      curationId?: string | null
      status?: string
    }>(),
    {
      gene: () => ({}),
      disease: () => ({}),
      classification: null,
      moi: 'Unknown',
      schema: null,
      expertPanel: null,
      curationId: null,
      status: 'draft'
    }
  )

  const schemaLabel = computed(() =>
    props.schema ? `${props.schema.name} v${props.schema.version}` : ''
  )

  // Same labels as CurationDetailView.formatInheritance
  const MOI_LABELS: Record<string, string> = {
    AD: 'Autosomal dominant',
    AR: 'Autosomal recessive',
    XLD: 'X-linked dominant',
    XLR: 'X-linked recessive',
    MT: 'Mitochondrial'
  }
  const moiDisplay = computed(() => {
    const moi = props.moi || ''
    return MOI_LABELS[moi.toUpperCase()] || (moi ? humanize(moi.toLowerCase()) : 'Unknown')
  })

  const statusColor = computed(() => curationStatusColor(props.status))

  const statusDisplay = computed(() => curationStatusLabel(props.status))
</script>

<style scoped>
  .curation-header {
    background: linear-gradient(to right, rgba(var(--v-theme-surface-variant), 0.3), transparent);
  }
</style>
