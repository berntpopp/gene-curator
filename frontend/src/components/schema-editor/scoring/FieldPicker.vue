<template>
  <v-combobox
    :model-value="modelValue"
    :items="items"
    :return-object="false"
    item-props
    density="compact"
    :no-data-text="emptyText"
    @update:model-value="v => emit('update:modelValue', v == null ? '' : String(v))"
  />
</template>

<script setup lang="ts">
  import type { Option } from './evidenceFields'

  /**
   * Choose a field of the schema by label; typing stays possible for paths the list does
   * not know (an older model, a field added later), which Check then flags.
   */
  withDefaults(defineProps<{ modelValue: string; items: Option[]; emptyText?: string }>(), {
    emptyText: 'No matching field in this schema'
  })
  const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
