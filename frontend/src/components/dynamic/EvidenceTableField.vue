<template>
  <div ref="root" class="evidence-table-field">
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
              :model-value="
                draftKey(row, index, col.key) in drafts
                  ? drafts[draftKey(row, index, col.key)]
                  : row[col.key]
              "
              :aria-label="`${col.label}, row ${index + 1}`"
              :rules="col.rules"
              :readonly="disabled"
              density="compact"
              variant="underlined"
              hide-details="auto"
              @update:model-value="(v: unknown) => onInput(row, index, col, v)"
              @change="(e: Event) => col.cell.lazy && onChange(row, index, col, e)"
              @keydown.escape="delete drafts[draftKey(row, index, col.key)]"
              @blur="(e: Event) => col.pmid && onPmidBlur(row, index, e)"
            />
            <template v-if="col.pmid && row[col.key]">
              <PubmedLinkButton :pmid="row[col.key]" />
              <span
                v-for="r in [lookup.resultOf(row[col.key])]"
                :key="r?.status"
                :class="['pmid-note', { 'pmid-note--error': r?.status === 'notfound' }]"
                :title="r?.title"
                :role="r?.status === 'notfound' ? 'alert' : undefined"
              >
                {{ pmidNote(r) }}
              </span>
            </template>
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
    <v-btn
      v-if="!disabled"
      class="add-row"
      variant="outlined"
      size="small"
      prepend-icon="mdi-plus"
      @click="addRow"
    >
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
  import {
    computed,
    getCurrentInstance,
    inject,
    nextTick,
    onBeforeUnmount,
    reactive,
    ref,
    watch
  } from 'vue'
  import { generateUUID } from '@/utils/uuidPolyfill'
  import { usePmidLookup, type PmidResult } from '@/composables/usePmidLookup'
  import { WORKSPACE_FRAME } from '@/components/workspace/useWorkspaceFrame'
  import PubmedLinkButton from './PubmedLinkButton.vue'
  import { cellFor, emptyValue } from './componentRegistry'
  import { rulesFor } from './composables/useValidationRules'
  import { humanize } from './fieldLabels'
  import type { CellDef } from './componentRegistry'
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

  // Legacy rows stored a single item object instead of a list: show it as one row
  const rows = computed<Row[]>(() => {
    const value = props.modelValue
    if (Array.isArray(value)) return value
    return value && typeof value === 'object' ? [value as Row] : []
  })
  const columns = computed(() =>
    Object.entries(props.fieldSchema.columns ?? {}).map(([key, schema]) => ({
      key,
      schema,
      label: schema.title || humanize(key),
      cell: cellFor(schema),
      rules: rulesFor(schema),
      pmid: schema.format === 'pmid'
    }))
  )

  // Row ids keep review diffs and comments anchored when rows are removed
  const rowKey = (row: Row, index: number) =>
    typeof row.id === 'string' || typeof row.id === 'number' ? row.id : index

  // PMID cells: Europe PMC lookup on blur; an unknown PMID blocks submitting, not saving a draft
  // (the workspace frame disables Submit and lists the reason under "Before you submit")
  const lookup = usePmidLookup()
  const frame = inject(WORKSPACE_FRAME, null)
  const blockerId = `evidence-table-${getCurrentInstance()?.uid}`
  const tablePmids = computed(() =>
    rows.value.flatMap(row => columns.value.filter(c => c.pmid).map(c => row[c.key]))
  )
  const unknownPmids = computed(() =>
    tablePmids.value.filter(p => lookup.statusOf(p) === 'notfound').map(p => String(p).trim())
  )
  watch(
    unknownPmids,
    list =>
      !lookup.shared &&
      frame?.setBlocker(
        blockerId,
        list.length
          ? `Fix ${list.length} unknown PMID${list.length > 1 ? 's' : ''} before submitting: ` +
              `PMID ${list.join(', ')} not found in Europe PMC`
          : null
      ),
    { immediate: true }
  )
  onBeforeUnmount(() => frame?.setBlocker(blockerId, null))
  // Retry on PMID-set/editability changes, not unrelated score edits or row reordering.
  watch(
    [() => JSON.stringify([...new Set(tablePmids.value)].sort()), () => props.disabled],
    () => !props.disabled && lookup.checkAll(tablePmids.value),
    { immediate: true }
  )
  // Removing a row cancels its own lookup
  watch(
    () => rows.value.map(rowKey),
    (keys, before) => {
      const live = new Set(keys)
      before?.filter(k => !live.has(k)).forEach(k => lookup.cancel(k))
    }
  )

  function onPmidBlur(row: Row, index: number, event: Event) {
    if (!props.disabled) lookup.check(rowKey(row, index), (event.target as HTMLInputElement).value)
  }

  const PMID_NOTES: Partial<Record<string, string>> = {
    notfound: 'PMID not found in Europe PMC',
    loading: 'Looking up…'
  }
  const pmidNote = (r: PmidResult | undefined) =>
    r?.status === 'found' ? r.citation : PMID_NOTES[r?.status ?? '']

  function inputValue(schema: FieldSchema, event: Event): unknown {
    const raw = (event.target as HTMLInputElement).value
    if (schema.type !== 'number' && schema.type !== 'integer') return raw
    // Number inputs report unparsable text as '', so this is a number or empty
    return raw === '' ? null : Number(raw)
  }

  interface Column {
    key: string
    schema: FieldSchema
    cell: CellDef
  }

  const root = ref<HTMLElement | null>(null)
  // Typed text of lazy cells, keyed by row and column: survives the rows being replaced
  // (e.g. late initialData) until the cell commits on change or Escape drops it
  const drafts = reactive<Record<string, unknown>>({})
  const draftKey = (row: Row, index: number, key: string) => `${rowKey(row, index)}:${key}`

  function onInput(row: Row, index: number, col: Column, value: unknown) {
    if (col.cell.lazy) drafts[draftKey(row, index, col.key)] = value
    else commit(rowKey(row, index), col.key, value)
  }

  function onChange(row: Row, index: number, col: Column, event: Event) {
    delete drafts[draftKey(row, index, col.key)]
    commit(rowKey(row, index), col.key, inputValue(col.schema, event))
  }

  // By row identity, not position: the rows may have been replaced since the edit began
  function commit(key: string | number, column: string, value: unknown) {
    const index = rows.value.findIndex((row, i) => rowKey(row, i) === key)
    if (index < 0 || rows.value[index]![column] === value) return
    emit(
      'update:model-value',
      rows.value.map((row, i) => (i === index ? { ...row, [column]: value } : row))
    )
  }

  const focus = (selector: string) =>
    nextTick(() => root.value?.querySelector<HTMLElement>(selector)?.focus())

  function addRow() {
    const row: Row = { id: generateUUID() }
    for (const col of columns.value) row[col.key] = emptyValue(col.schema)
    const position = rows.value.length + 1
    emit('update:model-value', [...rows.value, row])
    const first = columns.value[0]
    if (first) focus(`[aria-label=${CSS.escape(`${first.label}, row ${position}`)}]`)
  }

  function removeRow(index: number) {
    // The next row moves up into this position; without one, focus "Add row"
    const next =
      index < rows.value.length - 1 ? `[aria-label="Remove row ${index + 1}"]` : '.add-row'
    emit(
      'update:model-value',
      rows.value.filter((_, i) => i !== index)
    )
    focus(next)
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

  .pmid-note {
    display: block;
    font-size: 0.75rem;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .pmid-note--error {
    color: rgb(var(--v-theme-error));
  }

  .evidence-table-field :deep(th) {
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }
</style>
