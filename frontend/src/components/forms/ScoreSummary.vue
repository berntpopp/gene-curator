<template>
  <v-card class="score-summary" variant="outlined">
    <v-card-title class="text-body-large pb-0">
      <v-icon start size="small">mdi-counter</v-icon>
      Score summary
    </v-card-title>

    <v-card-text class="pt-2">
      <!-- Total Score Display -->
      <div class="text-center mb-4">
        <div class="score-circle" :class="classificationClass">
          <div class="score-value">{{ totalScore.toFixed(1) }}</div>
          <div class="score-max">/ 18</div>
        </div>
        <ClassificationMark :classification="classification" class="mt-2" />
      </div>

      <v-divider class="mb-3" />

      <!-- Score Breakdown Table -->
      <v-table density="compact" class="score-breakdown-table">
        <thead>
          <tr>
            <th class="text-left">Category</th>
            <th class="text-right">Counted</th>
            <th class="text-right">Max</th>
          </tr>
        </thead>
        <tbody>
          <!-- Genetic Evidence Header -->
          <tr class="category-header">
            <td colspan="3" class="font-weight-bold text-primary">
              <v-icon size="small" class="mr-1">mdi-dna</v-icon>
              Genetic Evidence
            </td>
          </tr>
          <tr>
            <td class="pl-6">Case-Level</td>
            <td class="text-right">{{ geneticBreakdown?.caseLevel?.toFixed(2) || '0.00' }}</td>
            <td class="text-right text-medium-emphasis">12</td>
          </tr>
          <tr>
            <td class="pl-6">Segregation</td>
            <td class="text-right">{{ geneticBreakdown?.segregation?.toFixed(2) || '0.00' }}</td>
            <td class="text-right text-medium-emphasis">3</td>
          </tr>
          <tr>
            <td class="pl-6">Case-Control</td>
            <td class="text-right">{{ geneticBreakdown?.caseControl?.toFixed(2) || '0.00' }}</td>
            <td class="text-right text-medium-emphasis">6</td>
          </tr>
          <tr class="subtotal-row">
            <td class="pl-4 font-weight-medium">Subtotal</td>
            <td class="text-right font-weight-bold">{{ geneticScore.toFixed(2) }}</td>
            <td class="text-right font-weight-medium">12</td>
          </tr>

          <!-- Experimental Evidence Header -->
          <tr class="category-header">
            <td colspan="3" class="font-weight-bold text-primary">
              <v-icon size="small" class="mr-1">mdi-flask</v-icon>
              Experimental Evidence
            </td>
          </tr>
          <tr>
            <td class="pl-6">Function</td>
            <td class="text-right">{{ experimentalBreakdown?.function?.toFixed(2) || '0.00' }}</td>
            <td class="text-right text-medium-emphasis">2</td>
          </tr>
          <tr>
            <td class="pl-6">Functional Alteration</td>
            <td class="text-right">
              {{ experimentalBreakdown?.functionalAlteration?.toFixed(2) || '0.00' }}
            </td>
            <td class="text-right text-medium-emphasis">2</td>
          </tr>
          <tr>
            <td class="pl-6">Models</td>
            <td class="text-right">{{ experimentalBreakdown?.models?.toFixed(2) || '0.00' }}</td>
            <td class="text-right text-medium-emphasis">4</td>
          </tr>
          <tr>
            <td class="pl-6">Rescue</td>
            <td class="text-right">{{ experimentalBreakdown?.rescue?.toFixed(2) || '0.00' }}</td>
            <td class="text-right text-medium-emphasis">4</td>
          </tr>
          <tr class="subtotal-row">
            <td class="pl-4 font-weight-medium">Subtotal</td>
            <td class="text-right font-weight-bold">{{ experimentalScore.toFixed(2) }}</td>
            <td class="text-right font-weight-medium">6</td>
          </tr>

          <!-- Total Row -->
          <tr class="total-row">
            <td class="font-weight-bold">TOTAL</td>
            <td class="text-right font-weight-bold text-title-large">
              {{ totalScore.toFixed(2) }}
            </td>
            <td class="text-right font-weight-bold">18</td>
          </tr>
        </tbody>
      </v-table>

      <!-- Contradictory Evidence Warning -->
      <v-alert
        v-if="hasContradictory"
        type="warning"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        <template #prepend>
          <v-icon>mdi-alert</v-icon>
        </template>
        Contradictory evidence present - classification may be "Disputed"
      </v-alert>

      <!-- Classification Thresholds Reference -->
      <v-expansion-panels variant="accordion" class="mt-3">
        <v-expansion-panel>
          <v-expansion-panel-title class="text-body-small">
            Classification Thresholds
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="d-flex flex-column ga-1 text-body-small">
              <div class="d-flex justify-space-between">
                <span><ClassificationMark classification="definitive" /></span>
                <span>12-18 points + replication over time</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><ClassificationMark classification="strong" /></span>
                <span>12-18 points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><ClassificationMark classification="moderate" /></span>
                <span>7-11 points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><ClassificationMark classification="limited" /></span>
                <span>1-6 points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><ClassificationMark classification="no_known" /></span>
                <span>0 points</span>
              </div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  /**
   * ScoreSummary
   *
   * Displays the backend score preview with breakdown by category.
   * Matches ClinGen Gene Validity scoring framework structure.
   */

  import { computed } from 'vue'
  import type { ScoreSnapshot } from '@/components/workspace/useWorkspaceFrame'

  const props = withDefaults(
    defineProps<{
      geneticScore?: number
      experimentalScore?: number
      totalScore?: number
      classification?: string
      hasContradictory?: boolean
      geneticBreakdown?: Partial<NonNullable<ScoreSnapshot['geneticBreakdown']>>
      experimentalBreakdown?: Partial<NonNullable<ScoreSnapshot['experimentalBreakdown']>>
    }>(),
    {
      geneticScore: 0,
      experimentalScore: 0,
      totalScore: 0,
      classification: 'No Known Disease Relationship',
      hasContradictory: false,
      geneticBreakdown: () => ({
        caseLevel: 0,
        segregation: 0,
        caseControl: 0
      }),
      experimentalBreakdown: () => ({
        function: 0,
        functionalAlteration: 0,
        models: 0,
        rescue: 0
      })
    }
  )

  const classificationClass = computed(() => {
    const classification = props.classification?.toLowerCase() || ''
    return `score-${classification.replace(/\s+/g, '-')}`
  })
