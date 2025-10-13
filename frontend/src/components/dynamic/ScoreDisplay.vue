<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-calculator</v-icon>
      Evidence Scoring
      <v-spacer />
      <v-chip
        v-if="totalScore !== null"
        :color="getScoreColor(totalScore)"
        size="large"
        variant="flat"
      >
        Total: {{ totalScore.toFixed(2) }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
        <div class="mt-4">Calculating scores...</div>
      </div>

      <div v-else-if="scoreCalculations">
        <!-- Score Categories -->
        <v-row class="mb-6">
          <v-col
            v-for="(score, category) in scoreCalculations"
            :key="category"
            cols="12"
            sm="6"
            md="4"
          >
            <v-card variant="outlined" :class="{ 'border-primary': score.value > 0 }">
              <v-card-text class="text-center">
                <div class="text-h3 font-weight-bold" :class="getScoreTextClass(score.value)">
                  {{ score.value.toFixed(2) }}
                </div>
                <div class="text-subtitle-1 font-weight-medium mb-2">
                  {{ formatCategoryName(category) }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  Max: {{ score.max_possible || 'N/A' }}
                </div>

                <!-- Score Progress -->
                <v-progress-linear
                  v-if="score.max_possible"
                  :model-value="(score.value / score.max_possible) * 100"
                  :color="getScoreColor(score.value)"
                  class="mt-2"
                  height="6"
                  rounded
                />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Score Breakdown -->
        <v-expansion-panels class="mb-6">
          <v-expansion-panel v-for="(score, category) in scoreCalculations" :key="category">
            <v-expansion-panel-title>
              <div class="d-flex align-center">
                <v-icon :color="getScoreColor(score.value)" class="mr-3">
                  {{ getCategoryIcon(category) }}
                </v-icon>
                <div>
                  <div class="font-weight-medium">{{ formatCategoryName(category) }}</div>
                  <div class="text-caption">{{ score.breakdown?.length || 0 }} evidence items</div>
                </div>
                <v-spacer />
                <v-chip :color="getScoreColor(score.value)" size="small" variant="flat">
                  {{ score.value.toFixed(2) }}
                </v-chip>
              </div>
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <div v-if="score.breakdown?.length">
                <v-list density="compact">
                  <v-list-item
                    v-for="(item, index) in score.breakdown"
                    :key="index"
                    :class="{ 'bg-grey-lighten-5': index % 2 === 0 }"
                  >
                    <template #prepend>
                      <v-icon :color="item.points > 0 ? 'success' : 'grey'" size="small">
                        {{ item.points > 0 ? 'mdi-plus-circle' : 'mdi-circle-outline' }}
                      </v-icon>
                    </template>

                    <v-list-item-title>
                      {{ item.evidence_type || item.description }}
                    </v-list-item-title>

                    <v-list-item-subtitle v-if="item.rationale">
                      {{ item.rationale }}
                    </v-list-item-subtitle>

                    <template #append>
                      <v-chip
                        :color="item.points > 0 ? 'success' : 'grey'"
                        size="small"
                        variant="outlined"
                      >
                        {{ item.points > 0 ? '+' : '' }}{{ item.points.toFixed(2) }}
                      </v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </div>

              <div v-else class="text-center py-4 text-medium-emphasis">
                No evidence items in this category yet
              </div>

              <div v-if="score.notes" class="mt-4 pa-3 bg-blue-lighten-5 rounded">
                <div class="text-subtitle-2 mb-1">Scoring Notes</div>
                <div class="text-body-2">{{ score.notes }}</div>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Classification Result -->
        <v-card
          v-if="classification"
          variant="tonal"
          :color="getClassificationColor(classification.verdict)"
        >
          <v-card-title class="d-flex align-center">
            <v-icon start>{{ getClassificationIcon(classification.verdict) }}</v-icon>
            Gene-Disease Classification
          </v-card-title>
          <v-card-text>
            <div class="d-flex align-center mb-4">
              <div>
                <div class="text-h5 font-weight-bold">{{ classification.verdict }}</div>
                <div class="text-body-1">{{ classification.description }}</div>
              </div>
              <v-spacer />
              <v-chip
                :color="getClassificationColor(classification.verdict)"
                size="x-large"
                variant="flat"
              >
                {{ totalScore.toFixed(2) }} points
              </v-chip>
            </div>

            <div v-if="classification.rationale" class="mb-4">
              <div class="text-subtitle-2 mb-2">Classification Rationale</div>
              <div class="text-body-2">{{ classification.rationale }}</div>
            </div>

            <div v-if="classification.confidence_level">
              <div class="text-subtitle-2 mb-2">Confidence Level</div>
              <v-progress-linear
                :model-value="classification.confidence_score * 100"
                :color="getClassificationColor(classification.verdict)"
                height="8"
                rounded
              >
                <template #default>
                  <strong
                    >{{ classification.confidence_level }} ({{
                      (classification.confidence_score * 100).toFixed(0)
                    }}%)</strong
                  >
                </template>
              </v-progress-linear>
            </div>
          </v-card-text>
        </v-card>

        <!-- Contradictory Evidence -->
        <v-card v-if="contradictoryEvidence?.length" variant="outlined" class="mt-4 border-warning">
          <v-card-title class="d-flex align-center text-warning">
            <v-icon start>mdi-alert-triangle</v-icon>
            Contradictory Evidence
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="(item, index) in contradictoryEvidence" :key="index">
                <template #prepend>
                  <v-icon color="warning" size="small">mdi-minus-circle</v-icon>
                </template>

                <v-list-item-title>{{ item.evidence_type }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>

                <template #append>
                  <v-chip color="warning" size="small" variant="outlined">
                    -{{ item.impact.toFixed(2) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Scoring Engine Info -->
        <v-card variant="outlined" class="mt-4">
          <v-card-title class="text-subtitle-1">
            <v-icon start>mdi-cog</v-icon>
            Scoring Engine Details
          </v-card-title>
          <v-card-text>
            <v-row dense>
              <v-col cols="12" sm="6">
                <div class="text-caption text-medium-emphasis">Engine</div>
                <div class="text-body-2">{{ scoringEngine?.name || 'Unknown' }}</div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-caption text-medium-emphasis">Version</div>
                <div class="text-body-2">{{ scoringEngine?.version || 'Unknown' }}</div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-caption text-medium-emphasis">Last Updated</div>
                <div class="text-body-2">{{ formatDate(lastCalculated) }}</div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-caption text-medium-emphasis">Calculation Time</div>
                <div class="text-body-2">{{ calculationTime || 'N/A' }}ms</div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </div>

      <v-alert v-else-if="error" type="error" variant="tonal">
        <template #prepend>
          <v-icon>mdi-alert-circle</v-icon>
        </template>
        Failed to calculate scores: {{ error }}
      </v-alert>

      <v-alert v-else type="info" variant="tonal">
        <template #prepend>
          <v-icon>mdi-information</v-icon>
        </template>
        No scoring data available. Add evidence to see live scoring.
      </v-alert>
    </v-card-text>

    <v-card-actions v-if="scoreCalculations">
      <v-spacer />
      <v-btn variant="outlined" :loading="refreshing" @click="refreshScores">
        <v-icon start>mdi-refresh</v-icon>
        Recalculate
      </v-btn>
      <v-btn variant="outlined" :loading="exporting" @click="exportScores">
        <v-icon start>mdi-download</v-icon>
        Export
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, watch } from 'vue'
  import { useValidationStore } from '@/stores'

  const props = defineProps({
    evidenceData: {
      type: Object,
      required: true
    },
    schemaId: {
      type: String,
      required: true
    },
    autoRefresh: {
      type: Boolean,
      default: true
    }
  })

  const emit = defineEmits(['score-updated', 'classification-changed'])

  const validationStore = useValidationStore()
  const refreshing = ref(false)
  const exporting = ref(false)

  const loading = computed(() => validationStore.loading)
  const error = computed(() => validationStore.error)
  const validationResult = computed(() => validationStore.getValidationResult('scoring'))

  const scoreCalculations = computed(() => validationResult.value?.score_calculations)
  const classification = computed(() => validationResult.value?.classification)
  const contradictoryEvidence = computed(() => validationResult.value?.contradictory_evidence)
  const scoringEngine = computed(() => validationResult.value?.scoring_engine)
  const lastCalculated = computed(() => validationResult.value?.calculated_at)
  const calculationTime = computed(() => validationResult.value?.calculation_time_ms)

  const totalScore = computed(() => {
    if (!scoreCalculations.value) return null
    return Object.values(scoreCalculations.value).reduce((sum, score) => sum + score.value, 0)
  })

  const getScoreColor = score => {
    if (score >= 12) return 'success'
    if (score >= 7) return 'primary'
    if (score >= 3) return 'warning'
    return 'grey'
  }

  const getScoreTextClass = score => {
    if (score >= 12) return 'text-success'
    if (score >= 7) return 'text-primary'
    if (score >= 3) return 'text-warning'
    return 'text-medium-emphasis'
  }

  const getClassificationColor = verdict => {
    const colorMap = {
      Definitive: 'success',
      Strong: 'primary',
      Moderate: 'info',
      Limited: 'warning',
      'No Known Disease Relationship': 'grey',
      Disputed: 'orange',
      Refuted: 'error'
    }
    return colorMap[verdict] || 'grey'
  }

  const getClassificationIcon = verdict => {
    const iconMap = {
      Definitive: 'mdi-star',
      Strong: 'mdi-star-three-points',
      Moderate: 'mdi-star-half',
      Limited: 'mdi-star-outline',
      'No Known Disease Relationship': 'mdi-minus-circle',
      Disputed: 'mdi-help-circle',
      Refuted: 'mdi-close-circle'
    }
    return iconMap[verdict] || 'mdi-help-circle'
  }

  const getCategoryIcon = category => {
    const iconMap = {
      genetic_evidence: 'mdi-dna',
      experimental_evidence: 'mdi-flask',
      case_level: 'mdi-account-group',
      segregation: 'mdi-family-tree',
      case_control: 'mdi-chart-bar',
      functional: 'mdi-cog',
      model_systems: 'mdi-rat',
      rescue: 'mdi-medical-bag'
    }
    return iconMap[category] || 'mdi-file-document'
  }

  const formatCategoryName = category => {
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = dateString => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  const refreshScores = async () => {
    refreshing.value = true
    try {
      await validationStore.validateEvidence(props.evidenceData, props.schemaId, 'scoring')
      emit('score-updated', validationResult.value)
    } catch (error) {
      logger.error('Failed to refresh scores:', { error: error.message, stack: error.stack })
    } finally {
      refreshing.value = false
    }
  }

  const exportScores = async () => {
    exporting.value = true
    try {
      // Create export data
      const exportData = {
        total_score: totalScore.value,
        classification: classification.value,
        score_calculations: scoreCalculations.value,
        contradictory_evidence: contradictoryEvidence.value,
        scoring_engine: scoringEngine.value,
        calculated_at: lastCalculated.value
      }

      // Create and download file
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `evidence-scores-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      logger.error('Failed to export scores:', { error: error.message, stack: error.stack })
    } finally {
      exporting.value = false
    }
  }

  // Watch for evidence data changes and auto-refresh scores
  watch(
    () => props.evidenceData,
    async newData => {
      if (props.autoRefresh && newData && Object.keys(newData).length > 0) {
        try {
          await validationStore.validateEvidence(newData, props.schemaId, 'scoring')
          emit('score-updated', validationResult.value)

          if (classification.value) {
            emit('classification-changed', classification.value)
          }
        } catch (error) {
          logger.error('Auto-refresh scoring failed:', { error: error.message, stack: error.stack })
        }
      }
    },
    { deep: true }
  )
</script>

<style scoped>
  .border-primary {
    border-color: rgb(var(--v-theme-primary)) !important;
  }

  .border-warning {
    border-color: rgb(var(--v-theme-warning)) !important;
  }
</style>
