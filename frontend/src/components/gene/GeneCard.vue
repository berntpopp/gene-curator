<template>
  <v-card hover>
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-dna" class="mr-2" />
      <a href="#" class="text-decoration-none gene-link" @click.prevent="emit('view', gene)">
        {{ gene.gene_symbol }}
      </a>
      <v-spacer />
      <v-chip :color="getStatusColor(gene.status)" size="small">
        {{ getStatusLabel(gene.status) }}
      </v-chip>
    </v-card-title>

    <v-card-subtitle v-if="gene.gene_hgnc_id">
      {{ gene.gene_hgnc_id }}
    </v-card-subtitle>

    <v-card-text>
      <!-- Curator -->
      <div class="d-flex align-center mb-2">
        <v-icon icon="mdi-account" size="small" class="mr-2" />
        <span class="text-caption">
          {{ gene.curator_name || 'Unassigned' }}
        </span>
      </div>

      <!-- Priority -->
      <div class="d-flex align-center mb-2">
        <v-icon :icon="getPriorityIcon(gene.priority)" size="small" class="mr-2" />
        <v-chip :color="getPriorityColor(gene.priority)" size="x-small" variant="tonal">
          {{ getPriorityLabel(gene.priority) }}
        </v-chip>
      </div>

      <!-- Progress -->
      <div class="mb-2">
        <div class="text-caption mb-1">Progress</div>
        <v-progress-linear
          :model-value="gene.progress || 0"
          :color="getProgressColor(gene.progress)"
          height="12"
          rounded
        >
          <strong>{{ gene.progress || 0 }}%</strong>
        </v-progress-linear>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-btn size="small" variant="text" @click="emit('view', gene)">
        <v-icon start>mdi-eye</v-icon>
        View
      </v-btn>
      <v-spacer />
      <!-- Workflow-aware action button -->
      <v-btn
        v-if="!hasPrecuration(gene)"
        size="small"
        color="primary"
        variant="tonal"
        :disabled="!!startBlockedReason"
        @click="emit('start-precuration', gene)"
      >
        <v-icon start>mdi-clipboard-text</v-icon>
        Start Precuration
      </v-btn>
      <v-btn
        v-else-if="hasPrecuration(gene) && !isPrecurationApproved(gene)"
        size="small"
        color="warning"
        variant="tonal"
        :disabled="!!startBlockedReason"
        @click="emit('complete-precuration', gene)"
      >
        <v-icon start>mdi-clipboard-check</v-icon>
        Complete Precuration
      </v-btn>
      <v-btn
        v-else-if="isPrecurationApproved(gene)"
        size="small"
        color="success"
        variant="tonal"
        :disabled="!!startBlockedReason"
        @click="emit('start-curation', gene)"
      >
        <v-icon start>mdi-pencil</v-icon>
        Start Curation
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
  /**
   * One gene as a card in the GeneList card view.
   */
  import type { GeneRow } from './types'
  import type { GeneWorkflowStatus } from './useGeneWorkflowStatus'
  import {
    getPriorityColor,
    getPriorityIcon,
    getPriorityLabel,
    getProgressColor,
    getStatusColor,
    getStatusLabel
  } from './geneDisplay'

  const props = defineProps<{
    gene: GeneRow
    workflow: GeneWorkflowStatus
    /** Why starting precuration/curation is unavailable (no methodology), if it is. */
    startBlockedReason?: string | null
  }>()

  const emit = defineEmits<{
    view: [gene: GeneRow]
    'start-precuration': [gene: GeneRow]
    'complete-precuration': [gene: GeneRow]
    'start-curation': [gene: GeneRow]
  }>()

  const { hasPrecuration, isPrecurationApproved } = props.workflow
</script>
