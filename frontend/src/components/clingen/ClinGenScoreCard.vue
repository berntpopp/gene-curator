<template>
  <v-card>
    <!-- Header -->
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-chart-box" class="mr-2" />
      ClinGen SOP v11 Score
      <v-spacer />
      <v-chip :color="classificationColor" size="large" class="font-weight-bold">
        {{ classification }}
      </v-chip>
    </v-card-title>

    <v-divider />

    <v-card-text>
      <!-- Total Score Display -->
      <div class="text-center mb-6">
        <div class="text-h1" :style="{ color: classificationColor }">
          {{ totalScore.toFixed(2) }}
        </div>
        <div class="text-caption text-medium-emphasis mb-2">out of 18 points</div>
        <v-progress-linear
          :model-value="progressPercentage"
          :color="classificationColor"
          height="20"
          rounded
          striped
        >
          <strong>{{ Math.round(progressPercentage) }}%</strong>
        </v-progress-linear>

        <!-- Classification guide -->
        <div class="mt-4 text-caption">
          <v-chip size="x-small" color="success" class="mr-1">≥12 Definitive</v-chip>
          <v-chip size="x-small" color="info" class="mr-1">7-11.99 Strong</v-chip>
          <v-chip size="x-small" color="warning" class="mr-1">2-6.99 Moderate</v-chip>
          <v-chip size="x-small" color="grey" class="mr-1">0.1-1.99 Limited</v-chip>
          <v-chip size="x-small" color="error">&lt;0.1 No Known</v-chip>
        </div>
      </div>

      <!-- Score Breakdown -->
      <v-row class="mb-4">
        <!-- Genetic Evidence -->
        <v-col cols="12" md="6">
          <v-card variant="outlined" color="primary">
            <v-card-title class="text-subtitle-1 bg-primary">
              <v-icon start size="small">mdi-dna</v-icon>
              Genetic Evidence
            </v-card-title>
            <v-card-text>
              <div class="d-flex align-center justify-space-between mb-2">
                <span class="text-h4 font-weight-bold">{{ geneticScore.toFixed(2) }}</span>
                <span class="text-caption">/ 12 points</span>
              </div>
              <v-progress-linear
                :model-value="(geneticScore / 12) * 100"
                color="primary"
                height="8"
                rounded
              />
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Experimental Evidence -->
        <v-col cols="12" md="6">
          <v-card variant="outlined" color="secondary">
            <v-card-title class="text-subtitle-1 bg-secondary">
              <v-icon start size="small">mdi-flask</v-icon>
              Experimental Evidence
            </v-card-title>
            <v-card-text>
              <div class="d-flex align-center justify-space-between mb-2">
                <span class="text-h4 font-weight-bold">{{ experimentalScore.toFixed(2) }}</span>
                <span class="text-caption">/ 6 points</span>
              </div>
              <v-progress-linear
                :model-value="(experimentalScore / 6) * 100"
                color="secondary"
                height="8"
                rounded
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Detailed Category Breakdown -->
      <v-expansion-panels variant="accordion">
        <!-- Genetic Categories -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start>mdi-dna</v-icon>
            Genetic Evidence Categories
            <v-spacer />
            <v-chip size="small" color="primary"> {{ geneticScore.toFixed(2) }} points </v-chip>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-list density="compact">
              <!-- Case-Level -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="primary">mdi-account-multiple</v-icon>
                </template>
                <v-list-item-title>Case-Level Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 12 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="primary">
                    {{ caseLevelScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Segregation -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="primary">mdi-family-tree</v-icon>
                </template>
                <v-list-item-title>Segregation Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 7 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="primary">
                    {{ segregationScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Case-Control -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="primary">mdi-chart-scatter-plot</v-icon>
                </template>
                <v-list-item-title>Case-Control Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 6 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="primary">
                    {{ caseControlScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- Experimental Categories -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start>mdi-flask</v-icon>
            Experimental Evidence Categories
            <v-spacer />
            <v-chip size="small" color="secondary">
              {{ experimentalScore.toFixed(2) }} points
            </v-chip>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-list density="compact">
              <!-- Expression -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="secondary">mdi-dna</v-icon>
                </template>
                <v-list-item-title>Expression Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 2 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="secondary">
                    {{ expressionScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Protein Function -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="secondary">mdi-protein</v-icon>
                </template>
                <v-list-item-title>Protein Function Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 2 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="secondary">
                    {{ functionScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Models -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="secondary">mdi-cube</v-icon>
                </template>
                <v-list-item-title>Model Systems Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 4 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="secondary">
                    {{ modelsScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Rescue -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="secondary">mdi-ambulance</v-icon>
                </template>
                <v-list-item-title>Rescue Evidence</v-list-item-title>
                <v-list-item-subtitle>Maximum 2 points</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="secondary">
                    {{ rescueScore.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Additional Info -->
      <v-alert
        v-if="!isSufficientEvidence"
        type="info"
        variant="tonal"
        class="mt-4"
        density="compact"
      >
        <div class="text-caption">
          This curation currently has insufficient evidence for classification. Add more evidence
          items to reach at least 0.1 points.
        </div>
      </v-alert>

      <v-alert
        v-else-if="classification === 'Definitive'"
        type="success"
        variant="tonal"
        class="mt-4"
        density="compact"
      >
        <div class="text-caption">
          <v-icon start size="small">mdi-check-circle</v-icon>
          <strong>Definitive classification achieved!</strong> This gene-disease association has
          strong evidence supporting pathogenicity.
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup>
  /**
   * ClinGenScoreCard Component
   *
   * Displays detailed ClinGen SOP v11 score breakdown with visual indicators.
   * Used in curation forms and curation detail views.
   *
   * Features:
   * - Total score with progress bar
   * - Classification badge with color coding
   * - Genetic vs Experimental score breakdown
   * - Expandable category details
   * - Scoring guidance
   *
   * @example
   * <ClinGenScoreCard :breakdown="scoreBreakdown" />
   */

  import { computed } from 'vue'

  const props = defineProps({
    breakdown: {
      type: Object,
      required: true,
      validator: obj => {
        return (
          typeof obj === 'object' &&
          typeof obj.total_score === 'number' &&
          typeof obj.classification === 'string'
        )
      }
    }
  })

  // Computed scores
  const totalScore = computed(() => props.breakdown.total_score || 0)
  const geneticScore = computed(() => props.breakdown.genetic_total || 0)
  const experimentalScore = computed(() => props.breakdown.experimental_total || 0)
  const classification = computed(
    () => props.breakdown.classification || 'No Known Disease Relationship'
  )

  // Genetic category scores
  const caseLevelScore = computed(() => Math.min(props.breakdown.case_level_score || 0, 12))
  const segregationScore = computed(() => Math.min(props.breakdown.segregation_score || 0, 7))
  const caseControlScore = computed(() => Math.min(props.breakdown.case_control_score || 0, 6))

  // Experimental category scores
  const expressionScore = computed(() => Math.min(props.breakdown.expression_score || 0, 2))
  const functionScore = computed(() => Math.min(props.breakdown.function_score || 0, 2))
  const modelsScore = computed(() => Math.min(props.breakdown.models_score || 0, 4))
  const rescueScore = computed(() => Math.min(props.breakdown.rescue_score || 0, 2))

  // Classification color
  const classificationColor = computed(() => {
    const cls = classification.value
    if (cls === 'Definitive') return 'rgb(var(--v-theme-success))'
    if (cls === 'Strong') return 'rgb(var(--v-theme-info))'
    if (cls === 'Moderate') return 'rgb(var(--v-theme-warning))'
    if (cls === 'Limited') return 'rgb(var(--v-theme-grey))'
    return 'rgb(var(--v-theme-error))'
  })

  // Progress percentage (normalized to 18 points = 100%)
  const progressPercentage = computed(() => {
    return Math.min((totalScore.value / 18) * 100, 100)
  })

  // Check if evidence is sufficient
  const isSufficientEvidence = computed(() => {
    return totalScore.value >= 0.1
  })
</script>

<style scoped>
  /* Score display */
  .text-h1 {
    font-size: 4rem !important;
    font-weight: 700;
    line-height: 1;
  }

  /* Category cards */
  .v-card--variant-outlined {
    border-width: 2px;
  }

  /* Progress bars */
  :deep(.v-progress-linear__determinate) {
    transition: width 0.3s ease;
  }

  /* Expansion panels */
  .v-expansion-panels {
    background: transparent;
  }
</style>
