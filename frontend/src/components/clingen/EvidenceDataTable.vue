<template>
  <div class="evidence-data-table">
    <v-table v-if="items.length > 0" density="compact" class="rounded">
      <thead>
        <tr class="bg-surface-variant">
          <th v-for="col in columns" :key="col.key" :style="{ width: col.width }">
            {{ col.label }}
          </th>
          <th v-if="!readonly" style="width: 60px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in items" :key="index">
          <td v-for="col in columns" :key="col.key">
            <!-- PMID field with link -->
            <template v-if="col.type === 'pmid'">
              <div class="d-flex align-center">
                <v-text-field
                  :model-value="item[col.key]"
                  density="compact"
                  :aria-label="`${col.label}, row ${index + 1}`"
                  variant="underlined"
                  hide-details="auto"
                  :rules="[pmidRule]"
                  :readonly="readonly"
                  placeholder="PMID"
                  @change="commitInput(index, col.key, $event)"
                  @blur="onPmidBlur(item, index, $event)"
                />
                <PubmedLinkButton v-if="item[col.key]" :pmid="item[col.key]" />
              </div>
              <template v-for="r in [lookup.resultOf(item[col.key])]" :key="r?.status">
                <div
                  v-if="r?.status === 'found'"
                  data-testid="pmid-citation"
                  class="pmid-note"
                  :title="r.title"
                >
                  {{ r.citation }}
                </div>
                <div
                  v-else-if="r?.status === 'notfound'"
                  data-testid="pmid-notfound"
                  class="pmid-note pmid-note--error"
                  role="alert"
                >
                  PMID not found in Europe PMC
                </div>
                <div v-else-if="r?.status === 'loading'" class="pmid-note">Looking up…</div>
              </template>
            </template>

            <!-- Select field -->
            <template v-else-if="col.type === 'select'">
              <v-select
                :model-value="item[col.key]"
                :items="col.options"
                item-title="label"
                item-value="value"
                density="compact"
                :aria-label="`${col.label}, row ${index + 1}`"
                variant="underlined"
                hide-details
                :readonly="readonly"
                @update:model-value="updateField(index, col.key, $event)"
              />
            </template>

            <!-- Number field -->
            <template v-else-if="col.type === 'number'">
              <v-text-field
                :model-value="item[col.key]"
                type="number"
                :min="col.min"
                :max="col.max"
                :step="col.step || 1"
                density="compact"
                :aria-label="`${col.label}, row ${index + 1}`"
                variant="underlined"
                hide-details="auto"
                :rules="[rangeRule(col)]"
                :readonly="readonly"
                @change="commitInput(index, col.key, $event, true)"
              />
            </template>

            <!-- Default text field -->
            <template v-else>
              <v-text-field
                :model-value="item[col.key]"
                density="compact"
                :aria-label="`${col.label}, row ${index + 1}`"
                variant="underlined"
                hide-details
                :readonly="readonly"
                @change="commitInput(index, col.key, $event)"
              />
            </template>
          </td>

          <!-- Actions column -->
          <td v-if="!readonly">
            <v-btn
              aria-label="Remove evidence"
              icon
              size="small"
              color="error"
              variant="text"
              @click="$emit('remove', index)"
            >
              <v-icon size="small">mdi-delete</v-icon>
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <!-- Empty state -->
    <v-alert v-else type="info" variant="tonal" density="compact">
      {{
        readonly
          ? 'No evidence recorded'
          : 'No evidence items added yet. Click "Add Evidence" to begin.'
      }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
  /**
   * EvidenceDataTable
   *
   * Reusable table component for entering ClinGen evidence data.
   * Supports various field types: text, number, select, pmid.
   */

  import { computed, getCurrentInstance, inject, onBeforeUnmount, watch } from 'vue'
  import PubmedLinkButton from './PubmedLinkButton.vue'
  import { usePmidLookup } from '@/composables/usePmidLookup'
  import { WORKSPACE_FRAME } from '@/components/workspace/useWorkspaceFrame'
  import type { EvidenceColumn, EvidenceItem } from './types'

  const props = withDefaults(
    defineProps<{
      items?: EvidenceItem[]
      columns: EvidenceColumn[]
      readonly?: boolean
      evidenceType?: string
    }>(),
    {
      items: () => [],
      readonly: false,
      evidenceType: ''
    }
  )

  const emit = defineEmits<{
    'update:items': [items: EvidenceItem[]]
    remove: [index: number]
  }>()

  // PMID cells: Europe PMC lookup on blur; an unknown PMID blocks saving (the workspace frame says so)
  const lookup = usePmidLookup()
  const frame = inject(WORKSPACE_FRAME, null)
  const blockerId = `evidence-table-${getCurrentInstance()?.uid}`
  const pmidKeys = computed(() => props.columns.filter(c => c.type === 'pmid').map(c => c.key))
  const unknownPmids = computed(() =>
    props.items
      .flatMap(item => pmidKeys.value.map(k => item[k]))
      .filter(p => lookup.statusOf(p) === 'notfound')
      .map(p => String(p).trim())
  )
  watch(
    unknownPmids,
    list =>
      frame?.setBlocker(
        blockerId,
        list.length ? `PMID ${list.join(', ')} not found in Europe PMC` : null
      ),
    { immediate: true }
  )
  onBeforeUnmount(() => frame?.setBlocker(blockerId, null))

  // Lookups are keyed by the row's id when it has one, so removing a row cancels its own lookup
  const rowKey = (item: EvidenceItem, index: number): string | number =>
    typeof item.id === 'string' || typeof item.id === 'number' ? item.id : index

  function onPmidBlur(item: EvidenceItem, index: number, event: Event) {
    if (!props.readonly) lookup.check(rowKey(item, index), (event.target as HTMLInputElement).value)
  }

  watch(
    () => props.items.map(rowKey),
    (keys, before) => {
      const live = new Set(keys)
      before?.filter(k => !live.has(k)).forEach(k => lookup.cancel(k))
    }
  )

  function updateField(index: number, key: string, value: unknown) {
    const newItems = [...props.items]
    newItems[index] = { ...newItems[index], [key]: value }
    emit('update:items', newItems)
  }

  // Cells commit on change (blur/Enter), not per keystroke: typing must not re-render the form tree
  function commitInput(index: number, key: string, event: Event, numeric = false) {
    const raw = (event.target as HTMLInputElement).value
    // Keep what was typed; the rules show the error (clamping is the scorer's job, #157)
    updateField(
      index,
      key,
      numeric && raw !== '' && Number.isFinite(Number(raw)) ? Number(raw) : raw
    )
  }

  const pmidRule = (v: unknown) =>
    !v || /^(PMID:?\s*)?\d{1,9}$/i.test(String(v).trim()) || 'PMID must be digits only'

  const rangeRule = (col: EvidenceColumn) => (v: unknown) => {
    if (v === '' || v == null) return true
    const n = Number(v)
    const { min = -Infinity, max = Infinity } = col
    return (Number.isFinite(n) && n >= min && n <= max) || `Enter a number from ${min} to ${max}`
  }
</script>

<style scoped>
  .evidence-data-table {
    overflow-x: auto;
  }

  .evidence-data-table :deep(.v-text-field input) {
    font-size: 0.875rem;
  }

  .evidence-data-table :deep(.v-select .v-field__input) {
    font-size: 0.875rem;
  }

  .evidence-data-table :deep(td) {
    padding: 4px 8px !important;
    vertical-align: middle;
  }

  .pmid-note {
    font-size: 0.75rem;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .pmid-note--error {
    color: rgb(var(--v-theme-error));
  }

  .evidence-data-table :deep(th) {
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }
</style>
