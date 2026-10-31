<template>
  <div>
    <v-alert
      v-for="d in general"
      :key="d.message"
      :type="d.severity"
      variant="tonal"
      density="compact"
      class="mb-3"
      :text="d.message"
    />
    <v-alert v-if="!shape" type="info" variant="tonal" class="mb-3">
      This workflow is not a list of states or a stage map; edit it in the Advanced JSON tab.
      <template v-if="!readonly && modelValue == null" #append>
        <v-btn variant="flat" color="primary" @click="start">Create workflow</v-btn>
      </template>
    </v-alert>

    <template v-else>
      <!-- Every stage works on this schema's one form and scoring -->
      <div class="d-flex flex-wrap ga-2 mb-3">
        <v-btn variant="tonal" prepend-icon="mdi-form-select" @click="emit('open', 'fields')">
          Open form
        </v-btn>
        <v-btn
          v-if="hasScoring"
          variant="tonal"
          prepend-icon="mdi-calculator"
          @click="emit('open', 'scoring')"
        >
          Open scoring
        </v-btn>
      </div>
      <v-select
        v-if="shape === 'list'"
        :model-value="initialState"
        :items="names"
        label="Initial state"
        variant="outlined"
        density="compact"
        class="initial mb-2"
        :readonly="readonly"
        clearable
        @update:model-value="
          v => edit(wf => (v ? (wf.initial_state = v) : delete wf.initial_state))
        "
      />
      <v-table density="compact">
        <thead>
          <tr>
            <th>Stage</th>
            <th>Description</th>
            <th>Next stages</th>
            <th v-if="shape === 'map'">Reviewers</th>
            <th v-if="!readonly" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="name in names" :key="name" :data-testid="`stage-${name}`">
            <td>
              <span class="font-mono">{{ name }}</span>
              <div v-for="m in stageDiag(name)" :key="m" class="text-body-small text-error">
                {{ m }}
              </div>
            </td>
            <td>
              <v-text-field
                :model-value="String(stageNode(modelValue, name)?.description ?? '')"
                :aria-label="`Description of ${name}`"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="v => setKey(name, 'description', v)"
              />
            </td>
            <td>
              <v-select
                :model-value="nextOf(modelValue, name)"
                :items="names.filter(n => n !== name)"
                :aria-label="`Next stages of ${name}`"
                multiple
                chips
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="v => edit(wf => setNext(wf, name, v))"
              />
            </td>
            <td v-if="shape === 'map'">
              <v-text-field
                v-if="name === 'review'"
                :model-value="stageNode(modelValue, name)?.reviewers_required ?? ''"
                aria-label="Reviewers required"
                type="number"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="v => setKey(name, 'reviewers_required', v, true)"
              />
            </td>
            <td v-if="!readonly" class="text-right">
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                :aria-label="`Remove stage ${name}`"
                @click="edit(wf => removeStage(wf, name))"
              />
            </td>
          </tr>
        </tbody>
      </v-table>
      <div v-if="!readonly" class="d-flex align-center ga-2 mt-3">
        <v-text-field
          v-model="newName"
          label="New stage"
          density="compact"
          variant="outlined"
          hide-details="auto"
          class="initial"
          :error-messages="names.includes(newName.trim()) ? ['A stage with this name exists'] : []"
          @keyup.enter="add"
        />
        <v-btn variant="tonal" prepend-icon="mdi-plus" :disabled="!canAdd" @click="add">
          Add stage
        </v-btn>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { clone } from './fieldModel'
  import {
    addStage,
    nextOf,
    removeStage,
    setNext,
    shapeOf,
    stageNames,
    stageNode,
    stagePaths
  } from './workflowModel'
  import type { Diagnostic } from './scoring/usePointModelChecks'

  type Rec = Record<string, unknown>

  // Table builder for `workflow_states` (#282); the Advanced JSON tab is its code view
  const props = defineProps<{
    modelValue: unknown
    diagnostics?: Diagnostic[]
    /** The schema has a scoring configuration: stages offer the scoring builder too */
    hasScoring?: boolean
    readonly?: boolean
  }>()
  const emit = defineEmits<{
    'update:modelValue': [value: unknown]
    open: [builder: 'fields' | 'scoring']
  }>()

  const shape = computed(() => shapeOf(props.modelValue))
  const names = computed(() => stageNames(props.modelValue))
  const initialState = computed(() => {
    const value = (props.modelValue as Rec).initial_state
    return value == null ? null : String(value)
  })
  const newName = ref('')
  const canAdd = computed(() => {
    const name = newName.value.trim()
    return !!name && !names.value.includes(name)
  })

  const diags = computed(() =>
    (props.diagnostics ?? []).filter(d => d.field.startsWith('workflow_states'))
  )
  const general = computed(() => diags.value.filter(d => d.field === 'workflow_states'))
  const stageDiag = (name: string) =>
    diags.value
      .filter(d =>
        stagePaths(name).some(
          p => d.field === p || d.field.startsWith(`${p}.`) || d.field.startsWith(`${p}[`)
        )
      )
      .map(d => d.message)

  /** Change a copy and emit it: the draft only changes through v-model. */
  const edit = (change: (wf: Rec) => unknown) => {
    const next = clone(props.modelValue) as Rec
    change(next)
    emit('update:modelValue', next)
  }

  /** Blank removes the key; `numeric` stores a number. */
  const setKey = (name: string, key: string, value: unknown, numeric = false) =>
    edit(wf => {
      const node = stageNode(wf, name)
      if (!node) return
      if (value === '' || value == null) delete node[key]
      else node[key] = numeric ? Number(value) : value
    })

  const add = () => {
    if (!canAdd.value) return
    edit(wf => addStage(wf, newName.value.trim()))
    newName.value = ''
  }

  // The skeleton a new schema gets (SchemaManagement createSchema)
  const start = () =>
    emit('update:modelValue', {
      states: [{ name: 'draft' }, { name: 'submitted' }],
      transitions: { draft: ['submitted'], submitted: [] },
      initial_state: 'draft'
    })
</script>

<style scoped>
  .initial {
    max-width: 280px;
  }
</style>
