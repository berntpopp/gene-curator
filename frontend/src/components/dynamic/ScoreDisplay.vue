<template>
  <v-card variant="outlined">
    <v-card-title>Live scoring</v-card-title>
    <v-card-text>
      <v-skeleton-loader v-if="loading" type="article" />
      <ScoreTrace v-else :scores="scores" :classification="classification" />
    </v-card-text>
  </v-card>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import ScoreTrace from '@/components/curation/ScoreTrace.vue'
  import { storedScores, record } from '@/views/curation/curationScores'
  import type { ScoringConfiguration } from './types'
  const props = defineProps<{
    scoreCalculations?: Record<string, unknown> | null
    scoringConfiguration?: ScoringConfiguration | null
    loading?: boolean
  }>()
  const scores = computed(() => storedScores(props.scoreCalculations))
  const classification = computed(() => {
    const verdict = record(props.scoreCalculations)?.verdict
    return typeof verdict === 'string' ? verdict : ''
  })
</script>
