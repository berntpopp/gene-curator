<template>
  <div class="evidence-readonly">
    <v-card variant="tonal" class="mb-4">
      <v-card-title class="text-body-large">Evidence summary</v-card-title>
      <v-card-text class="evidence-summary">
        {{ evidence.evidence_summary || 'No evidence summary was written.' }}
      </v-card-text>
    </v-card>
    <GeneticEvidenceSection :model-value="genetic" :moi="moi" readonly />
    <ExperimentalEvidenceSection class="mt-4" :model-value="experimental" readonly />
    <h3 class="text-body-large mt-4 mb-2">Contradictory evidence</h3>
    <ContradictoryEvidenceSection :model-value="evidence.contradictory_evidence ?? []" readonly />
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import GeneticEvidenceSection from '@/components/clingen/sections/GeneticEvidenceSection.vue'
  import ExperimentalEvidenceSection from '@/components/clingen/sections/ExperimentalEvidenceSection.vue'
  import ContradictoryEvidenceSection from '@/components/clingen/sections/ContradictoryEvidenceSection.vue'
  import {
    createEmptyExperimentalEvidence,
    createEmptyGeneticEvidence
  } from '@/components/clingen/evidenceDefaults'
  import type { ClinGenEvidenceData } from '@/components/clingen/types'

  const props = defineProps<{ evidence: Partial<ClinGenEvidenceData>; moi?: string }>()

  const genetic = computed(() => props.evidence.genetic_evidence ?? createEmptyGeneticEvidence())
  const experimental = computed(
    () => props.evidence.experimental_evidence ?? createEmptyExperimentalEvidence()
  )
</script>

<style scoped>
  .evidence-summary {
    white-space: pre-wrap;
  }
</style>
