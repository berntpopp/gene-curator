<template>
  <div
    ref="root"
    class="evidence-table-field"
    role="region"
    :aria-label="`${label} evidence table`"
    tabindex="0"
  >
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
          <th v-if="authored" scope="col">Added / changed</th>
          <th v-if="!disabled && !readonly" scope="col"><span class="d-sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="rowKey(row, index)">
          <td
            v-for="col in columns"
            :key="col.key"
            :class="{ 'text-cell': col.schema.type === 'string' }"
          >
            <SourceCell
              v-if="(readonly || wide) && col.schema.type === 'source'"
              readonly
              :model-value="row[col.key]"
            />
            <ReadonlyValue
              v-else-if="readonly || wide"
              :schema="col.schema"
              :model-value="row[col.key]"
            />
            <component
              :is="col.cell.is"
              v-else
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
              @keydown.escape="onEscape(row, index, col)"
              @blur="(e: Event) => col.pmid && onPmidBlur(row, index, e)"
            />
            <component
              :is="urlLink(row[col.key])"
              v-if="!readonly && col.url && safeHref(row[col.key])"
            />
            <template v-if="!readonly && col.pmid && row[col.key]">
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
          <td
            v-if="authored"
            class="row-author"
            :title="rowTools(stampOf(stamps, path, row, index)).join(', ')"
          >
            {{ rowAuthorship(stampOf(stamps, path, row, index)) }}
          </td>
          <td v-if="!disabled && !readonly" class="text-no-wrap">
            <v-btn
              v-if="wide"
              :aria-label="`Edit row ${index + 1}`"
              icon="mdi-pencil"
              size="small"
              variant="text"
              @click="editing = rowKey(row, index)"
            />
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
      v-if="!disabled && !readonly"
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
    <EvidenceRowEditor
      :row="editedRow"
      :title="editedTitle"
      :columns="columns"
      @update="updateRow"
      @close="editing = null"
    />
  </div>
</template>

