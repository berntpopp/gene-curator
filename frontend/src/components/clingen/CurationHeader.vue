<template>
  <v-card class="curation-header mb-4" variant="outlined">
    <v-card-text class="pa-4">
      <v-row align="center">
        <!-- Gene Info -->
        <v-col cols="12" md="3">
          <div class="d-flex align-center">
            <v-icon size="32" color="primary" class="mr-3">mdi-dna</v-icon>
            <div>
              <div class="text-caption text-medium-emphasis">Gene</div>
              <div class="text-h5 font-weight-bold">{{ gene?.symbol || 'Unknown' }}</div>
              <div v-if="gene?.hgnc_id" class="text-caption">{{ gene.hgnc_id }}</div>
            </div>
          </div>
        </v-col>

        <!-- Disease Info -->
        <v-col cols="12" md="3">
          <div class="d-flex align-center">
            <v-icon size="32" color="secondary" class="mr-3">mdi-hospital</v-icon>
            <div>
              <div class="text-caption text-medium-emphasis">Disease</div>
              <div class="text-subtitle-1 font-weight-medium">
                {{ disease?.name || 'Not specified' }}
              </div>
              <div v-if="disease?.mondo_id" class="text-caption">
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
              <div class="text-caption text-medium-emphasis">Mode of Inheritance</div>
              <v-chip :color="moiColor" size="small" variant="tonal">
                {{ moiDisplay }}
              </v-chip>
            </div>
          </div>
        </v-col>

        <!-- Classification -->
        <v-col cols="12" md="2">
          <div class="d-flex align-center">
            <v-icon size="32" :color="classificationColor" class="mr-3">mdi-certificate</v-icon>
            <div>
              <div class="text-caption text-medium-emphasis">Classification</div>
              <v-chip :color="classificationColor" size="small">
                {{ classification || 'Not Classified' }}
              </v-chip>
            </div>
          </div>
        </v-col>

        <!-- Status & SOP Version -->
        <v-col cols="12" md="2">
          <div class="text-right">
            <v-chip :color="statusColor" size="small" variant="outlined" class="mb-1">
              {{ statusDisplay }}
            </v-chip>
            <div class="text-caption text-medium-emphasis">{{ sopVersion }}</div>
            <div v-if="curationId" class="text-caption">ID: {{ curationId.slice(0, 8) }}...</div>
          </div>
        </v-col>
      </v-row>

      <!-- Expert Panel (if applicable) -->
      <v-row v-if="expertPanel && expertPanel !== 'Not specified'">
        <v-col cols="12">
          <v-divider class="my-2" />
          <div class="d-flex align-center text-caption text-medium-emphasis">
            <v-icon size="small" class="mr-2">mdi-account-group</v-icon>
            Expert Panel: {{ expertPanel }}
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
  /**
   * CurationHeader
   *
   * Displays gene, disease, MOI, classification, and status information
   * at the top of the ClinGen curation form.
   */

  import { computed } from 'vue'

  const props = defineProps({
    gene: {
      type: Object,
      default: () => ({})
    },
    disease: {
      type: Object,
      default: () => ({})
    },
    classification: {
      type: String,
      default: null
    },
    moi: {
      type: String,
      default: 'Unknown'
    },
    sopVersion: {
      type: String,
      default: 'SOP v11'
    },
    expertPanel: {
      type: String,
      default: null
    },
    curationId: {
      type: String,
      default: null
    },
    status: {
      type: String,
      default: 'draft'
    }
  })

  const moiDisplay = computed(() => {
    const moi = props.moi?.toLowerCase() || ''
    if (moi.includes('dominant') || moi === 'ad') return 'AD'
    if (moi.includes('recessive') || moi === 'ar') return 'AR'
    if (moi.includes('x-linked') || moi === 'xl') return 'X-linked'
    if (moi.includes('mitochondrial')) return 'MT'
    return props.moi || 'Unknown'
  })

  const moiColor = computed(() => {
    const moi = moiDisplay.value
    const colorMap = {
      AD: 'purple',
      AR: 'blue',
      'X-linked': 'pink',
      MT: 'orange'
    }
    return colorMap[moi] || 'grey'
  })

  const classificationColor = computed(() => {
    const classification = props.classification?.toLowerCase() || ''
    const colorMap = {
      definitive: 'success',
      strong: 'info',
      moderate: 'warning',
      limited: 'grey',
      disputed: 'error',
      refuted: 'error',
      'no known disease relationship': 'grey'
    }
    return colorMap[classification] || 'grey'
  })

  const statusColor = computed(() => {
    const statusMap = {
      draft: 'grey',
      submitted: 'info',
      in_review: 'warning',
      approved: 'success',
      active: 'primary',
      archived: 'grey'
    }
    return statusMap[props.status] || 'grey'
  })

  const statusDisplay = computed(() => {
    const displayMap = {
      draft: 'Draft',
      submitted: 'Submitted',
      in_review: 'In Review',
      approved: 'Approved',
      active: 'Active',
      archived: 'Archived'
    }
    return displayMap[props.status] || props.status
  })
</script>

<style scoped>
  .curation-header {
    background: linear-gradient(to right, rgba(var(--v-theme-surface-variant), 0.3), transparent);
  }
</style>
