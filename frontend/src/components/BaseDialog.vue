<template>
  <v-dialog
    :model-value="modelValue"
    :persistent="persistent"
    :max-width="widths[size]"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
    @keydown.escape="emit('cancel')"
    @after-leave="restoreFocus"
  >
    <v-card>
      <v-card-title v-if="title || $slots.title"
        ><slot name="title">{{ title }}</slot></v-card-title
      >
      <v-card-text><slot /></v-card-text>
      <v-card-actions v-if="$slots.actions">
        <v-spacer />
        <slot name="actions" />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import { watch } from 'vue'

  const props = withDefaults(
    defineProps<{
      modelValue: boolean
      title?: string
      size?: 'sm' | 'md' | 'lg'
      persistent?: boolean
    }>(),
    { title: '', size: 'md', persistent: false }
  )
  const emit = defineEmits<{ 'update:modelValue': [value: boolean]; cancel: [] }>()

  const widths = { sm: 400, md: 560, lg: 800 }

  // Vuetify has no activator when opened via v-model, so remember the opener ourselves.
  let opener: HTMLElement | null = null
  watch(
    () => props.modelValue,
    open => {
      if (open) opener = document.activeElement as HTMLElement | null
    },
    { flush: 'sync', immediate: true }
  )

  function restoreFocus() {
    opener?.focus()
    opener = null
  }
</script>
