<template>
  <div class="summary-section">
    <!-- Classification Overview -->
    <v-card class="mb-4" variant="tonal" :color="classificationColor">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="6">
            <div class="text-h4 font-weight-bold">{{ classification }}</div>
            <div class="text-body-2 mt-1">Gene-Disease Validity Classification</div>
          </v-col>
          <v-col cols="12" md="6" class="text-md-right">
            <div class="d-flex align-center justify-md-end ga-4">
              <div class="text-center">
                <div class="text-h5 font-weight-bold">{{ geneticScore.toFixed(1) }}</div>
                <div class="text-caption">Genetic</div>
              </div>
              <v-icon size="24">mdi-plus</v-icon>
              <div class="text-center">
                <div class="text-h5 font-weight-bold">{{ experimentalScore.toFixed(1) }}</div>
                <div class="text-caption">Experimental</div>
              </div>
              <v-icon size="24">mdi-equal</v-icon>
              <div class="text-center">
                <div class="text-h4 font-weight-bold">{{ totalScore.toFixed(1) }}</div>
                <div class="text-caption">Total</div>
              </div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Score Summary Table (ClinGen Style) -->
    <v-card class="mb-4" variant="outlined">
      <v-card-title class="text-subtitle-1">
        <v-icon start size="small">mdi-table</v-icon>
        Evidence Score Summary
      </v-card-title>
      <v-card-text class="pa-0">
        <v-table density="compact">
          <thead>
            <tr class="bg-grey-lighten-4">
              <th class="text-left">Evidence Type</th>
              <th class="text-center">Points (default)</th>
              <th class="text-center">Range</th>
              <th class="text-center">Max</th>
              <th class="text-center">Counted</th>
            </tr>
          </thead>
          <tbody>
            <!-- Genetic Evidence Section -->
            <tr class="section-header">
              <td colspan="5" class="font-weight-bold bg-primary text-white">
                <v-icon size="small" color="white" class="mr-2">mdi-dna</v-icon>
                Genetic Evidence (Max 12)
              </td>
            </tr>

            <!-- Case-Level -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">Case-Level Data</td>
            </tr>
            <tr>
              <td class="pl-8">Variant detected - proband (AD/XL): Predicted null</td>
              <td class="text-center">1.5</td>
              <td class="text-center">0-3</td>
              <td class="text-center" rowspan="2">12</td>
              <td class="text-center" rowspan="4">{{ geneticScore.toFixed(2) }}</td>
            </tr>
            <tr>
              <td class="pl-8">Variant detected - proband (AD/XL): Other variant type</td>
              <td class="text-center">0.1</td>
              <td class="text-center">0-1.5</td>
            </tr>
            <tr>
              <td class="pl-8">Variant detected - proband (AR): Predicted null</td>
              <td class="text-center">1.5</td>
              <td class="text-center">0-3</td>
              <td class="text-center" rowspan="2">12</td>
            </tr>
            <tr>
              <td class="pl-8">Variant detected - proband (AR): Other variant type</td>
              <td class="text-center">0.1</td>
              <td class="text-center">0-1.5</td>
            </tr>

            <!-- Segregation -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">Segregation Evidence</td>
            </tr>
            <tr>
              <td class="pl-8">Segregation (LOD score-based)</td>
              <td class="text-center">varies</td>
              <td class="text-center">0-3</td>
              <td class="text-center">3</td>
              <td class="text-center">-</td>
            </tr>

            <!-- Case-Control -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">Case-Control Data</td>
            </tr>
            <tr>
              <td class="pl-8">Single Variant Analysis</td>
              <td class="text-center">-</td>
              <td class="text-center">0-6</td>
              <td class="text-center" rowspan="2">6</td>
              <td class="text-center" rowspan="2">-</td>
            </tr>
            <tr>
              <td class="pl-8">Aggregate Variant Analysis</td>
              <td class="text-center">-</td>
              <td class="text-center">0-6</td>
            </tr>

            <!-- Experimental Evidence Section -->
            <tr class="section-header">
              <td colspan="5" class="font-weight-bold bg-secondary text-white">
                <v-icon size="small" color="white" class="mr-2">mdi-flask</v-icon>
                Experimental Evidence (Max 6)
              </td>
            </tr>

            <!-- Function -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">Function</td>
            </tr>
            <tr>
              <td class="pl-8">Biochemical Function</td>
              <td class="text-center">0.5</td>
              <td class="text-center">0-2</td>
              <td class="text-center" rowspan="3">2</td>
              <td class="text-center" rowspan="12">{{ experimentalScore.toFixed(2) }}</td>
            </tr>
            <tr>
              <td class="pl-8">Protein Interaction</td>
              <td class="text-center">0.5</td>
              <td class="text-center">0-2</td>
            </tr>
            <tr>
              <td class="pl-8">Expression</td>
              <td class="text-center">0.5</td>
              <td class="text-center">0-2</td>
            </tr>

            <!-- Functional Alteration -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">
                Functional Alteration
              </td>
            </tr>
            <tr>
              <td class="pl-8">Patient Cells</td>
              <td class="text-center">1</td>
              <td class="text-center">0-2</td>
              <td class="text-center" rowspan="2">2</td>
            </tr>
            <tr>
              <td class="pl-8">Non-patient Cells</td>
              <td class="text-center">0.5</td>
              <td class="text-center">0-1</td>
            </tr>

            <!-- Models -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">Models</td>
            </tr>
            <tr>
              <td class="pl-8">Non-human Model Organism</td>
              <td class="text-center">2</td>
              <td class="text-center">0-4</td>
              <td class="text-center" rowspan="2">4</td>
            </tr>
            <tr>
              <td class="pl-8">Cell Culture Model</td>
              <td class="text-center">1</td>
              <td class="text-center">0-2</td>
            </tr>

            <!-- Rescue -->
            <tr class="category-header">
              <td colspan="5" class="font-weight-medium bg-grey-lighten-3">Rescue</td>
            </tr>
            <tr>
              <td class="pl-8">Human</td>
              <td class="text-center">2</td>
              <td class="text-center">0-4</td>
              <td class="text-center" rowspan="4">4</td>
            </tr>
            <tr>
              <td class="pl-8">Non-human Model Organism</td>
              <td class="text-center">2</td>
              <td class="text-center">0-4</td>
            </tr>
            <tr>
              <td class="pl-8">Cell Culture</td>
              <td class="text-center">1</td>
              <td class="text-center">0-2</td>
              <td></td>
            </tr>
            <tr>
              <td class="pl-8">Patient Cells</td>
              <td class="text-center">1</td>
              <td class="text-center">0-2</td>
              <td></td>
            </tr>

            <!-- Total -->
            <tr class="total-row">
              <td colspan="3" class="font-weight-bold text-right">Total Score</td>
              <td class="text-center font-weight-bold">18</td>
              <td class="text-center font-weight-bold text-h6">{{ totalScore.toFixed(2) }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <!-- Evidence Summary Text -->
    <v-card variant="outlined">
      <v-card-title class="text-subtitle-1">
        <v-icon start size="small">mdi-text</v-icon>
        Evidence Summary
      </v-card-title>
      <v-card-text>
        <v-textarea
          v-model="summaryText"
          label="Narrative summary of evidence"
          placeholder="Enter a summary of the key evidence supporting this gene-disease relationship..."
          rows="4"
          variant="outlined"
          hide-details="auto"
          @update:model-value="$emit('update:evidence-summary', $event)"
        />
        <div class="text-caption text-medium-emphasis mt-2">
          Provide a brief narrative explaining the overall evidence and classification rationale.
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
  /**
   * SummarySection
   *
   * Overview tab content showing score summary table and evidence narrative.
   * Matches ClinGen Gene Validity Summary page structure.
   */

  import { ref, computed, watch } from 'vue'

  const props = defineProps({
    evidenceSummary: {
      type: String,
      default: ''
    },
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
    }
  })

  defineEmits(['update:evidence-summary'])

  const summaryText = ref(props.evidenceSummary)

  watch(
    () => props.evidenceSummary,
    newVal => {
      summaryText.value = newVal
    }
  )

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
</script>

<style scoped>
  .section-header td {
    font-size: 0.9rem;
  }

  .category-header td {
    font-size: 0.85rem;
  }

  .total-row {
    background: rgba(var(--v-theme-primary), 0.1);
  }

  .total-row td {
    border-top: 2px solid rgba(var(--v-border-color), 0.8);
  }
</style>
