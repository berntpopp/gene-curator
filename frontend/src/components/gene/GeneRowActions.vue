<template>
  <v-menu>
    <template #activator="{ props: menuProps }">
      <v-btn v-bind="menuProps" icon variant="text" size="small" aria-label="Gene actions">
        <v-icon>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>
    <v-list density="compact">
      <v-list-item v-if="!hasPrecuration(gene)" @click="emit('start-precuration', gene)">
        <template #prepend>
          <v-icon>mdi-clipboard-text</v-icon>
        </template>
        <v-list-item-title>Start Precuration</v-list-item-title>
      </v-list-item>
      <v-list-item
        v-else-if="hasPrecuration(gene) && !isPrecurationApproved(gene)"
        @click="emit('complete-precuration', gene)"
      >
        <template #prepend>
          <v-icon>mdi-clipboard-check</v-icon>
        </template>
        <v-list-item-title>Complete Precuration</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="hasCuration(gene)" @click="emit('view-curation', gene)">
        <template #prepend>
          <v-icon>mdi-file-document</v-icon>
        </template>
        <v-list-item-title> View Curation ({{ getCurationStatusLabel(gene) }}) </v-list-item-title>
      </v-list-item>
      <v-list-item v-else-if="isPrecurationApproved(gene)" @click="emit('start-curation', gene)">
        <template #prepend>
          <v-icon>mdi-pencil</v-icon>
        </template>
        <v-list-item-title>Start Curation</v-list-item-title>
      </v-list-item>
      <v-list-item v-else disabled>
        <template #prepend>
          <v-icon>mdi-pencil</v-icon>
        </template>
        <v-list-item-title> Curation (requires approved precuration) </v-list-item-title>
      </v-list-item>
      <v-divider />
      <v-list-item v-if="canAssignGenes" @click="emit('reassign', gene)">
        <template #prepend>
          <v-icon>mdi-account-switch</v-icon>
        </template>
        <v-list-item-title>Reassign</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="canAssignGenes" @click="emit('edit-assignment', gene)">
        <template #prepend>
          <v-icon>mdi-pencil-box</v-icon>
        </template>
        <v-list-item-title>Edit Assignment</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="canRemoveGenes" class="text-error" @click="emit('remove', gene)">
        <template #prepend>
          <v-icon color="error">mdi-delete</v-icon>
        </template>
        <v-list-item-title>Remove from Scope</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
  /**
   * Row action menu for one gene in the GeneList table.
   * Emits the chosen action; the parent owns navigation and modals.
   */
  import type { GeneRow } from './types'
  import type { GeneWorkflowStatus } from './useGeneWorkflowStatus'

  const props = defineProps<{
    gene: GeneRow
    workflow: GeneWorkflowStatus
    canAssignGenes: boolean
    canRemoveGenes: boolean
  }>()

  const emit = defineEmits<{
    'start-precuration': [gene: GeneRow]
    'complete-precuration': [gene: GeneRow]
    'view-curation': [gene: GeneRow]
    'start-curation': [gene: GeneRow]
    reassign: [gene: GeneRow]
    'edit-assignment': [gene: GeneRow]
    remove: [gene: GeneRow]
  }>()

  const { hasPrecuration, isPrecurationApproved, hasCuration, getCurationStatusLabel } =
    props.workflow
</script>
