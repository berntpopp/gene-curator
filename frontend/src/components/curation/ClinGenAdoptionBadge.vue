<template>
  <v-chip
    v-if="permalink"
    :href="permalink"
    target="_blank"
    rel="noopener"
    class="mt-1 ml-1"
    size="small"
    color="info"
    variant="tonal"
    :title="title"
  >
    <v-icon start size="small">mdi-link-variant</v-icon>
    Adopted from ClinGen
    <v-icon end size="x-small">mdi-open-in-new</v-icon>
  </v-chip>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  // The adopted ClinGen record (#105), stored verbatim from GeneFoundry
  const props = defineProps<{ adoption?: { [key: string]: unknown } | null }>()
  const permalink = computed(() => {
    const link = props.adoption?.permalink
    return typeof link === 'string' && link.startsWith('https://') ? link : null
  })
  const title = computed(() =>
    [props.adoption?.classification, props.adoption?.expert_panel].filter(Boolean).join(' · ')
  )
</script>