<script setup lang="ts">
  /**
   * `evidence_table` field: one row per evidence item, columns are fields rendered with the
   * registry's compact cell editors. Text cells commit on change (blur/Enter) or after a pause in
   * typing (#469: the form must see it as unsaved), never per keystroke.
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
  import ReadonlyValue from './ReadonlyValue.vue'
  import EvidenceRowEditor from './EvidenceRowEditor.vue'
  import SourceCell from './SourceCell.vue'
  import { FIELD_PATH, ROW_PROVENANCE, rowAuthorship, rowTools, stampOf } from './rowAuthorship'
  import {
    CELL_COMMIT_MS,
    cellFor,
    emptyValue,
    isListType,
    safeHref,
    urlLink,
    urlRule
  } from './componentRegistry'
  import { rulesFor } from './composables/useValidationRules'
  import { humanize } from './fieldLabels'
  import type { CellDef } from './componentRegistry'
  import type { FieldSchema } from './types'

  type Row = Record<string, unknown>

  const props = defineProps<{
    fieldSchema: FieldSchema
    /** Data key of this table; with FIELD_PATH it finds the rows' provenance */
    fieldName?: string
    label: string
    modelValue?: unknown
    disabled?: boolean
    readonly?: boolean
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
      rules:
        schema.type === 'url'
          ? [...rulesFor(schema), urlRule]
          : // The list cell offers only valid options; the enum rule checks a single value
            rulesFor(isListType(schema) ? { ...schema, enum: undefined } : schema),
      pmid: schema.format === 'pmid',
      url: schema.type === 'url'
    }))
  )

  // Wide tables (UX): rows read inline and edit one at a time in a side sheet
  const WIDE_COLUMNS = 6
  const wide = computed(() => columns.value.length > WIDE_COLUMNS && !props.readonly)
  const editing = ref<string | number | null>(null)
  const editedIndex = computed(() => rows.value.findIndex((r, i) => rowKey(r, i) === editing.value))
  const editedRow = computed(() => rows.value[editedIndex.value] ?? null)
  const editedTitle = computed(() => {
    const own = Object.entries(editedRow.value ?? {}).find(
      ([k, v]) => (k === 'label' || k.endsWith('_label')) && typeof v === 'string' && v.trim()
    )?.[1]
    return `${props.label} · ${own ?? `Row ${editedIndex.value + 1}`}`
  })
  // ponytail: sheet edits skip default_by suggestions (inline cells keep them); add when asked
  const updateRow = (row: Row) =>
    emit(
      'update:model-value',
      rows.value.map((r, i) => (i === editedIndex.value ? row : r))
    )

  // #593: who added and changed each row, from the curation's row_provenance
  const stamps = inject(ROW_PROVENANCE, null)
  const path = `${inject(FIELD_PATH, '')}${props.fieldName ?? ''}`
  const authored = computed(() => rows.value.some((row, i) => stampOf(stamps?.value, path, row, i)))

  // Only rows created in this mounted table may follow selector-driven suggestions.
  const automaticDefaults = new Set<string | number>()

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
    [
      () => JSON.stringify([...new Set(tablePmids.value)].sort()),
      () => props.disabled || props.readonly
    ],
    () => !props.disabled && !props.readonly && lookup.checkAll(tablePmids.value),
    { immediate: true }
  )
  // Removing a row cancels its own lookup
  watch(
    () => rows.value.map(rowKey),
    (keys, before) => {
      const live = new Set(keys)
      before
        ?.filter(k => !live.has(k))
        .forEach(k => {
          lookup.cancel(k)
          automaticDefaults.delete(k)
        })
    }
  )

  function onPmidBlur(row: Row, index: number, event: Event) {
    if (!props.disabled && !props.readonly)
      lookup.check(rowKey(row, index), (event.target as HTMLInputElement).value)
  }

  const PMID_NOTES: Partial<Record<string, string>> = {
    notfound: 'PMID not found in Europe PMC',
    loading: 'Looking up…'
  }
  const pmidNote = (r: PmidResult | undefined) =>
    r?.status === 'found' ? r.citation : PMID_NOTES[r?.status ?? '']

  function inputValue(schema: FieldSchema, event: Event): unknown {
    return parsed(schema, (event.target as HTMLInputElement).value)
  }

  function parsed(schema: FieldSchema, raw: unknown): unknown {
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

  // Pending pause-commits of typed text, and each edited cell's value from before the edit
  const timers = new Map<string, { at: ReturnType<typeof setTimeout>; run: () => void }>()
  const before = new Map<string, unknown>()

  function settle(draft: string) {
    clearTimeout(timers.get(draft)?.at)
    timers.delete(draft)
  }

  function onInput(row: Row, index: number, col: Column, value: unknown) {
    if (props.readonly) return
    const key = rowKey(row, index)
    if (col.schema.default_by) automaticDefaults.delete(key)
    if (!col.cell.lazy) return commit(key, col.key, value)
    const draft = draftKey(row, index, col.key)
    drafts[draft] = value
    if (!before.has(draft)) before.set(draft, row[col.key])
    settle(draft)
    const run = () => {
      timers.delete(draft)
      commit(key, col.key, parsed(col.schema, value))
    }
    timers.set(draft, { at: setTimeout(run, CELL_COMMIT_MS), run })
  }

  function onChange(row: Row, index: number, col: Column, event: Event) {
    if (props.readonly) return
    // A deliberate same-value edit is still manual, even when commit emits nothing.
    if (col.schema.default_by) automaticDefaults.delete(rowKey(row, index))
    const draft = draftKey(row, index, col.key)
    settle(draft)
    before.delete(draft)
    delete drafts[draft]
    commit(rowKey(row, index), col.key, inputValue(col.schema, event))
  }

  // Escape drops the typed text; a pause-commit already made is reverted to the pre-edit value
  function onEscape(row: Row, index: number, col: Column) {
    const draft = draftKey(row, index, col.key)
    settle(draft)
    delete drafts[draft]
    if (before.has(draft)) commit(rowKey(row, index), col.key, before.get(draft))
    before.delete(draft)
  }

  // Leaving the tab or page view must not lose typed text
  onBeforeUnmount(() => [...timers.values()].forEach(t => (clearTimeout(t.at), t.run())))

  // By row identity, not position: the rows may have been replaced since the edit began
  function commit(key: string | number, column: string, value: unknown) {
    const index = rows.value.findIndex((row, i) => rowKey(row, i) === key)
    if (index < 0 || rows.value[index]![column] === value) return
    emit(
      'update:model-value',
      rows.value.map((row, i) => {
        if (i !== index) return row
        const changed = { ...row, [column]: value }
        if (automaticDefaults.has(key)) {
          for (const col of columns.value) {
            if (col.schema.default_by?.field === column)
              changed[col.key] = suggested(col.schema, changed)
          }
        }
        return changed
      })
    )
  }

  const focus = (selector: string) =>
    nextTick(() => root.value?.querySelector<HTMLElement>(selector)?.focus())

  function suggested(schema: FieldSchema, row: Row): unknown {
    const mapping = schema.default_by
    return mapping?.values[String(row[mapping.field])] ?? emptyValue(schema)
  }

  function addRow() {
    if (props.readonly) return
    const row: Row = { id: generateUUID() }
    for (const col of columns.value) row[col.key] = emptyValue(col.schema)
    for (const col of columns.value) {
      if (col.schema.default_by) row[col.key] = suggested(col.schema, row)
    }
    automaticDefaults.add(rowKey(row, rows.value.length))
    const position = rows.value.length + 1
    emit('update:model-value', [...rows.value, row])
    if (wide.value) {
      editing.value = row.id as string
      return
    }
    const first = columns.value[0]
    if (first) focus(`[aria-label=${CSS.escape(`${first.label}, row ${position}`)}]`)
  }

  function removeRow(index: number) {
    if (props.readonly) return
    automaticDefaults.delete(rowKey(rows.value[index]!, index))
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
    min-width: 0;
    max-width: 100%;
    overflow-x: auto;
  }

  .evidence-table-field :deep(.v-table__wrapper) {
    overflow: visible;
  }

  .evidence-table-field:focus-visible {
    outline: 2px solid rgb(var(--v-theme-primary));
    outline-offset: 2px;
  }

  .evidence-table-field :deep(.text-cell) {
    min-width: 14rem;
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

  .row-author {
    font-size: 0.75rem;
    min-width: 10rem;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
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
