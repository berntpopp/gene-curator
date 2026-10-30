<template>
  <div>
    <v-table density="compact" class="point-types">
      <thead>
        <tr>
          <th>Evidence path</th>
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
              <v-text-field
                v-model="item.path"
                aria-label="Evidence path"
                density="compact"
                variant="plain"
                placeholder="table.path"
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
                variant="plain"
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
                variant="plain"
                :error-messages="diag(`${base}[${k}].${col.key}`)"
                :hide-details="!diag(`${base}[${k}].${col.key}`).length"
                @update:model-value="v => col.set(item, v)"
              />
            </td>
            <td>
              <v-text-field
                :model-value="item.group_by ?? ''"
                aria-label="Group by field"
                density="compact"
                variant="plain"
                placeholder="variant"
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
                variant="plain"
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
                @click="types.splice(k, 1)"
              />
            </td>
          </tr>
          <tr v-if="open[k]">
            <td colspan="9" class="bg-surface-light">
              <PointModelRowRules :item="item" :base="`${base}[${k}]`" :diag="diag" />
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
  import PointModelRowRules from './PointModelRowRules.vue'
  import { setNumber, setText, type DiagFn, type ItemType } from './pointModel'

  defineProps<{ base: string; diag: DiagFn }>()
  const types = defineModel<ItemType[]>({ required: true })
  const open = reactive<Record<number, boolean>>({})

  // '' is the default rule: the row's points (or the type default)
  const RULES = [
    { title: 'Points entered', value: '' },
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

  const NUMBER_COLS = [
    {
      key: 'default',
      label: 'Default points',
      get: (i: ItemType) => i.default ?? '',
      set: (i: ItemType, v: unknown) => setNumber(i, 'default', v)
    },
    {
      key: 'range',
      label: 'Minimum points',
      get: (i: ItemType) => i.range?.[0] ?? '',
      set: (i: ItemType, v: unknown) => setRange(i, 0, v)
    },
    {
      key: 'range',
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
</style>
