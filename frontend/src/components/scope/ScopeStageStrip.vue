<template>
  <div role="group" aria-label="Genes by stage" class="stage-strip">
    <button
      v-for="s in GENE_STAGES"
      :key="s.value"
      type="button"
      class="stage-strip__cell"
      :class="{ 'stage-strip__cell--active': modelValue === s.value }"
      :aria-pressed="modelValue === s.value"
      :data-testid="`stage-${s.value}`"
      @click="emit('update:modelValue', modelValue === s.value ? undefined : s.value)"
    >
      <span class="stage-strip__label">{{ s.title }}</span>
      <span class="stage-strip__count">{{ counts[s.value] }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
  /** Gene counts per pipeline stage; a click filters the table to that stage, a second click clears. */
  import { GENE_STAGES, type GeneStage } from '@/components/gene/geneStage'

  defineProps<{ counts: Record<GeneStage, number>; modelValue?: string }>()
  const emit = defineEmits<{ 'update:modelValue': [GeneStage | undefined] }>()
</script>

<style scoped>
  .stage-strip {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-radius: 6px;
    overflow: hidden;
  }

  .stage-strip__cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 14px;
    text-align: left;
    color: inherit;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-left: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
  }

  .stage-strip__cell:first-child {
    border-left: 0;
  }

  .stage-strip__cell:focus-visible {
    outline: 2px solid rgb(var(--v-theme-secondary));
    outline-offset: -2px;
  }

  .stage-strip__cell--active {
    background: rgba(var(--v-theme-secondary), 0.12);
  }

  .stage-strip__label {
    font-size: 12px;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .stage-strip__count {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px;
    font-variant-numeric: tabular-nums;
  }

  @media (max-width: 600px) {
    .stage-strip {
      grid-template-columns: repeat(2, 1fr);
    }

    .stage-strip__cell:nth-child(odd) {
      border-left: 0;
    }
  }
</style>
