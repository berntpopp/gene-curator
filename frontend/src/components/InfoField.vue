<template>
  <div class="mb-3">
    <div class="text-caption text-medium-emphasis mb-1">{{ label }}</div>
    <div :class="`text-body-1 ${monospace ? 'font-monospace' : ''}`">
      {{ value || '—' }}
    </div>
  </div>
</template>

<script setup>
  defineProps({
    label: {
      type: String,
      required: true
    },
    value: {
      type: String,
      default: ''
    },
    monospace: {
      type: Boolean,
      default: false
    }
  })
</script>

<style scoped>
  .font-monospace {
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
  }
</style>
