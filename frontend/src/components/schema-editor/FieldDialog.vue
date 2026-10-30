<template>
  <v-dialog :model-value="!!field" max-width="760" scrollable @update:model-value="close">
    <v-card v-if="draft">
      <v-card-title>{{ isNew ? 'Add field' : `Edit field: ${field?.id}` }}</v-card-title>
      <v-card-text>
        <v-form ref="form" @submit.prevent="save">
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="draft.id"
                label="Field id"
                hint="Key in the evidence data. Renaming updates conditions and the form layout"
                persistent-hint
                variant="outlined"
                :rules="[idRule]"
              />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="label" label="Label" variant="outlined" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-select v-model="draft.type" :items="FIELD_TYPES" label="Type" variant="outlined" />
            </v-col>
            <v-col cols="12" sm="6" class="d-flex flex-wrap ga-4">
              <v-switch v-model="draft.required" label="Required" color="primary" hide-details />
              <v-switch
                v-model="draft.llm_share"
                label="Share with LLM"
                color="primary"
                hide-details
              />
            </v-col>
            <v-col cols="12">
              <v-textarea
                v-model="helpText"
                label="Help text"
                variant="outlined"
                rows="2"
                auto-grow
              />
            </v-col>

            <v-col v-if="isChoice" cols="12">
              <div class="text-title-small mb-2">Choices</div>
              <div
                v-for="(option, i) in options"
                :key="i"
                class="d-flex align-center ga-2 mb-2"
                :data-testid="`option-${i}`"
              >
                <v-text-field
                  v-model="option.value"
                  label="Value"
                  density="compact"
                  variant="outlined"
                  hide-details
                />
                <v-text-field
                  v-model="option.label"
                  label="Label"
                  density="compact"
                  variant="outlined"
                  hide-details
                />
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="small"
                  :aria-label="`Remove choice ${option.value || i + 1}`"
                  @click="options.splice(i, 1)"
                />
              </div>
              <v-btn
                variant="tonal"
                size="small"
                prepend-icon="mdi-plus"
                @click="options.push({ value: '', label: '' })"
              >
                Add choice
              </v-btn>
            </v-col>

            <v-col v-if="draft.type === 'evidence_table'" cols="12">
              <ColumnsEditor v-model="columns" />
            </v-col>

            <v-col cols="12">
              <div class="text-title-small mb-2">Show when</div>
              <v-alert v-if="complexCondition" type="info" variant="tonal" density="compact">
                This field has a multi-part condition; edit it in the Advanced JSON tab.
              </v-alert>
              <v-row v-else dense>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="conditionField"
                    :items="otherIds"
                    label="Show only when field"
                    variant="outlined"
                    clearable
                    hint="Empty: always shown"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model="conditionValues"
                    label="has one of the values"
                    hint="Comma separated, e.g. AD, AR or true"
                    persistent-hint
                    variant="outlined"
                    :disabled="!conditionField"
                    :rules="[valuesRule]"
                  />
                </v-col>
              </v-row>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Cancel</v-btn>
        <v-btn color="primary" variant="flat" @click="save">
          {{ isNew ? 'Add field' : 'Apply' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import ColumnsEditor from './ColumnsEditor.vue'
  import {
    CHOICE_TYPES,
    FIELD_TYPES,
    clone,
    formatValues,
    parseValues,
    type FieldDef
  } from './fieldModel'

  type Def = Record<string, unknown>

  // Edits a copy of one field; keys the form does not show are kept as they are
  const props = defineProps<{
    /** The field to edit; one without an id is a new field; null closes the dialog */
    field: FieldDef | null
    /** Ids of the other fields (uniqueness, show_when targets) */
    otherIds: string[]
  }>()
  const emit = defineEmits<{ save: [field: FieldDef]; close: [] }>()

  const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const draft = ref<FieldDef | null>(null)
  const options = ref<Array<{ value: string; label: string }>>([])
  const columns = ref<Record<string, Def> | undefined>()
  const conditionField = ref<string | null>(null)
  const conditionValues = ref('')

  const isNew = computed(() => !props.field?.id)
  const isChoice = computed(() => CHOICE_TYPES.includes(String(draft.value?.type)))
  // Seeds use `label` and `help_text`; keep whichever key a field already uses
  const labelKey = computed(() =>
    draft.value && 'title' in draft.value && !('label' in draft.value) ? 'title' : 'label'
  )
  const helpKey = computed(() =>
    draft.value && 'hint' in draft.value && !('help_text' in draft.value) ? 'hint' : 'help_text'
  )
  const condKey = computed(() => (draft.value?.visible_when ? 'visible_when' : 'show_when'))
  const condition = computed(() => draft.value?.[condKey.value] as Def | undefined)
  const complexCondition = computed(
    () => !!condition.value && Object.keys(condition.value).length !== 1
  )

  const text = (key: () => string) =>
    computed({
      get: () => String(draft.value?.[key()] ?? ''),
      set: v => {
        if (draft.value) draft.value[key()] = v
      }
    })
  const label = text(() => labelKey.value)
  const helpText = text(() => helpKey.value)

  watch(
    () => props.field,
    field => {
      draft.value = field ? clone(field) : null
      if (!draft.value) return
      options.value = clone((draft.value.options ?? []) as typeof options.value)
      columns.value = draft.value.columns as Record<string, Def> | undefined
      const [entry] = Object.entries(condition.value ?? {})
      conditionField.value = entry?.[0] ?? null
      conditionValues.value = entry ? formatValues(entry[1]) : ''
    },
    { immediate: true }
  )

  const idRule = (v: string) => {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(v ?? '')) {
      return 'Letters, digits and _ only, starting with a letter'
    }
    return props.otherIds.includes(v) ? 'Another field already uses this id' : true
  }

  const close = () => emit('close')

  const valuesRule = (v: string) =>
    !conditionField.value || !!v?.trim() || 'Enter at least one value'

  /** An empty key the field did not have before is dropped, not stored as "" or false */
  const prune = (def: Def, key: string) => {
    const empty = def[key] === '' || def[key] === false || def[key] == null
    if (empty && !(key in (props.field ?? {}))) delete def[key]
  }

  const save = async () => {
    if (!draft.value || !form.value) return
    if (!(await form.value.validate()).valid) return
    const def = draft.value
    if (isChoice.value) def.options = options.value.filter(o => String(o.value).trim())
    if (def.type === 'evidence_table') def.columns = columns.value ?? {}
    if (!complexCondition.value) {
      if (conditionField.value) {
        def[condKey.value] = { [conditionField.value]: parseValues(conditionValues.value) }
      } else delete def[condKey.value]
    }
    for (const key of [labelKey.value, helpKey.value, 'required', 'llm_share']) prune(def, key)
    emit('save', def)
  }
</script>
