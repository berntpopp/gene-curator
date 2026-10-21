<template>
  <span
    class="cls-mark"
    :class="{ 'cls-mark--hued': hued }"
    :style="{ '--cls-color': `var(--v-theme-${info.color})` }"
    :title="info.label"
  >
    <span class="cls-mark__bars" aria-hidden="true">
      <i v-for="n in 4" :key="n" :class="{ on: n <= info.bars }" />
    </span>
    <span class="cls-mark__label">{{ info.label }}</span>
  </span>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { getClassification } from '@/config/classification'

  const props = defineProps<{ classification: string | null | undefined }>()
  const info = computed(() => getClassification(props.classification))
  const hued = computed(() => info.value.key === 'disputed' || info.value.key === 'refuted')
</script>

<style scoped>
  .cls-mark {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    color: rgb(var(--v-theme-on-surface));
    font-size: inherit;
    line-height: inherit;
  }

  .cls-mark--hued {
    color: rgb(var(--cls-color));
  }

  .cls-mark__bars {
    display: inline-flex;
    gap: 2px;
    align-items: flex-end;
  }

  .cls-mark__bars i {
    width: 4px;
    height: 0.9em;
    border-radius: 1px;
    border: 1px solid rgb(var(--cls-color));
    box-sizing: border-box;
  }

  .cls-mark__bars i.on {
    background: rgb(var(--cls-color));
  }
</style>
