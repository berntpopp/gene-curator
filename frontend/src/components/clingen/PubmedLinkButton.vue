<template>
  <v-btn
    v-if="pubmedUrl"
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

  // Only a numeric PMID is a link ("PMID: 123" is read as 123); anything else would be a bad URL
  const pubmedUrl = computed(() => {
    const id = String(props.pmid ?? '')
      .trim()
      .replace(/^PMID:?\s*/i, '')
    return /^\d{1,9}$/.test(id) ? `https://pubmed.ncbi.nlm.nih.gov/${id}` : undefined
  })
</script>
