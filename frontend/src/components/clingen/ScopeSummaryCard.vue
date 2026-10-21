<template>
  <v-card>
    <v-card-title>
      <div class="d-flex align-center justify-space-between">
        <span>{{ scopeSummary.scope_name }}</span>
        <ClassificationMark :classification="scopeSummary.classification" />
      </div>
    </v-card-title>

    <v-card-text>
      <!-- Score breakdown -->
      <v-row dense>
        <v-col cols="6">
          <div class="text-body-small text-grey">Genetic Score</div>
          <div class="text-title-large">{{ scopeSummary.genetic_score.toFixed(2) }}</div>
        </v-col>
        <v-col cols="6">
          <v-col cols="6">
            <div class="text-body-small text-grey">Experimental Score</div>
            <div class="text-title-large">{{ scopeSummary.experimental_score.toFixed(2) }}</div>
          </v-col>
        </v-col>
      </v-row>

      <!-- Total score -->
      <v-divider class="my-3" />
      <div class="d-flex justify-space-between align-center">
        <span class="text-title-small">Total Score</span>
        <span class="text-headline-small font-weight-bold">{{
          scopeSummary.total_score.toFixed(2)
        }}</span>
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
      <div class="text-body-small text-grey">
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

<script setup lang="ts">
  import { formatDate } from '@/utils/format'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { getClassification } from '@/config/classification'
  import { computed } from 'vue'

  interface ScopeSummary {
    scope_name: string
    classification?: string | null
    genetic_score: number
    experimental_score: number
    total_score: number
    curator_count: number
    evidence_count: number
    last_updated?: string | null
    is_public?: boolean
  }

  const props = defineProps<{ scopeSummary: ScopeSummary }>()

  const classificationColor = computed(
    () => getClassification(props.scopeSummary.classification).color
  )

  // Progress percentage (0-100) of the 18-point maximum
  const progressPercentage = computed(() => {
    return Math.min((props.scopeSummary.total_score / 18) * 100, 100)
  })

  // Format date helper
</script>
