<template>
  <v-card>
    <v-card-title>
      <v-icon start>mdi-calculator</v-icon>
      Live Scoring
    </v-card-title>
    <v-card-text>
      <!-- Skeleton loader during loading -->
      <v-skeleton-loader v-if="loading" type="list-item-avatar@3" :boilerplate="false" />

      <template v-else>
        <!-- Total score display with progress -->
        <div class="text-center mb-4">
          <div class="d-flex align-center justify-center gap-2">
            <div :class="`text-h2 font-weight-bold text-${classificationColor}`">
              {{ totalScore.toFixed(2) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              <div>out of</div>
              <div class="font-weight-bold">{{ maxScore.toFixed(2) }}</div>
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

        <!-- Classification chip with color -->
        <v-chip
          v-if="classification"
          :color="classificationColor"
          size="large"
          variant="flat"
          class="mb-4"
          block
        >
          <v-icon start>{{ getClassificationIcon(classification) }}</v-icon>
          {{ classification }}
        </v-chip>

        <!-- Near-threshold indicator -->
        <v-alert
          v-if="nearThreshold"
          type="info"
          variant="tonal"
          density="compact"
          icon="mdi-alert-circle"
          class="mb-3"
        >
          <div class="text-caption">
            <strong>Near threshold:</strong> Within 1 point of next classification
          </div>
        </v-alert>

        <!-- Category breakdown (expandable) -->
        <v-expansion-panels v-if="hasCategoryScores" variant="accordion" class="mb-3">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start size="small">mdi-view-list</v-icon>
              <span class="text-caption">Category Breakdown</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row dense>
                <v-col
                  v-for="(score, category) in categoryScores"
                  :key="category"
                  cols="12"
                >
                  <v-card variant="outlined">
                    <v-card-text class="d-flex align-center pa-2">
                      <div class="flex-grow-1">
                        <div class="text-caption text-medium-emphasis">
                          {{ formatCategory(category) }}
                        </div>
                        <div
                          class="text-h6 font-weight-bold score-value"
                          :class="getScoreColorClass(score)"
                        >
                          {{ score.toFixed(2) }}
                        </div>
                      </div>
                      <v-icon :color="getCategoryIconColor(score)" size="large">
                        {{ getCategoryIcon(category) }}
                      </v-icon>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Threshold reference (collapsed by default) -->
        <v-expansion-panels v-if="hasThresholds" variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start size="small">mdi-information</v-icon>
              <span class="text-caption">Classification Thresholds</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-list density="compact">
                <v-list-item
                  v-for="(threshold, level) in sortedThresholds"
                  :key="level"
                >
                  <template #prepend>
                    <v-chip
                      :color="getClassificationColorForLevel(level)"
                      size="small"
                      variant="flat"
                    />
                  </template>
                  <v-list-item-title>{{ level }}</v-list-item-title>
                  <v-list-item-subtitle>≥ {{ threshold }} points</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
/**
 * ScoreDisplay Component
 *
 * Schema-agnostic score display sidebar for DynamicForm.
 * Works with any scoring engine (ClinGen, GenCC, Qualitative).
 *
 * Design principles:
 * - Real-time updates with smooth transitions
 * - Schema-agnostic (derives all from props)
 * - Progressive disclosure (expandable details)
 * - Accessible (color + text, semantic HTML)
 *
 * @example
 * <ScoreDisplay
 *   :score-calculations="validationResult.score_calculations"
 *   :scoring-configuration="schema.scoring_configuration"
 *   :loading="validating"
 * />
 */

import { computed } from 'vue'
import { useSchemaScoring } from '@/composables/useSchemaScoring'

const props = defineProps({
  /**
   * Score calculations from validation result
   * Object mapping category names to score values
   */
  scoreCalculations: {
    type: Object,
    default: () => ({})
  },
  /**
   * Scoring configuration from schema
   * Contains engine, thresholds, max_scores
   */
  scoringConfiguration: {
    type: Object,
    default: () => ({})
  },
  /**
   * Loading state (validation in progress)
   */
  loading: {
    type: Boolean,
    default: false
  }
})

// Convert props to refs for composable
const scoreCalculationsRef = computed(() => props.scoreCalculations || {})
const scoringConfigurationRef = computed(() => props.scoringConfiguration || {})

// Use schema scoring composable for calculations
const {
  totalScore,
  categoryScores,
  classification,
  classificationColor,
  nearThreshold,
  maxScore,
  progressPercentage
} = useSchemaScoring(scoreCalculationsRef, scoringConfigurationRef)

// Check if category scores exist
const hasCategoryScores = computed(() => {
  return Object.keys(categoryScores.value).length > 0
})

// Check if thresholds exist
const hasThresholds = computed(() => {
  const thresholds = props.scoringConfiguration?.classification_thresholds
  return thresholds && Object.keys(thresholds).length > 0
})

// Sort thresholds by value (descending)
const sortedThresholds = computed(() => {
  const thresholds = props.scoringConfiguration?.classification_thresholds
  if (!thresholds) return {}

  return Object.entries(thresholds)
    .sort(([, a], [, b]) => b - a)
    .reduce((acc, [level, value]) => {
      acc[level] = value
      return acc
    }, {})
})

/**
 * Format category name: snake_case -> Title Case
 */
function formatCategory(category) {
  return category
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

/**
 * Get Vuetify color class for score value
 */
function getScoreColorClass(score) {
  if (score >= 7) return 'text-success'
  if (score >= 2) return 'text-warning'
  return 'text-info'
}

/**
 * Get icon color for category (based on score)
 */
function getCategoryIconColor(score) {
  if (score >= 7) return 'success'
  if (score >= 2) return 'warning'
  return 'info'
}

/**
 * Get icon for category based on name
 */
function getCategoryIcon(category) {
  const catLower = category.toLowerCase()

  if (catLower.includes('genetic') || catLower.includes('gene')) {
    return 'mdi-dna'
  }

  if (catLower.includes('experimental') || catLower.includes('function') || catLower.includes('model')) {
    return 'mdi-flask'
  }

  if (catLower.includes('clinical') || catLower.includes('phenotype')) {
    return 'mdi-hospital-box'
  }

  if (catLower.includes('qualitative') || catLower.includes('literature')) {
    return 'mdi-chart-bar'
  }

  return 'mdi-chart-box'
}

/**
 * Get icon for classification level
 */
function getClassificationIcon(cls) {
  const clsLower = cls.toLowerCase()

  if (clsLower.includes('definitive') || clsLower.includes('strong')) {
    return 'mdi-check-circle'
  }

  if (clsLower.includes('moderate')) {
    return 'mdi-check'
  }

  if (clsLower.includes('limited') || clsLower.includes('disputed')) {
    return 'mdi-alert'
  }

  return 'mdi-minus-circle'
}

/**
 * Get color for a specific classification level (for threshold display)
 */
function getClassificationColorForLevel(level) {
  const levelLower = level.toLowerCase()

  if (levelLower.includes('definitive') || levelLower.includes('strong')) {
    return 'success'
  }

  if (levelLower.includes('moderate')) {
    return 'info'
  }

  if (levelLower.includes('limited') || levelLower.includes('disputed')) {
    return 'warning'
  }

  return 'grey'
}
</script>

<style scoped>
/* Gap utility */
.gap-2 {
  gap: 8px;
}

/* Smooth transitions for score changes (300ms per CONTEXT.md) */
.text-h2 {
  transition: color 0.3s ease, transform 0.3s ease;
}

.score-value {
  transition: color 0.3s ease;
}

:deep(.v-progress-linear) {
  transition: all 0.3s ease;
}

/* Prevent layout shift during transitions */
.text-h2 {
  min-width: 80px;
  text-align: center;
}
</style>
