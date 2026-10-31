<template>
  <div>
    <div class="text-title-small mb-2">Table columns</div>
    <div
      v-for="(row, i) in rows"
      :key="i"
      class="d-flex flex-wrap align-center ga-2 mb-2"
      :data-testid="`column-${i}`"
    >
      <v-text-field
        v-model="row.key"
        label="Column id"
        density="compact"
        variant="outlined"
        hide-details="auto"
        class="col-key"
        :rules="[keyRule(i)]"
        @update:model-value="sync"
      />
      <v-text-field
        :model-value="String(row.def.label ?? '')"
        label="Column label"
        density="compact"
        variant="outlined"
        hide-details
        class="col-label"
        @update:model-value="v => set(row, 'label', v)"
      />
      <v-select
        :model-value="row.def.type"
        :items="FIELD_TYPES"
        label="Column type"
        density="compact"
        variant="outlined"
        hide-details
        class="col-type"
        @update:model-value="v => set(row, 'type', v)"
      />
      <v-text-field
        v-if="CHOICE_TYPES.includes(String(row.def.type))"
        :model-value="optionValues(row.def)"
        label="Choices (comma separated)"
        density="compact"
        variant="outlined"
        hide-details
        class="col-label"
        @update:model-value="v => setOptions(row, v)"
      />
      <v-checkbox
        :model-value="!!row.def.required"
        label="Required"
        density="compact"
        hide-details
        @update:model-value="v => set(row, 'required', !!v)"
      />
      <v-btn
        icon="mdi-delete"
        variant="text"
        size="small"
        :aria-label="`Remove column ${row.key || i + 1}`"
        @click="remove(i)"
      />
    </div>
    <v-btn variant="tonal" size="small" prepend-icon="mdi-plus" @click="add"> Add column </v-btn>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { CHOICE_TYPES, FIELD_TYPES, clone } from './fieldModel'

  type Def = Record<string, unknown>
  interface Row {
    key: string
    def: Def
  }

  // Evidence-table columns ({ key: field }); keys the editor does not show are kept per column
  const props = defineProps<{ modelValue: Record<string, Def> | undefined }>()
  const emit = defineEmits<{ 'update:modelValue': [value: Record<string, Def>] }>()

  // jsonb does not keep key order: each column carries its `order` (monkey B10)
  const rows = ref<Row[]>(
    Object.entries(clone(props.modelValue ?? {}))
      .map(([key, def]) => ({ key, def }))
      .sort((a, b) => Number(a.def.order ?? Infinity) - Number(b.def.order ?? Infinity))
  )

  const sync = () =>
    emit(
      'update:modelValue',
      Object.fromEntries(
        rows.value
          .filter(r => r.key.trim())
          .map((r, i) => [r.key.trim(), Object.assign(r.def, { order: i + 1 })])
      )
    )

  const set = (row: Row, key: string, value: unknown) => {
    row.def[key] = value
    sync()
  }

  const optionValues = (def: Def) =>
    ((def.options ?? []) as Array<{ value: unknown }>).map(o => String(o.value)).join(', ')

  // Labels of existing options survive; a new value is its own label
  const setOptions = (row: Row, text: string) => {
    const old = (row.def.options ?? []) as Array<{ value: unknown; label?: string }>
    const values = text
      .split(',')
      .map(v => v.trim())
      .filter(Boolean)
    set(
      row,
      'options',
      values.map(value => old.find(o => String(o.value) === value) ?? { value, label: value })
    )
  }

  const keyRule = (i: number) => (v: string) => {
    if (!v.trim()) return 'Column id is required'
    return rows.value.some((r, j) => j !== i && r.key.trim() === v.trim())
      ? 'Column ids must be unique'
      : true
  }

  const add = () => {
    rows.value.push({ key: `column_${rows.value.length + 1}`, def: { type: 'text', label: '' } })
    sync()
  }

  const remove = (i: number) => {
    rows.value.splice(i, 1)
    sync()
  }
</script>

<style scoped>
  .col-key {
    flex: 1 1 140px;
  }
  .col-label {
    flex: 2 1 180px;
  }
  .col-type {
    flex: 1 1 160px;
  }
</style>
