<template>
  <v-card :color="cardColor" variant="tonal">
    <v-card-title class="d-flex align-center">
      <v-icon start :color="classificationColor">mdi-chart-line</v-icon>
      <span class="text-subtitle-1">ClinGen SOP v11 Score</span>
      <v-spacer />
      <v-chip :color="classificationColor" size="small" variant="elevated" class="font-weight-bold">
        {{ breakdown.classification }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Total Score Display -->
      <div class="text-center mb-4">
        <div class="d-flex align-center justify-center gap-2">
          <div :class="`text-h2 font-weight-bold text-${classificationColor}`">
            {{ breakdown.total_score.toFixed(2) }}
          </div>
          <div class="text-caption text-medium-emphasis">
            <div>out of</div>
            <div class="font-weight-bold">18.00</div>
          </div>
        </div>

        <v-progress-linear
          :model-value="progressPercentage"
          :color="classificationColor"
          height="8"
          rounded
          class="mt-2"
        >
          <template #default>
            <div class="text-caption font-weight-bold">{{ progressPercentage.toFixed(0) }}%</div>
          </template>
        </v-progress-linear>
      </div>

      <!-- Category Breakdown (Compact) -->
      <v-row dense>
        <v-col cols="6">
          <v-card variant="outlined" density="compact">
            <v-card-text class="text-center pa-2">
              <div class="text-caption text-medium-emphasis">Genetic Evidence</div>
              <div class="text-h6 font-weight-bold text-primary">
                {{ breakdown.genetic_total.toFixed(2) }}
              </div>
              <v-progress-linear
                :model-value="(breakdown.genetic_total / 12) * 100"
                color="primary"
                height="4"
                rounded
                class="mt-1"
              />
              <div class="text-caption text-medium-emphasis mt-1">max 12.00</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6">
          <v-card variant="outlined" density="compact">
            <v-card-text class="text-center pa-2">
              <div class="text-caption text-medium-emphasis">Experimental Evidence</div>
              <div class="text-h6 font-weight-bold text-secondary">
                {{ breakdown.experimental_total.toFixed(2) }}
              </div>
              <v-progress-linear
                :model-value="(breakdown.experimental_total / 6) * 100"
                color="secondary"
                height="4"
                rounded
                class="mt-1"
              />
              <div class="text-caption text-medium-emphasis mt-1">max 6.00</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Evidence Count Summary -->
      <v-alert
        v-if="evidenceCount > 0"
        :icon="isSufficientEvidence ? 'mdi-check-circle' : 'mdi-alert-circle'"
        :color="isSufficientEvidence ? 'success' : 'warning'"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        <div class="text-caption">
          <strong>{{ evidenceCount }}</strong> evidence item{{ evidenceCount !== 1 ? 's' : '' }}
          added
          <span v-if="!isSufficientEvidence"> - Add more evidence for classification </span>
        </div>
      </v-alert>

      <!-- No Evidence State -->
      <v-alert
        v-else
        icon="mdi-information"
        color="info"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        <div class="text-caption">No evidence items added yet</div>
      </v-alert>

      <!-- Category Details (Expandable) -->
      <v-expansion-panels v-if="showDetails" variant="accordion" class="mt-3">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-view-list</v-icon>
            <span class="text-caption">Detailed Breakdown</span>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <!-- Genetic Categories -->
            <div class="mb-2">
              <div class="text-caption font-weight-bold text-primary mb-1">Genetic Evidence</div>
              <v-row dense>
                <v-col cols="6">
                  <div class="text-caption">Case-Level</div>
                  <div class="font-weight-bold">{{ breakdown.case_level_score.toFixed(2) }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">Segregation</div>
                  <div class="font-weight-bold">{{ breakdown.segregation_score.toFixed(2) }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">Case-Control</div>
                  <div class="font-weight-bold">{{ breakdown.case_control_score.toFixed(2) }}</div>
                </v-col>
              </v-row>
            </div>

            <v-divider class="my-2" />

            <!-- Experimental Categories -->
            <div>
              <div class="text-caption font-weight-bold text-secondary mb-1">
                Experimental Evidence
              </div>
              <v-row dense>
                <v-col cols="6">
                  <div class="text-caption">Expression</div>
                  <div class="font-weight-bold">{{ breakdown.expression_score.toFixed(2) }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">Function</div>
                  <div class="font-weight-bold">{{ breakdown.function_score.toFixed(2) }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">Models</div>
                  <div class="font-weight-bold">{{ breakdown.models_score.toFixed(2) }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">Rescue</div>
                  <div class="font-weight-bold">{{ breakdown.rescue_score.toFixed(2) }}</div>
                </v-col>
              </v-row>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <v-card-actions v-if="showFullScoreLink">
      <v-spacer />
      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-file-document"
        @click="$emit('view-full-score')"
      >
        View Full Scorecard
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
  /**
   * ScorePreview Component
   *
   * Real-time ClinGen SOP v11 score preview for curation forms.
   * Updates automatically as evidence items are added/removed.
   *
   * Design principles:
   * - Real-time calculation (client-side preview)
   * - Clear visual hierarchy (score → classification → breakdown)
   * - Progressive disclosure (expand for details)
   * - Accessible (color + text, ARIA labels)
   * - Mobile-responsive
   *
   * @example
   * <score-preview
   *   :evidence-items="formData.evidence_items"
   *   show-details
   *   show-full-score-link
   *   @view-full-score="openScoreCard"
   * />
   */

  import { computed } from 'vue'
  import { useScoring } from '@/composables/useScoring.js'

  const props = defineProps({
    /**
     * Array of evidence items with computed scores
     * Each item should have: evidence_type, evidence_category, computed_score
     */
    evidenceItems: {
      type: Array,
      default: () => []
    },
    /**
     * Show expandable detailed breakdown
     */
    showDetails: {
      type: Boolean,
      default: true
    },
    /**
     * Show "View Full Scorecard" link
     */
    showFullScoreLink: {
      type: Boolean,
      default: false
    },
    /**
     * Compact mode (smaller text, less padding)
     */
    compact: {
      type: Boolean,
      default: false
    }
  })

  defineEmits(['view-full-score'])

  // Reactive evidence items reference
  const evidenceItemsRef = computed(() => props.evidenceItems || [])

  // Use scoring composable for real-time calculation
  const { breakdown, classificationColor, progressPercentage, isSufficientEvidence } =
    useScoring(evidenceItemsRef)

  // Evidence count
  const evidenceCount = computed(() => evidenceItemsRef.value.length)

  // Card color based on classification (subtle tonal background)
  const cardColor = computed(() => {
    if (breakdown.value.total_score === 0) return 'default'
    return classificationColor.value
  })
</script>

<style scoped>
  /* Ensure consistent spacing */
  .gap-2 {
    gap: 8px;
  }

  /* Smooth transitions for score changes */
  .text-h2 {
    transition: color 0.3s ease;
  }

  :deep(.v-progress-linear) {
    transition: all 0.3s ease;
  }

  /* Compact mode */
  .v-card--compact {
    font-size: 0.875rem;
  }

  .v-card--compact .text-h2 {
    font-size: 2rem;
  }
</style>
