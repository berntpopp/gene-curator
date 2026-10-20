<template>
  <v-btn
    icon
    size="x-small"
    variant="text"
    :href="pubmedUrl"
    target="_blank"
    title="Open in PubMed"
  >
    <v-icon size="small">mdi-open-in-new</v-icon>
  </v-btn>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  // Separate component: a dynamic href on v-btn inside a v-for breaks vue-tsc scope checking.
  const props = defineProps<{ pmid: unknown }>()

  const pubmedUrl = computed(() => `https://pubmed.ncbi.nlm.nih.gov/${props.pmid}`)
</script>
