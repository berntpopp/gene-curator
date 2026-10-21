<template>
  <div class="evidence-table-field">
    <v-table density="compact">
      <caption class="text-left text-body-medium font-weight-medium pb-2">
        {{
          label
        }}
        <span v-if="fieldSchema.required" class="text-error" aria-hidden="true">*</span>
        <div
          v-if="fieldSchema.hint || fieldSchema.description"
          class="text-body-small font-weight-regular text-medium-emphasis"
        >
          {{ fieldSchema.hint || fieldSchema.description }}
        </div>
      </caption>
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" scope="col">
            {{ col.label }}
            <span v-if="col.schema.required" class="text-error" aria-hidden="true">*</span>
          </th>
          <th v-if="!disabled" scope="col"><span class="d-sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="rowKey(row, index)">
          <td v-for="col in columns" :key="col.key">
            <component
              :is="col.cell.is"
              v-bind="col.cell.props"
              :model-value="row[col.key]"
              :aria-label="`${col.label}, row ${index + 1}`"
              :rules="col.rules"
              :readonly="disabled"
              density="compact"
              variant="underlined"
              hide-details="auto"
              @update:model-value="(v: unknown) => col.cell.lazy || commit(index, col.key, v)"
              @change="
                (e: Event) => col.cell.lazy && commit(index, col.key, inputValue(col.schema, e))
              "
            />
          </td>
          <td v-if="!disabled">
            <v-btn
              :aria-label="`Remove row ${index + 1}`"
              icon="mdi-delete"
              size="small"
              color="error"
              variant="text"
              @click="removeRow(index)"
            />
          </td>
        </tr>
      </tbody>
    </v-table>

    <div v-if="!rows.length" class="text-body-small text-medium-emphasis py-2">No rows yet</div>
    <v-btn v-if="!disabled" variant="outlined" size="small" prepend-icon="mdi-plus" @click="addRow">
      Add row
    </v-btn>
    <div v-if="errorMessages?.length" class="text-error text-body-small mt-1" role="alert">
      {{ errorMessages.join(', ') }}
    </div>
  </div>
</template>

<script setup lang="ts">
  /**
   * `evidence_table` field: one row per evidence item, columns are fields rendered with the
   * registry's compact cell editors. Text cells commit on change (blur/Enter), never per keystroke.
   */
  import { computed } from 'vue'
  import { generateUUID } from '@/utils/uuidPolyfill'
  import { cellFor, emptyValue } from './componentRegistry'
  import { rulesFor } from './composables/useValidationRules'
  import { humanize } from './fieldLabels'
  import type { FieldSchema } from './types'

  type Row = Record<string, unknown>

  const props = defineProps<{
    fieldSchema: FieldSchema
    label: string
    modelValue?: unknown
    disabled?: boolean
    errorMessages?: string[]
  }>()

  const emit = defineEmits<{ 'update:model-value': [rows: Row[]] }>()

  const rows = computed<Row[]>(() => (Array.isArray(props.modelValue) ? props.modelValue : []))
  const columns = computed(() =>
    Object.entries(props.fieldSchema.columns ?? {}).map(([key, schema]) => ({
      key,
      schema,
      label: schema.title || humanize(key),
      cell: cellFor(schema),
      rules: rulesFor(schema)
    }))
  )

  // Row ids keep review diffs and comments anchored when rows are removed
  const rowKey = (row: Row, index: number) =>
    typeof row.id === 'string' || typeof row.id === 'number' ? row.id : index

  function inputValue(schema: FieldSchema, event: Event): unknown {
    const raw = (event.target as HTMLInputElement).value
    if (schema.type !== 'number' && schema.type !== 'integer') return raw
    // Number inputs report unparsable text as '', so this is a number or empty
    return raw === '' ? null : Number(raw)
  }

  function commit(index: number, key: string, value: unknown) {
    if (rows.value[index]?.[key] === value) return
    emit(
      'update:model-value',
      rows.value.map((row, i) => (i === index ? { ...row, [key]: value } : row))
    )
  }

  function addRow() {
    const row: Row = { id: generateUUID() }
    for (const col of columns.value) row[col.key] = emptyValue(col.schema)
    emit('update:model-value', [...rows.value, row])
  }

  function removeRow(index: number) {
    emit(
      'update:model-value',
      rows.value.filter((_, i) => i !== index)
    )
  }
</script>

<style scoped>
  .evidence-table-field {
    overflow-x: auto;
  }

  .evidence-table-field :deep(td) {
    padding: 4px 8px !important;
    min-width: 8rem;
  }

  /* Visible focus for keyboard users on every cell editor */
  .evidence-table-field :deep(td:focus-within) {
    outline: 2px solid rgb(var(--v-theme-primary));
    outline-offset: -2px;
  }

  .evidence-table-field :deep(th) {
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }
</style>
