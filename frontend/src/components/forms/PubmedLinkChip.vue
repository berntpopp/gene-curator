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

  // Not a numeric PMID: still shown, but not a link ("PMID: 123" is read as 123)
  const pubmedUrl = computed(() => {
    const id = String(props.pmid)
      .trim()
      .replace(/^PMID:?\s*/i, '')
    return /^\d{1,9}$/.test(id) ? `https://pubmed.ncbi.nlm.nih.gov/${id}` : undefined
  })
</script>
