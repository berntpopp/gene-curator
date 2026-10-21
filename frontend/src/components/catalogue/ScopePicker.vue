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
        Up to {{ MAX }} columns. Your choice is saved as your default view.
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

  const props = defineProps<{ scopes: PickerScope[]; modelValue: string[]; mine: string[] }>()
  const emit = defineEmits<{ 'update:modelValue': [string[]] }>()

  const query = ref('')
  const all = computed(() => props.scopes.map(s => s.id))
  const visible = computed(() => {
    const q = (query.value ?? '').toLowerCase()
    return props.scopes.filter(s => s.display_name.toLowerCase().includes(q))
  })

  // Emit in list order so columns do not jump around as boxes are ticked.
  function toggle(id: string) {
    const next = new Set(props.modelValue)
    if (!next.delete(id)) next.add(id)
    emit(
      'update:modelValue',
      all.value.filter(i => next.has(i))
    )
  }
</script>

<style scoped>
  .scope-picker__list {
    max-height: 320px;
    overflow-y: auto;
  }
</style>
