<template>
  <v-dialog
    :model-value="!!row"
    content-class="row-editor"
    :content-props="{ 'aria-labelledby': titleId }"
    transition="slide-x-reverse-transition"
    scrollable
    @update:model-value="open => !open && emit('close')"
  >
    <v-card v-if="row">
      <v-card-title :id="titleId" class="text-title-medium">{{ title }}</v-card-title>
      <v-card-text>
        <!-- One row through the dynamic form's own fields: the full editors, with room to type -->
        <DynamicField
          v-for="col in columns"
          :key="col.key"
          class="mb-2"
          :field-name="col.key"
          :field-schema="col.schema"
          :model-value="row[col.key]"
          variant="outlined"
          @update:model-value="(v: unknown) => emit('update', col.key, v)"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" variant="flat" @click="emit('close')">Done</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  /** Side sheet editing one evidence row of a wide table; every change applies at once. */
  import { getCurrentInstance } from 'vue'
  import DynamicField from './DynamicField.vue'
  import type { FieldSchema } from './types'

  type Row = Record<string, unknown>
  defineProps<{
    row: Row | null
    title: string
    columns: { key: string; schema: FieldSchema }[]
  }>()
  const emit = defineEmits<{ update: [column: string, value: unknown]; close: [] }>()
  const titleId = `row-editor-${getCurrentInstance()?.uid}`
</script>

<style>
  /* A sheet on the right, full height, as wide as a phone allows */
  .row-editor {
    position: fixed !important;
    inset: 0 0 0 auto;
    margin: 0 !important;
    width: min(32rem, 100vw) !important;
    max-width: 100vw !important;
    height: 100%;
    max-height: 100% !important;
  }

  .row-editor > .v-card {
    border-radius: 0 !important;
    height: 100%;
  }
</style>
