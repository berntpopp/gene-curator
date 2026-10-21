<template>
  <v-card>
    <v-card-title>
      <v-icon start>mdi-chart-bar</v-icon>
      Evidence score breakdown
    </v-card-title>
    <v-card-text>
      <v-row>
        <!-- Genetic Evidence -->
        <v-col cols="12" md="6">
          <div class="text-subtitle-1 font-weight-medium mb-3">
            <v-icon start color="primary">mdi-dna</v-icon>
            Genetic Evidence
            <v-chip size="small" class="ml-2" color="primary" variant="tonal">
              {{ scores.genetic.toFixed(2) }} / 12
            </v-chip>
          </div>
          <v-table density="compact">
            <tbody>
              <tr>
                <td>Case-Level (AD/XL Null)</td>
                <td class="text-right">{{ scores.caseLevel.adxlNull.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Case-Level (AD/XL Other)</td>
                <td class="text-right">{{ scores.caseLevel.adxlOther.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Case-Level (AR Null)</td>
                <td class="text-right">{{ scores.caseLevel.arNull.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Case-Level (AR Other)</td>
                <td class="text-right">{{ scores.caseLevel.arOther.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Segregation</td>
                <td class="text-right">{{ scores.segregation.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Case-Control</td>
                <td class="text-right">{{ scores.caseControl.toFixed(2) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>

        <!-- Experimental Evidence -->
        <v-col cols="12" md="6">
          <div class="text-subtitle-1 font-weight-medium mb-3">
            <v-icon start>mdi-flask</v-icon>
            Experimental Evidence
            <v-chip size="small" class="ml-2" variant="tonal">
              {{ scores.experimental.toFixed(2) }} / 6
            </v-chip>
          </div>
          <v-table density="compact">
            <tbody>
              <tr>
                <td>Biochemical Function</td>
                <td class="text-right">{{ scores.function.biochemical.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Protein Interaction</td>
                <td class="text-right">
                  {{ scores.function.proteinInteraction.toFixed(2) }}
                </td>
              </tr>
              <tr>
                <td>Expression</td>
                <td class="text-right">{{ scores.function.expression.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Functional Alteration</td>
                <td class="text-right">{{ scores.functionalAlteration.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Models</td>
                <td class="text-right">{{ scores.models.toFixed(2) }}</td>
              </tr>
              <tr>
                <td>Rescue</td>
                <td class="text-right">{{ scores.rescue.toFixed(2) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
  import type { EvidenceScores } from '@/views/curation/curationScores'

  defineProps<{ scores: EvidenceScores }>()
</script>
