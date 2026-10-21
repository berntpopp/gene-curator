<template>
  <v-btn v-if="!readonly" size="small" :color="color" variant="tonal">
    <v-icon start>mdi-plus</v-icon>
    {{ label }}
  </v-btn>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{ color?: string; label?: string; readonly?: boolean }>(), {
    color: 'primary',
    label: 'Add Evidence',
    readonly: false
  })
</script>
