<template>
  <div>
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      Raw JSON of every configuration block. Changes here and in the other tabs edit the same draft;
      Save stores all of them.
    </v-alert>
    <v-tabs v-model="active" color="primary" density="compact" show-arrows class="mb-4">
      <v-tab v-for="block in BLOCKS" :key="block.key" :value="block.key">
        {{ block.label }}
        <v-badge v-if="errors[block.key]" color="error" dot inline class="ml-2" />
      </v-tab>
    </v-tabs>
    <v-window v-model="active">
      <v-window-item v-for="block in BLOCKS" :key="block.key" :value="block.key" eager>
        <JsonBlockEditor
          :model-value="modelValue[block.key]"
          :label="`${block.label} (JSON)`"
          :hint="block.hint"
          :nullable="block.key === 'scoring_configuration'"
          :readonly="readonly"
          @update:model-value="value => emit('update', block.key, value)"
          @error="message => emit('error', block.key, message)"
        />
      </v-window-item>
    </v-window>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import JsonBlockEditor from './JsonBlockEditor.vue'
  import type { BlockKey } from './fieldModel'

  const BLOCKS: Array<{ key: BlockKey; label: string; hint: string }> = [
    {
      key: 'field_definitions',
      label: 'Field definitions',
      hint: 'A { key: field } map, or { "sections": [{ id, label, fields: [...] }] }'
    },
    {
      key: 'ui_configuration',
      label: 'UI configuration',
      hint: 'Layout of the form, e.g. { "sections": [...] } or { "layout": { "tabs": [...] } }'
    },
    { key: 'validation_rules', label: 'Validation rules', hint: 'Cross-field rules, or {}' },
    {
      key: 'scoring_configuration',
      label: 'Scoring',
      hint: 'Engine, point model and classifications; empty for no scoring'
    },
    { key: 'workflow_states', label: 'Workflow states', hint: 'States and allowed transitions' }
  ]

  defineProps<{
    modelValue: Partial<Record<BlockKey, unknown>>
    errors: Partial<Record<BlockKey, string>>
    readonly?: boolean
  }>()
  const emit = defineEmits<{
    update: [key: BlockKey, value: unknown]
    error: [key: BlockKey, message: string]
  }>()

  const active = ref<BlockKey>('field_definitions')
</script>
