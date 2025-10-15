<template>
  <v-card>
    <v-card-title>
      <div class="d-flex align-center justify-space-between">
        <span>{{ scopeSummary.scope_name }}</span>
        <v-chip :color="classificationColor" size="small" label>
          {{ scopeSummary.classification || 'N/A' }}
        </v-chip>
      </div>
    </v-card-title>

    <v-card-text>
      <!-- Score breakdown -->
      <v-row dense>
        <v-col cols="6">
          <div class="text-caption text-grey">Genetic Score</div>
          <div class="text-h6">{{ scopeSummary.genetic_score.toFixed(2) }}</div>
        </v-col>
        <v-col cols="6">
          <v-col cols="6">
            <div class="text-caption text-grey">Experimental Score</div>
            <div class="text-h6">{{ scopeSummary.experimental_score.toFixed(2) }}</div>
          </v-col>
        </v-col>
      </v-row>

      <!-- Total score -->
      <v-divider class="my-3" />
      <div class="d-flex justify-space-between align-center">
        <span class="text-subtitle-2">Total Score</span>
        <span class="text-h5 font-weight-bold">{{ scopeSummary.total_score.toFixed(2) }}</span>
      </div>

      <!-- Progress bar -->
      <v-progress-linear
        :model-value="progressPercentage"
        :color="classificationColor"
        height="8"
        rounded
        class="mt-2"
      />

      <!-- Metadata -->
      <v-divider class="my-3" />
      <div class="text-caption text-grey">
        <v-row dense>
          <v-col cols="6">
            <div>
              <v-icon size="x-small">mdi-account-group</v-icon>
              {{ scopeSummary.curator_count }} curators
            </div>
          </v-col>
          <v-col cols="6">
            <div>
              <v-icon size="x-small">mdi-file-document</v-icon>
              {{ scopeSummary.evidence_count }} evidence items
            </div>
          </v-col>
        </v-row>
        <div class="mt-2">
          <v-icon size="x-small">mdi-clock-outline</v-icon>
          Updated: {{ formatDate(scopeSummary.last_updated) }}
        </div>
      </div>

      <!-- Public/Private indicator -->
      <v-chip v-if="!scopeSummary.is_public" size="x-small" color="grey" class="mt-2">
        <v-icon start size="x-small">mdi-lock</v-icon>
        Private
      </v-chip>
    </v-card-text>
  </v-card>
</template>

<script setup>
  import { computed } from 'vue'

  const props = defineProps({
    scopeSummary: {
      type: Object,
      required: true
    }
  })

  // Classification color based on score
  const classificationColor = computed(() => {
    const cls = props.scopeSummary.classification?.toLowerCase()
    if (cls === 'definitive') return 'success'
    if (cls === 'strong') return 'info'
    if (cls === 'moderate') return 'warning'
    if (cls === 'limited') return 'grey'
    return 'error'
  })

  // Progress percentage (0-100) based on max score of 12
  const progressPercentage = computed(() => {
    return Math.min((props.scopeSummary.total_score / 12) * 100, 100)
  })

  // Format date helper
  const formatDate = dateString => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }
</script>
