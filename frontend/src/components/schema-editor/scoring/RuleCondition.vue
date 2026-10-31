<template>
  <FieldPicker
    v-model="cond.field"
    :items="columns"
    label="Column"
    variant="outlined"
    :error-messages="diag(`${path}.field`)"
  />
  <template v-if="!bounds(cond).length">
    <v-select
      :model-value="listOp(cond)"
      :items="OPS"
      label="Test"
      density="compact"
      variant="outlined"
      class="op"
      @update:model-value="v => setOp(cond, listOp(cond), v)"
    />
    <v-combobox
      v-if="listOp(cond) === 'in'"
      :model-value="(cond.in ?? []).map(String)"
      :items="choicesOf(cond)"
      :item-title="(v: string) => labelsOf(cond)[v] ?? v"
      label="Values"
      multiple
      chips
      closable-chips
      density="compact"
      variant="outlined"
      :error-messages="diag(`${path}.in`)"
      @update:model-value="v => (cond.in = keepTypes(cond.in, v))"
    />
  </template>
  <template v-for="op in bounds(cond)" :key="op">
    <v-select
      :model-value="op"
      :items="OPS.filter(o => o.value === op || !bounds(cond).includes(o.value as Bound))"
      label="Test"
      density="compact"
      variant="outlined"
      class="op"
      @update:model-value="v => setOp(cond, op, v)"
    />
    <v-text-field
      :model-value="cond[op]"
      label="Value"
      type="number"
      density="compact"
      variant="outlined"
      :error-messages="diag(`${path}.${op}`)"
      @update:model-value="v => setValue(cond, op, v)"
    />
  </template>
  <v-btn
    v-if="bounds(cond).length === 1"
    aria-label="Add second bound"
    icon="mdi-plus"
    size="small"
    variant="text"
    @click="addBound(cond)"
  />
</template>

<script setup lang="ts">
  import FieldPicker from './FieldPicker.vue'
  import type { ColumnOption } from './evidenceFields'
  import { keepTypes, type DiagFn, type RowCondition } from './pointModel'

  /** One row test (column, operator, values or bounds) of a `points_when` rule or its `and`. */
  const props = withDefaults(
    defineProps<{ path: string; diag: DiagFn; columns?: ColumnOption[] }>(),
    { columns: () => [] }
  )
  const cond = defineModel<RowCondition>('cond', { required: true })

  const OPS = [
    { title: 'is one of', value: 'in' },
    { title: 'is filled in', value: 'present' },
    { title: 'is blank', value: 'absent' },
    { title: '>', value: 'gt' },
    { title: '≥', value: 'gte' },
    { title: '<', value: 'lt' },
    { title: '≤', value: 'lte' }
  ] as const
  type Op = (typeof OPS)[number]['value']
  const NUMERIC = ['gt', 'gte', 'lt', 'lte'] as const
  type Bound = (typeof NUMERIC)[number]

  /** The numeric bounds a condition holds (gte + lte is a range); none means a value list. */
  const bounds = (c: RowCondition): Bound[] => NUMERIC.filter(op => op in c)

  /** A condition without bounds tests a value list, or that the field is filled in or blank. */
  const listOp = (c: RowCondition): Op =>
    'present' in c ? (c.present ? 'present' : 'absent') : 'in'

  /** The picked column's choice values, so "is one of" offers what the form stores. */
  const choicesOf = (c: RowCondition) =>
    props.columns.find(col => col.value === c.field)?.options ?? []

  const labelsOf = (c: RowCondition) =>
    props.columns.find(col => col.value === c.field)?.optionLabels ?? {}

  /** Change one test; a bound keeps its value and the other bound stays. */
  const setOp = (c: RowCondition, from: Op, picked: string) => {
    const to = picked as Op // one of OPS: the select offers nothing else
    if (from === to) return
    if (to === 'in' || to === 'present' || to === 'absent') {
      for (const key of [...NUMERIC, 'in', 'present']) delete c[key]
      if (to === 'in') c.in = []
      else c.present = to === 'present'
      return
    }
    const bound = from !== 'in' && from !== 'present' && from !== 'absent'
    const value = bound ? (c[from] ?? 0) : 0
    delete c[bound ? from : 'in']
    delete c.present
    c[to] = value
  }

  const addBound = (c: RowCondition) => {
    const [only] = bounds(c)
    c[only === 'gt' || only === 'gte' ? 'lte' : 'gte'] = 0
  }

  // A cleared value removes that bound; it never turns into 0
  const setValue = (c: RowCondition, op: Bound, value: unknown) => {
    if (value === '' || value === null || value === undefined) delete c[op]
    else c[op] = Number(value)
  }
</script>

<style scoped>
  .op {
    max-width: 140px;
  }
</style>
