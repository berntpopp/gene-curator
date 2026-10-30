<template>
  <div>
    <v-alert
      v-if="!layout.sectioned && !readonly"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      This schema stores its fields as one list; its layout lives in the UI configuration (Advanced
      JSON). Nested groups are edited there too.
    </v-alert>
    <v-alert v-if="!layout.sections.length" type="info" variant="tonal" class="mb-4">
      No fields yet. {{ readonly ? 'Edit the schema to add one.' : 'Add a section to start.' }}
    </v-alert>

    <v-card
      v-for="(section, si) in layout.sections"
      :key="si"
      variant="outlined"
      class="mb-4"
      :data-testid="`section-${si}`"
    >
      <v-card-item>
        <div v-if="layout.sectioned && !readonly" class="d-flex flex-wrap ga-2">
          <v-text-field
            :model-value="section.label"
            label="Section title"
            density="compact"
            variant="outlined"
            hide-details
            class="flex-grow-1"
            @update:model-value="v => edit(l => (l.sections[si]!.label = v))"
          />
          <v-text-field
            :model-value="section.description"
            label="Section description"
            density="compact"
            variant="outlined"
            hide-details
            class="flex-grow-1"
            @update:model-value="v => edit(l => (l.sections[si]!.description = v))"
          />
          <div class="d-flex align-center">
            <v-btn
              v-for="action in sectionActions(si)"
              :key="action.icon"
              :icon="action.icon"
              :aria-label="action.label"
              :disabled="action.disabled"
              variant="text"
              size="small"
              @click="action.run"
            />
          </div>
        </div>
        <template v-else>
          <v-card-title class="px-0">{{ section.label || section.id }}</v-card-title>
          <v-card-subtitle v-if="section.description" class="px-0">
            {{ section.description }}
          </v-card-subtitle>
        </template>
      </v-card-item>

      <v-list density="compact" class="py-0">
        <v-list-item
          v-for="(field, fi) in section.fields"
          :key="field.id"
          :data-testid="`field-${field.id}`"
        >
          <v-list-item-title>
            {{ field.label ?? field.title ?? field.id }}
            <span class="text-medium-emphasis text-body-small ml-2 font-mono">{{ field.id }}</span>
          </v-list-item-title>
          <v-list-item-subtitle class="d-flex flex-wrap ga-1 mt-1">
            <v-chip size="x-small" label>{{ typeTitle(field.type) }}</v-chip>
            <v-chip v-if="field.required" size="x-small" label color="primary">Required</v-chip>
            <v-chip v-if="field.show_when || field.visible_when" size="x-small" label>
              Conditional
            </v-chip>
            <v-chip v-if="field.llm_share" size="x-small" label color="info">LLM</v-chip>
          </v-list-item-subtitle>
          <template v-if="!readonly" #append>
            <v-btn
              v-for="action in fieldActions(si, fi)"
              :key="action.icon"
              :icon="action.icon"
              :aria-label="action.label"
              :disabled="action.disabled"
              variant="text"
              size="small"
              @click="action.run"
            />
          </template>
        </v-list-item>
      </v-list>

      <v-card-actions v-if="!readonly">
        <v-btn variant="tonal" size="small" prepend-icon="mdi-plus" @click="openField(si, -1)">
          Add field
        </v-btn>
      </v-card-actions>
    </v-card>

    <v-btn
      v-if="layout.sectioned && !readonly"
      variant="outlined"
      prepend-icon="mdi-folder-plus"
      @click="addSection"
    >
      Add section
    </v-btn>

    <FieldDialog
      :field="editing?.field ?? null"
      :other-ids="otherIds"
      @save="saveField"
      @close="editing = null"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import FieldDialog from './FieldDialog.vue'
  import { useConfirm } from '@/composables/useConfirm'
  import {
    FIELD_TYPES,
    clone,
    fieldIds,
    move,
    readLayout,
    renumber,
    writeLayout,
    type FieldDef,
    type Layout
  } from './fieldModel'

  // Sections and fields of `field_definitions`, edited without JSON (#219)
  const props = defineProps<{
    modelValue: Record<string, unknown> | null | undefined
    readonly?: boolean
  }>()
  const emit = defineEmits<{ 'update:modelValue': [value: Record<string, unknown>] }>()
  const { confirm } = useConfirm()

  const layout = computed(() => readLayout(props.modelValue))
  const editing = ref<{ si: number; fi: number; field: FieldDef } | null>(null)

  const typeTitle = (type: unknown) =>
    FIELD_TYPES.find(t => t.value === type)?.title ?? String(type ?? 'no type')

  /** Change a copy of the layout and emit it in the stored shape */
  const edit = (change: (l: Layout) => void) => {
    const next = clone(layout.value)
    change(next)
    emit('update:modelValue', writeLayout(next, props.modelValue))
  }

  const otherIds = computed(() => {
    const ids = fieldIds(layout.value)
    const own = editing.value?.field.id
    return own ? ids.filter(id => id !== own) : ids
  })

  const openField = (si: number, fi: number) => {
    const field =
      fi < 0 ? { id: '', type: 'text', label: '' } : layout.value.sections[si]!.fields[fi]!
    editing.value = { si, fi, field }
  }

  const saveField = (field: FieldDef) => {
    const target = editing.value
    if (!target) return
    edit(l => {
      const fields = l.sections[target.si]!.fields
      if (target.fi < 0) fields.push(field)
      else fields[target.fi] = field
      if (target.fi < 0) renumber(l)
    })
    editing.value = null
  }

  const removeField = async (si: number, fi: number) => {
    const field = layout.value.sections[si]!.fields[fi]!
    const ok = await confirm({
      title: `Remove field "${field.label ?? field.id}"?`,
      text: 'Values already saved under this id stay in existing records but are no longer shown.',
      confirmText: 'Remove',
      destructive: true
    })
    if (ok) edit(l => l.sections[si]!.fields.splice(fi, 1))
  }

  const fieldActions = (si: number, fi: number) => {
    const count = layout.value.sections[si]!.fields.length
    const name = layout.value.sections[si]!.fields[fi]!.id
    const shift = (step: number) => () =>
      edit(l => {
        move(l.sections[si]!.fields, fi, step)
        renumber(l)
      })
    return [
      { icon: 'mdi-pencil', label: `Edit ${name}`, disabled: false, run: () => openField(si, fi) },
      { icon: 'mdi-chevron-up', label: `Move ${name} up`, disabled: fi === 0, run: shift(-1) },
      {
        icon: 'mdi-chevron-down',
        label: `Move ${name} down`,
        disabled: fi === count - 1,
        run: shift(1)
      },
      {
        icon: 'mdi-delete',
        label: `Remove ${name}`,
        disabled: false,
        run: () => removeField(si, fi)
      }
    ]
  }

  const addSection = () =>
    edit(l => {
      const ids = new Set(l.sections.map(s => s.id))
      let n = l.sections.length + 1
      while (ids.has(`section_${n}`)) n++
      l.sections.push({ id: `section_${n}`, label: `Section ${n}`, fields: [] })
    })

  const removeSection = async (si: number) => {
    const section = layout.value.sections[si]!
    if (
      section.fields.length &&
      !(await confirm({
        title: `Remove section "${section.label || section.id}" and its ${section.fields.length} fields?`,
        confirmText: 'Remove',
        destructive: true
      }))
    ) {
      return
    }
    edit(l => l.sections.splice(si, 1))
  }

  const sectionActions = (si: number) => {
    const name = layout.value.sections[si]!.label || layout.value.sections[si]!.id
    const last = layout.value.sections.length - 1
    return [
      {
        icon: 'mdi-chevron-up',
        label: `Move section ${name} up`,
        disabled: si === 0,
        run: () => edit(l => move(l.sections, si, -1))
      },
      {
        icon: 'mdi-chevron-down',
        label: `Move section ${name} down`,
        disabled: si === last,
        run: () => edit(l => move(l.sections, si, 1))
      },
      {
        icon: 'mdi-delete',
        label: `Remove section ${name}`,
        disabled: false,
        run: () => removeSection(si)
      }
    ]
  }
</script>
