<template>
  <div class="readonly-value">
    <div v-if="label" class="text-body-small text-medium-emphasis">{{ label }}</div>
    <span class="readonly-value__text">{{ displayValue }}</span>
    <PubmedLinkButton
      v-if="schema.format === 'pmid' || schema.component === 'PMIDInput'"
      :pmid="modelValue"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { formatValue } from '@/utils/evidenceValue'
  import PubmedLinkButton from './PubmedLinkButton.vue'
  import type { FieldSchema } from './types'

  const props = defineProps<{ schema: FieldSchema; modelValue?: unknown; label?: string }>()
  const displayValue = computed(() => {
    const options = props.schema.enumOptions ?? props.schema.enum
    return Array.isArray(props.modelValue)
      ? props.modelValue.map(value => formatValue(value, options)).join(', ') || 'none'
      : formatValue(props.modelValue, options)
  })
</script>

<style scoped>
  .readonly-value__text {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    user-select: text;
  }
</style>
