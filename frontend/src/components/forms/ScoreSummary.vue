<template>
  <v-card variant="outlined"
    ><v-card-title>Score summary</v-card-title
    ><v-card-text><ScoreTrace :scores="scores" :classification="classification" /></v-card-text
  ></v-card>
</template>
<script setup lang="ts">
  import ScoreTrace from '@/components/curation/ScoreTrace.vue'
  import type { EvidenceScores } from '@/views/curation/curationScores'
  defineProps<{ scores: EvidenceScores; classification?: string }>()
</script>