</script>

<style scoped>
  .score-summary {
    background: rgba(var(--v-theme-surface-variant), 0.3);
  }

  .score-circle {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    margin: 0 auto;
    border: 4px solid currentColor;
    transition:
      border-color,
      color,
      background-color 0.3s ease;
  }

  .score-value {
    font-size: 1.75rem;
    font-weight: bold;
    line-height: 1;
  }

  .score-max {
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .score-definitive {
    color: rgb(var(--v-theme-success));
    background: rgba(var(--v-theme-success), 0.1);
  }

  .score-strong {
    color: rgb(var(--v-theme-info));
    background: rgba(var(--v-theme-info), 0.1);
  }

  .score-moderate {
    color: rgb(var(--v-theme-warning));
    background: rgba(var(--v-theme-warning), 0.1);
  }

  .score-limited,
  .score-no-known-disease-relationship {
    color: rgb(var(--v-theme-grey));
    background: rgba(var(--v-theme-grey), 0.1);
  }

  .score-disputed,
  .score-refuted {
    color: rgb(var(--v-theme-error));
    background: rgba(var(--v-theme-error), 0.1);
  }

  .score-breakdown-table {
    font-size: 0.875rem;
  }

  .category-header td {
    padding-top: 12px !important;
    border-bottom: none !important;
  }

  .subtotal-row td {
    border-top: 1px solid rgba(var(--v-border-color), 0.5);
    background: rgba(var(--v-theme-surface-variant), 0.3);
  }

  .total-row td {
    border-top: 2px solid rgba(var(--v-border-color), 0.8);
    background: rgba(var(--v-theme-primary), 0.1);
  }
</style>
