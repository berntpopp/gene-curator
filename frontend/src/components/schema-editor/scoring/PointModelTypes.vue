<template>
  <div>
    <v-table density="compact" class="point-types">
      <thead>
        <tr>
          <th class="path">Evidence table</th>
          <th>Rule</th>
          <th class="num">Default</th>
          <th class="num">Min</th>
          <th class="num">Max</th>
          <th>Group by</th>
          <th class="num">Group cap</th>
          <th>Needs variant</th>
          <th aria-label="Actions" />
        </tr>
      </thead>
      <tbody>
        <template v-for="(item, k) in types" :key="k">
          <tr>
            <td>
              <FieldPicker
                v-model="item.path"
                :items="tables"
                aria-label="Evidence table"
                variant="underlined"
                placeholder="Choose a table"
                empty-text="This schema has no evidence table here yet"
                :error-messages="diag(`${base}[${k}].path`)"
                :hide-details="!diag(`${base}[${k}].path`).length"
              />
            </td>
            <td>
              <v-select
                :model-value="item.rule ?? ''"
                :items="RULES"
                aria-label="Rule"
                density="compact"
                variant="underlined"
                hide-details
                @update:model-value="v => setText(item, 'rule', v)"
              />
            </td>
            <td v-for="col in NUMBER_COLS" :key="col.label" class="num">
              <v-text-field
                :model-value="col.get(item)"
                :aria-label="col.label"
                type="number"
                density="compact"
                variant="underlined"
                :error-messages="diag(`${base}[${k}].${col.key(item)}`)"
                :hide-details="!diag(`${base}[${k}].${col.key(item)}`).length"
                @update:model-value="v => col.set(item, v)"
              />
            </td>
            <td>
              <FieldPicker
                :model-value="item.group_by ?? ''"
                :items="columnsOf(item)"
                aria-label="Group by column"
                variant="underlined"
                placeholder="None"
                :error-messages="diag(`${base}[${k}].group_by`)"
                :hide-details="!diag(`${base}[${k}].group_by`).length"
                @update:model-value="v => setText(item, 'group_by', v)"
              />
            </td>
            <td class="num">
              <v-text-field
                :model-value="item.group_cap ?? ''"
                aria-label="Group cap"
                type="number"
                density="compact"
                variant="underlined"
                :error-messages="diag(`${base}[${k}].group_cap`)"
                :hide-details="!diag(`${base}[${k}].group_cap`).length"
                @update:model-value="v => setNumber(item, 'group_cap', v)"
              />
            </td>
            <td>
              <v-checkbox-btn
                :model-value="item.require_variant === true"
                aria-label="Rows need a variant to score"
                @update:model-value="v => setFlag(item, v)"
              />
            </td>
            <td class="text-no-wrap">
              <v-btn
                :aria-label="open[k] ? 'Hide row rules' : 'Show row rules'"
                :icon="open[k] ? 'mdi-chevron-up' : 'mdi-cog-outline'"
                size="small"
                variant="text"
                @click="open[k] = !open[k]"
              />
              <v-btn
                aria-label="Remove evidence type"
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="remove(k)"
              />
            </td>
          </tr>
          <tr v-if="open[k]">
            <td colspan="9" class="bg-surface-light">
              <PointModelRowRules
                :item="item"
                :base="`${base}[${k}]`"
                :diag="diag"
                :columns="columnsOf(item)"
              />
            </td>
          </tr>
        </template>
      </tbody>
    </v-table>
    <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="types.push({ path: '' })">
      Evidence type
    </v-btn>
  </div>
</template>

<script setup lang="ts">
  import { reactive } from 'vue'
  import { confirmRemoval } from '@/composables/useConfirm'
  import FieldPicker from './FieldPicker.vue'
  import PointModelRowRules from './PointModelRowRules.vue'
  import type { ColumnOption, TableOption } from './evidenceFields'
  import { setNumber, setText, type DiagFn, type ItemType } from './pointModel'

  const props = withDefaults(
    defineProps<{ base: string; diag: DiagFn; tables?: TableOption[] }>(),
    {
      tables: () => []
    }
  )
  /** Columns of the table a type reads; empty while its path names no known table. */
  const columnsOf = (item: ItemType): ColumnOption[] =>
    props.tables.find(t => t.value === item.path)?.columns ?? []
  const types = defineModel<ItemType[]>({ required: true })
  const open = reactive<Record<number, boolean>>({})
  const remove = async (k: number) =>
    (await confirmRemoval('evidence type')) && types.value.splice(k, 1)

  // '' is the default rule: the row's points (or the type default)
  const RULES = [
    { title: 'Entered, else default', value: '' },
    { title: 'Case row', value: 'case_row' },
    { title: 'Segregation (LOD)', value: 'segregation' },
    { title: 'Explicit points', value: 'explicit_points' },
    { title: 'Step on a field', value: 'step' }
  ]

  /** One bound of the pair; the other is kept. Only clearing both removes the range. */
  const setRange = (item: ItemType, at: 0 | 1, value: unknown) => {
    const range: [number | null, number | null] = [...(item.range ?? [null, null])]
    range[at] = value === '' || value === null ? null : Number(value)
    if (range[0] === null && range[1] === null) delete item.range
    else item.range = range
  }

  // A case row's default is what a blank row scores: `blank_at`, which case_row needs (monkey B8)
  const defaultKey = (i: ItemType) => (i.rule === 'case_row' ? 'blank_at' : 'default')
  const NUMBER_COLS = [
    {
      key: defaultKey,
      label: 'Default points',
      get: (i: ItemType) => i[defaultKey(i)] ?? '',
      set: (i: ItemType, v: unknown) => setNumber(i, defaultKey(i), v)
    },
    {
      key: () => 'range',
      label: 'Minimum points',
      get: (i: ItemType) => i.range?.[0] ?? '',
      set: (i: ItemType, v: unknown) => setRange(i, 0, v)
    },
    {
      key: () => 'range',
      label: 'Maximum points',
      get: (i: ItemType) => i.range?.[1] ?? '',
      set: (i: ItemType, v: unknown) => setRange(i, 1, v)
    }
  ]

  const setFlag = (item: ItemType, on: unknown) => {
    if (on) item.require_variant = true
    else delete item.require_variant
  }
</script>

<style scoped>
  .point-types :deep(td),
  .point-types :deep(th) {
    padding-inline: 6px !important;
  }
  .num {
    width: 88px;
  }
  .path {
    min-width: 200px;
  }
</style>
