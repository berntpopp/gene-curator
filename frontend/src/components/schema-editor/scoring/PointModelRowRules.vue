<template>
  <div class="py-2">
    <v-row dense>
      <v-col cols="12" sm="4">
        <v-text-field
          :model-value="item.points_key ?? ''"
          label="Points column"
          placeholder="points"
          density="compact"
          variant="outlined"
          hint="Row column holding entered points"
          :error-messages="diag(`${base}.points_key`)"
          @update:model-value="v => setText(item, 'points_key', v)"
        />
      </v-col>
      <v-col v-if="item.rule === 'step'" cols="12" sm="4">
        <v-text-field
          :model-value="item.field ?? ''"
          label="Step field"
          placeholder="summed_lod"
          density="compact"
          variant="outlined"
          hint="Summed over the rows; the highest step reached scores once"
          :error-messages="diag(`${base}.field`)"
          @update:model-value="v => setText(item, 'field', v)"
        />
      </v-col>
    </v-row>

    <div v-if="item.rule === 'step'" class="mb-3">
      <div class="text-label-large mb-1">Steps (highest reached minimum wins)</div>
      <div v-for="(step, s) in item.steps ?? []" :key="s" class="d-flex ga-2 align-start">
        <v-text-field
          :model-value="step.min"
          label="From value"
          type="number"
          density="compact"
          variant="outlined"
          :error-messages="diag(`${base}.steps[${s}].min`)"
          @update:model-value="v => (step.min = Number(v))"
        />
        <v-text-field
          :model-value="step.points"
          label="Points"
          type="number"
          density="compact"
          variant="outlined"
          :error-messages="diag(`${base}.steps[${s}].points`)"
          @update:model-value="v => (step.points = Number(v))"
        />
        <v-btn
          aria-label="Remove step"
          icon="mdi-close"
          size="small"
          variant="text"
          @click="remove('steps', s)"
        />
      </div>
      <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="addStep">Step</v-btn>
    </div>

    <div class="text-label-large">Points when</div>
    <p class="text-body-small text-medium-emphasis mb-2">
      A matching rule worth 0 points always wins (e.g. no variant source). A rule worth more only
      fills rows where the curator left the points blank.
    </p>
    <div v-for="(cond, c) in item.points_when ?? []" :key="c" class="d-flex ga-2 align-start">
      <v-text-field
        v-model="cond.field"
        label="Field"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${base}.points_when[${c}].field`)"
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
          label="Values"
          multiple
          chips
          closable-chips
          density="compact"
          variant="outlined"
          :error-messages="diag(`${base}.points_when[${c}].in`)"
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
          :hint="cond.and?.length ? `and ${cond.and.length} more (edit in Code)` : ''"
          persistent-hint
          :error-messages="diag(`${base}.points_when[${c}].${op}`)"
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
      <v-text-field
        :model-value="cond.points"
        label="Points"
        type="number"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${base}.points_when[${c}].points`)"
        @update:model-value="v => (cond.points = Number(v))"
      />
      <v-btn
        aria-label="Remove condition"
        icon="mdi-close"
        size="small"
        variant="text"
        @click="remove('points_when', c)"
      />
    </div>
    <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="addCondition">
      Condition
    </v-btn>
  </div>
</template>

<script setup lang="ts">
  import { keepTypes, setText, type DiagFn, type ItemType, type PointsWhen } from './pointModel'

  defineProps<{ base: string; diag: DiagFn }>()
  const item = defineModel<ItemType>('item', { required: true })

  const OPS = [
    { title: 'is one of', value: 'in' },
    { title: 'is filled in', value: 'present' },
    { title: '>', value: 'gt' },
    { title: '≥', value: 'gte' },
    { title: '<', value: 'lt' },
    { title: '≤', value: 'lte' }
  ] as const
  type Op = (typeof OPS)[number]['value']
  const NUMERIC = ['gt', 'gte', 'lt', 'lte'] as const
  type Bound = (typeof NUMERIC)[number]

  /** The numeric bounds a condition holds (gte + lte is a range); none means a value list. */
  const bounds = (cond: PointsWhen): Bound[] => NUMERIC.filter(op => op in cond)

  /** A condition without bounds tests a value list or that the field is filled in. */
  const listOp = (cond: PointsWhen): Op => (cond.present === true ? 'present' : 'in')

  /** Change one test; a bound keeps its value and the other bound stays. */
  const setOp = (cond: PointsWhen, from: Op, picked: string) => {
    const to = picked as Op // one of OPS: the select offers nothing else
    if (from === to) return
    if (to === 'in' || to === 'present') {
      for (const key of [...NUMERIC, 'in', 'present']) delete cond[key]
      if (to === 'in') cond.in = []
      else cond.present = true
      return
    }
    const bound = from !== 'in' && from !== 'present'
    const value = bound ? (cond[from] ?? 0) : 0
    delete cond[bound ? from : 'in']
    delete cond.present
    cond[to] = value
  }

  const addBound = (cond: PointsWhen) => {
    const [only] = bounds(cond)
    cond[only === 'gt' || only === 'gte' ? 'lte' : 'gte'] = 0
  }

  const setValue = (cond: PointsWhen, op: Bound, value: unknown) => {
    cond[op] = Number(value)
  }

  const addCondition = () => {
    item.value.points_when = [...(item.value.points_when ?? []), { field: '', in: [], points: 0 }]
  }
  const addStep = () => {
    item.value.steps = [...(item.value.steps ?? []), { min: 0, points: 0 }]
  }
  const remove = (key: 'steps' | 'points_when', at: number) => {
    const list = (item.value[key] ?? []).filter((_, i) => i !== at)
    if (list.length) item.value[key] = list as never
    else delete item.value[key]
  }
</script>

<style scoped>
  .op {
    max-width: 140px;
  }
</style>
