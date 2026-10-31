<template>
  <v-menu :close-on-content-click="false" location="bottom end">
    <template #activator="{ props: menu }">
      <v-btn v-bind="menu" data-testid="scope-picker" variant="outlined" size="small">
        Scopes shown: {{ modelValue.length }} of {{ scopes.length }}
      </v-btn>
    </template>
    <v-card class="scope-picker" min-width="300" max-width="360">
      <div class="pa-3">
        <v-text-field
          v-model="query"
          data-testid="scope-search"
          :placeholder="`Find a scope (${scopes.length})`"
          density="compact"
          variant="outlined"
          hide-details
          clearable
          aria-label="Find a scope"
        />
        <div class="d-flex flex-wrap ga-2 mt-2">
          <v-chip
            v-if="mine.length"
            data-testid="preset-mine"
            size="small"
            variant="outlined"
            @click="emit('update:modelValue', mine.slice(0, MAX))"
          >
            My scopes
          </v-chip>
          <v-chip
            v-if="withResults.length"
            data-testid="preset-results"
            size="small"
            variant="outlined"
            @click="emit('update:modelValue', withResults.slice(0, MAX))"
          >
            With results
          </v-chip>
          <v-chip
            data-testid="preset-disagreements"
            size="small"
            variant="outlined"
            @click="emit('disagreements')"
          >
            Disagreements
          </v-chip>
          <v-chip
            data-testid="preset-all"
            size="small"
            variant="outlined"
            @click="emit('update:modelValue', all.slice(0, MAX))"
          >
            All {{ scopes.length }}
          </v-chip>
        </div>
      </div>
      <v-divider />
      <v-list density="compact" class="scope-picker__order" aria-label="Column order">
        <v-list-subheader>Column order</v-list-subheader>
        <v-list-item
          v-for="(id, i) in modelValue"
          :key="id"
          :data-testid="`order-${id}`"
          class="py-0 scope-picker__drag"
          draggable="true"
          @dragstart="dragFrom = i"
          @dragover.prevent
          @drop.prevent="dragFrom !== null && move(dragFrom, i)"
        >
          <v-list-item-title class="text-body-medium">{{ nameOf(id) }}</v-list-item-title>
          <template #append>
            <v-btn
              icon="mdi-chevron-up"
              size="x-small"
              variant="text"
              :disabled="i === 0"
              :aria-label="`Move ${nameOf(id)} left`"
              @click="move(i, i - 1)"
            />
            <v-btn
              icon="mdi-chevron-down"
              size="x-small"
              variant="text"
              :disabled="i === modelValue.length - 1"
              :aria-label="`Move ${nameOf(id)} right`"
              @click="move(i, i + 1)"
            />
          </template>
        </v-list-item>
      </v-list>
      <v-divider />
      <v-list density="compact" class="scope-picker__list">
        <v-list-item v-for="s in visible" :key="s.id" :data-testid="`scope-${s.id}`" class="py-0">
          <v-checkbox
            :model-value="modelValue.includes(s.id)"
            :label="s.display_name"
            density="compact"
            hide-details
            :disabled="
              modelValue.includes(s.id) ? modelValue.length <= 1 : modelValue.length >= MAX
            "
            @update:model-value="toggle(s.id)"
          />
        </v-list-item>
        <v-list-item v-if="!visible.length" class="text-medium-emphasis">
          No scope matches.
        </v-list-item>
      </v-list>
      <v-divider />
      <p class="text-body-small text-medium-emphasis pa-3">
        Up to {{ MAX }} columns. Drag or use the arrows to reorder. Your choice is saved as your
        default view.
      </p>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'

  interface PickerScope {
    id: string
    display_name: string
  }

  /** The matrix endpoint accepts at most this many scopes. */
  const MAX = 50

  const props = withDefaults(
    defineProps<{
      scopes: PickerScope[]
      modelValue: string[]
      mine: string[]
      /** Scopes with at least one active curation. */
      withResults?: string[]
    }>(),
    { withResults: () => [] }
  )
  const emit = defineEmits<{ 'update:modelValue': [string[]]; disagreements: [] }>()

  const query = ref('')
  const all = computed(() => props.scopes.map(s => s.id))
  const visible = computed(() => {
    const q = (query.value ?? '').toLowerCase()
    return props.scopes.filter(s => s.display_name.toLowerCase().includes(q))
  })

  const names = computed(() => new Map(props.scopes.map(s => [s.id, s.display_name])))
  const nameOf = (id: string) => names.value.get(id) ?? id

  // Keep the user's column order: a ticked scope joins at the end.
  function toggle(id: string) {
    const shown = props.modelValue
    emit('update:modelValue', shown.includes(id) ? shown.filter(i => i !== id) : [...shown, id])
  }

  const dragFrom = ref<number | null>(null)
  function move(from: number, to: number) {
    dragFrom.value = null
    if (from === to) return
    const next = [...props.modelValue]
    next.splice(to, 0, ...next.splice(from, 1))
    emit('update:modelValue', next)
  }
</script>

<style scoped>
  .scope-picker__list {
    max-height: 320px;
    overflow-y: auto;
  }

  .scope-picker__order {
    max-height: 200px;
    overflow-y: auto;
  }

  .scope-picker__drag {
    cursor: grab;
  }
</style>
