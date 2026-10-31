<template>
  <div class="py-2">
    <v-row dense>
      <v-col cols="12" sm="4">
        <FieldPicker
          :model-value="item.points_key ?? ''"
          :items="columns"
          label="Points column"
          placeholder="points"
          variant="outlined"
          hint="Row column holding entered points"
          :error-messages="diag(`${base}.points_key`)"
          @update:model-value="v => setText(item, 'points_key', v)"
        />
      </v-col>
      <v-col v-if="item.rule === 'step'" cols="12" sm="4">
        <FieldPicker
          :model-value="item.field ?? ''"
          :items="columns"
          label="Step column"
          placeholder="summed_lod"
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
      fills rows where the curator left the points blank. Times and At most then scale or cap the
      row's points, entered or not.
    </p>
    <div
      v-for="(cond, c) in item.points_when ?? []"
      :key="c"
      class="mb-2"
      :data-testid="`rule-${c}`"
    >
      <div class="d-flex ga-2 align-start">
        <RuleCondition
          :cond="cond"
          :path="`${base}.points_when[${c}]`"
          :diag="diag"
          :columns="columns"
        />
        <v-select
          :model-value="effectOf(cond)"
          :items="EFFECTS"
          label="Effect"
          aria-label="Rule effect"
          density="compact"
          variant="outlined"
          @update:model-value="v => setEffect(cond, v)"
        />
        <v-text-field
          :model-value="cond[effectOf(cond)]"
          :label="EFFECTS.find(e => e.value === effectOf(cond))?.title"
          type="number"
          density="compact"
          variant="outlined"
          :error-messages="diag(`${base}.points_when[${c}].points`)"
          @update:model-value="v => (cond[effectOf(cond)] = Number(v))"
        />
        <v-btn
          aria-label="Remove condition"
          icon="mdi-close"
          size="small"
          variant="text"
          @click="remove('points_when', c)"
        />
      </div>
      <div v-for="(sub, a) in cond.and ?? []" :key="a" class="d-flex ga-2 align-start ml-6">
        <span class="text-label-large mt-2">and</span>
        <RuleCondition
          :cond="sub"
          :path="`${base}.points_when[${c}].and[${a}]`"
          :diag="diag"
          :columns="columns"
        />
        <v-btn
          :aria-label="`Remove and-condition ${a + 1}`"
          icon="mdi-close"
          size="small"
          variant="text"
          @click="removeAnd(cond, a)"
        />
      </div>
      <v-btn
        size="small"
        variant="text"
        prepend-icon="mdi-plus"
        class="ml-6"
        @click="cond.and = [...(cond.and ?? []), { field: '', in: [] }]"
      >
        And
      </v-btn>
    </div>
    <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="addCondition">
      Condition
    </v-btn>
  </div>
</template>

<script setup lang="ts">
  import FieldPicker from './FieldPicker.vue'
  import RuleCondition from './RuleCondition.vue'
  import type { ColumnOption } from './evidenceFields'
  import {
    EFFECTS,
    effectOf,
    setEffect,
    setText,
    type DiagFn,
    type ItemType,
    type PointsWhen
  } from './pointModel'

  withDefaults(defineProps<{ base: string; diag: DiagFn; columns?: ColumnOption[] }>(), {
    columns: () => []
  })
  const item = defineModel<ItemType>('item', { required: true })

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
  /** The last and-condition gone drops `and`, so the rule stores as it was written. */
  const removeAnd = (cond: PointsWhen, at: number) => {
    const rest = (cond.and ?? []).filter((_, i) => i !== at)
    if (rest.length) cond.and = rest
    else delete cond.and
  }
</script>
