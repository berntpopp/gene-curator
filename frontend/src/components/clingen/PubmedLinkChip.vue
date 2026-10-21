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

  // Not a numeric PMID: still shown, but not a link
  const pubmedUrl = computed(() =>
    /^\d{1,9}$/.test(String(props.pmid).trim())
      ? `https://pubmed.ncbi.nlm.nih.gov/${String(props.pmid).trim()}`
      : undefined
  )
</script>
