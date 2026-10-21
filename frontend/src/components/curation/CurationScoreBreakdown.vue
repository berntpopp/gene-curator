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
          <div class="text-body-large font-weight-medium mb-3">
            <v-icon start color="primary">mdi-dna</v-icon>
            Genetic Evidence
            <v-chip size="small" class="ml-2" color="primary" variant="tonal">
              {{ scores.genetic.toFixed(2) }}{{ capNote(scores.caps.genetic) }}
            </v-chip>
          </div>
          <v-table density="compact">
            <tbody>
              <tr>
                <td>Case-Level (AD/XL Null)</td>
                <td class="text-right">{{ fmt(scores.caseLevel.adxlNull) }}</td>
              </tr>
              <tr>
                <td>Case-Level (AD/XL Other)</td>
                <td class="text-right">{{ fmt(scores.caseLevel.adxlOther) }}</td>
              </tr>
              <tr>
                <td>Case-Level (AR Null)</td>
                <td class="text-right">{{ fmt(scores.caseLevel.arNull) }}</td>
              </tr>
              <tr>
                <td>Case-Level (AR Other)</td>
                <td class="text-right">{{ fmt(scores.caseLevel.arOther) }}</td>
              </tr>
              <tr>
                <td>Segregation</td>
                <td class="text-right">{{ fmt(scores.segregation) }}</td>
              </tr>
              <tr>
                <td>Case-Control</td>
                <td class="text-right">{{ fmt(scores.caseControl) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>

        <!-- Experimental Evidence -->
        <v-col cols="12" md="6">
          <div class="text-body-large font-weight-medium mb-3">
            <v-icon start>mdi-flask</v-icon>
            Experimental Evidence
            <v-chip size="small" class="ml-2" variant="tonal">
              {{ scores.experimental.toFixed(2) }}{{ capNote(scores.caps.experimental) }}
            </v-chip>
          </div>
          <v-table density="compact">
            <tbody>
              <tr>
                <td>Biochemical Function</td>
                <td class="text-right">{{ fmt(scores.function.biochemical) }}</td>
              </tr>
              <tr>
                <td>Protein Interaction</td>
                <td class="text-right">
                  {{ fmt(scores.function.proteinInteraction) }}
                </td>
              </tr>
              <tr>
                <td>Expression</td>
                <td class="text-right">{{ fmt(scores.function.expression) }}</td>
              </tr>
              <tr>
                <td>Functional Alteration</td>
                <td class="text-right">{{ fmt(scores.functionalAlteration) }}</td>
              </tr>
              <tr>
                <td>Models</td>
                <td class="text-right">{{ fmt(scores.models) }}</td>
              </tr>
              <tr>
                <td>Rescue</td>
                <td class="text-right">{{ fmt(scores.rescue) }}</td>
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

  const props = defineProps<{ scores: EvidenceScores }>()
  // Legacy rows have no stored trace: show unknown, not zero
  const fmt = (n: number) => (props.scores.traced ? n.toFixed(2) : '—')
  const capNote = (cap: number | null) => (cap == null ? '' : ` / ${cap}`)
</script>
