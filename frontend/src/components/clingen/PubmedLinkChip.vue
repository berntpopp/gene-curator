<template>
  <v-chip size="small" variant="outlined" :href="pubmedUrl" target="_blank">
    PMID: {{ pmid }}
    <v-icon end size="x-small">mdi-open-in-new</v-icon>
  </v-chip>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  // Separate component: a dynamic href on v-chip inside a v-for breaks vue-tsc scope checking.
  const props = defineProps<{ pmid: string }>()

  const pubmedUrl = computed(() => `https://pubmed.ncbi.nlm.nih.gov/${props.pmid}`)
</script>
