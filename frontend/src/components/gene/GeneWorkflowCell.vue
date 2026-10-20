<template>
  <!-- Active/Completed curation -->
  <v-chip v-if="isCurationActive(gene)" size="small" color="success" variant="elevated">
    <v-icon start size="small">mdi-check-decagram</v-icon>
    Active
  </v-chip>
  <!-- Curation awaiting review -->
  <v-chip
    v-else-if="hasCuration(gene) && getCuration(gene)?.status === 'submitted'"
    size="small"
    color="info"
    variant="tonal"
  >
    <v-icon start size="small">mdi-eye-check</v-icon>
    Awaiting Review
  </v-chip>
  <!-- Curation in progress -->
  <v-chip
    v-else-if="hasCuration(gene) && getCuration(gene)?.status === 'draft'"
    size="small"
    color="warning"
    variant="tonal"
  >
    <v-icon start size="small">mdi-pencil</v-icon>
    Curation In Progress
  </v-chip>
  <!-- Ready for curation (precuration approved) -->
  <v-chip v-else-if="isPrecurationApproved(gene)" size="small" color="success" variant="tonal">
    <v-icon start size="small">mdi-check-circle</v-icon>
    Ready for Curation
  </v-chip>
  <!-- Precuration in progress -->
  <v-chip v-else-if="hasPrecuration(gene)" size="small" color="warning" variant="tonal">
    <v-icon start size="small">mdi-clipboard-text</v-icon>
    {{ getPrecurationStatusLabel(gene) }}
  </v-chip>
  <!-- No precuration -->
  <v-chip v-else size="small" variant="outlined" color="grey">
    <v-icon start size="small">mdi-clipboard-outline</v-icon>
    No Precuration
  </v-chip>
</template>

<script setup lang="ts">
  /** Workflow status chip of one gene row (precuration / curation progress). */
  import type { GeneRow } from './types'
  import type { GeneWorkflowStatus } from './useGeneWorkflowStatus'

  const props = defineProps<{ gene: GeneRow; workflow: GeneWorkflowStatus }>()

  const {
    hasPrecuration,
    isPrecurationApproved,
    hasCuration,
    getCuration,
    isCurationActive,
    getPrecurationStatusLabel
  } = props.workflow
</script>
