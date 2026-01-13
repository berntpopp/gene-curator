<template>
  <v-card class="score-summary" variant="outlined">
    <v-card-title class="text-subtitle-1 pb-0">
      <v-icon start size="small">mdi-counter</v-icon>
      Score Summary
    </v-card-title>

    <v-card-text class="pt-2">
      <!-- Total Score Display -->
      <div class="text-center mb-4">
        <div class="score-circle" :class="classificationClass">
          <div class="score-value">{{ totalScore.toFixed(1) }}</div>
          <div class="score-max">/ 18</div>
        </div>
        <v-chip :color="classificationColor" size="small" class="mt-2">
          {{ classification }}
        </v-chip>
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
            <td colspan="3" class="font-weight-bold text-secondary">
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
            <td class="text-right font-weight-bold text-h6">{{ totalScore.toFixed(2) }}</td>
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
          <v-expansion-panel-title class="text-caption">
            Classification Thresholds
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="d-flex flex-column ga-1 text-caption">
              <div class="d-flex justify-space-between">
                <span><v-chip size="x-small" color="success">Definitive</v-chip></span>
                <span>12+ points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><v-chip size="x-small" color="info">Strong</v-chip></span>
                <span>7-11.99 points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><v-chip size="x-small" color="warning">Moderate</v-chip></span>
                <span>2-6.99 points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span><v-chip size="x-small" color="grey">Limited</v-chip></span>
                <span>0.1-1.99 points</span>
              </div>
              <div class="d-flex justify-space-between">
                <span
                  ><v-chip size="x-small" color="grey" variant="outlined">No Known</v-chip></span
                >
                <span>0 points</span>
              </div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup>
  /**
   * ScoreSummary
   *
   * Displays live scoring summary in sidebar with breakdown by category.
   * Matches ClinGen Gene Validity scoring framework structure.
   */

  import { computed } from 'vue'

  const props = defineProps({
    geneticScore: {
      type: Number,
      default: 0
    },
    experimentalScore: {
      type: Number,
      default: 0
    },
    totalScore: {
      type: Number,
      default: 0
    },
    classification: {
      type: String,
      default: 'No Known Disease Relationship'
    },
    hasContradictory: {
      type: Boolean,
      default: false
    },
    geneticBreakdown: {
      type: Object,
      default: () => ({
        caseLevel: 0,
        segregation: 0,
        caseControl: 0
      })
    },
    experimentalBreakdown: {
      type: Object,
      default: () => ({
        function: 0,
        functionalAlteration: 0,
        models: 0,
        rescue: 0
      })
    }
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
    transition: all 0.3s ease;
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
