<template>
  <ol class="stage-line" aria-label="Workflow stage">
    <li
      v-for="s in steps"
      :key="s.key"
      :class="['stage', `stage--${s.state}`]"
      :aria-current="s.state === 'current' ? 'step' : undefined"
    >
      <span class="stage__dot" aria-hidden="true" />{{ s.label }}
    </li>
  </ol>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  const STAGES = [
    { key: 'precuration', label: 'Precuration' },
    { key: 'curation', label: 'Curation' },
    { key: 'review', label: 'Review' },
    { key: 'active', label: 'Active' }
  ]

  const props = defineProps<{ stage?: string | null; archived?: boolean }>()

  const steps = computed(() => {
    const all = props.archived ? [...STAGES, { key: 'archived', label: 'Archived' }] : STAGES
    const at = all.findIndex(s => s.key === (props.archived ? 'archived' : props.stage))
    return all.map((s, i) => ({
      ...s,
      state: at < 0 ? 'todo' : i < at ? 'done' : i === at ? 'current' : 'todo'
    }))
  })
</script>

<style scoped>
  .stage-line {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 13px;
  }

  .stage {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .stage__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1px solid currentColor;
    box-sizing: border-box;
  }

  .stage--done .stage__dot {
    background: rgb(var(--v-theme-primary));
    border-color: rgb(var(--v-theme-primary));
  }

  .stage--current {
    color: rgb(var(--v-theme-on-surface));
    font-weight: 600;
  }

  .stage--current .stage__dot {
    background: rgb(var(--v-theme-secondary));
    border-color: rgb(var(--v-theme-secondary));
  }
</style>
