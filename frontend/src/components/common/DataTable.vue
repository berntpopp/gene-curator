<template>
  <div class="data-table" :class="`data-table--${density}`">
    <div class="data-table__toolbar">
      <v-text-field
        :model-value="search"
        placeholder="Search"
        prepend-inner-icon="mdi-magnify"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        class="data-table__search"
        aria-label="Search table"
        @update:model-value="emit('update:search', $event ?? '')"
      />
      <div class="data-table__chips">
        <v-menu v-for="f in filterDefs" :key="f.key" :close-on-content-click="!f.multiple">
          <template #activator="{ props: menu }">
            <v-chip
              v-bind="menu"
              :data-testid="`filter-${f.key}`"
              :color="isActive(f) ? 'secondary' : undefined"
              :variant="isActive(f) ? 'tonal' : 'outlined'"
              :closable="isActive(f)"
              close-label="Clear filter"
              size="small"
              @click:close="setFilter(f, undefined)"
            >
              {{ f.label }}<template v-if="isActive(f)">: {{ activeTitles(f) }}</template>
            </v-chip>
          </template>
          <v-list density="compact">
            <v-list-item
              v-for="o in f.options"
              :key="o.value"
              :title="o.title"
              :active="selected(f).includes(o.value)"
              @click="pick(f, o.value)"
            />
          </v-list>
        </v-menu>
      </div>
      <v-spacer />
      <v-btn-toggle
        :model-value="density"
        mandatory
        density="compact"
        variant="outlined"
        divided
        aria-label="Row density"
        @update:model-value="emit('update:density', $event)"
      >
        <v-btn value="compact" size="small" data-testid="density-compact">Compact</v-btn>
        <v-btn value="comfortable" size="small" data-testid="density-comfortable"
          >Comfortable</v-btn
        >
      </v-btn-toggle>
      <v-menu :close-on-content-click="false">
        <template #activator="{ props: menu }">
          <v-btn
            v-bind="menu"
            data-testid="column-picker"
            variant="text"
            size="small"
            prepend-icon="mdi-table"
          >
            Columns
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item
            v-for="h in headers.filter(c => c.hideable !== false)"
            :key="h.key"
            :data-testid="`column-${h.key}`"
          >
            <v-checkbox
              :model-value="!hidden.has(h.key)"
              :label="h.title"
              density="compact"
              hide-details
              @update:model-value="toggleColumn(h.key)"
            />
          </v-list-item>
        </v-list>
      </v-menu>
      <slot name="toolbar-actions" />
    </div>

    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      data-testid="table-error"
      class="data-table__error"
    >
      {{ error }}
      <template #append>
        <v-btn data-testid="table-retry" variant="text" size="small" @click="emit('retry')">
          Retry
        </v-btn>
      </template>
    </v-alert>

    <v-data-table-server
      v-else
      :headers="visibleHeaders"
      :items="items"
      :items-length="itemsLength"
      :loading="loading"
      :page="page"
      :items-per-page="itemsPerPage"
      :items-per-page-options="PAGE_SIZES"
      :sort-by="sortBy"
      :row-props="rowProps"
      fixed-header
      hover
      class="data-table__grid"
      @update:page="emit('update:page', $event)"
      @update:items-per-page="emit('update:itemsPerPage', $event)"
      @update:sort-by="emit('update:sortBy', $event)"
    >
      <template v-for="name in itemSlots()" #[name]="slotProps" :key="name">
        <slot :name="name as `item.${string}`" v-bind="slotProps" />
      </template>
      <template v-if="!slots['no-data']" #no-data>
        <div data-testid="table-empty" class="data-table__empty">
          {{ emptyText }}
        </div>
      </template>
    </v-data-table-server>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, unknown>">
  import { computed, ref, useSlots, watch } from 'vue'
  import { PAGE_SIZES } from '@/composables/useTableUrlState'
  import type { Density, FilterValue, SortItem } from '@/composables/useTableUrlState'

  interface Header {
    title: string
    key: string
    /** false keeps the column out of the column picker */
    hideable?: boolean
    [k: string]: unknown
  }
  interface FilterDef {
    key: string
    label: string
    options: { value: string; title: string }[]
    /** Multi-select: the filter value is a string[]. */
    multiple?: boolean
  }

  const props = withDefaults(
    defineProps<{
      headers: Header[]
      items: T[]
      /** Server total, not the length of the current page. */
      itemsLength: number
      loading?: boolean
      error?: string | null
      search?: string
      filterDefs?: FilterDef[]
      filters?: Record<string, FilterValue>
      page?: number
      itemsPerPage?: number
      sortBy?: SortItem[]
      density?: Density
      emptyText?: string
      /** Names this table's hidden columns in browser storage; stable across column changes. */
      storageKey: string
      rowProps?: (data: { item: T }) => Record<string, unknown>
    }>(),
    {
      loading: false,
      error: null,
      search: '',
      filterDefs: () => [],
      filters: () => ({}),
      page: 1,
      itemsPerPage: 25,
      sortBy: () => [],
      density: 'comfortable',
      emptyText: 'No results. Adjust the search or filters.',
      rowProps: undefined
    }
  )

  const emit = defineEmits<{
    'update:search': [string]
    'update:filters': [Record<string, FilterValue>]
    'update:page': [number]
    'update:itemsPerPage': [number]
    'update:sortBy': [SortItem[]]
    'update:density': [Density]
    retry: []
  }>()

  // Hidden columns are a per-browser preference, kept per table
  const storeKey = computed(() => `table-columns:${props.storageKey}`)
  function loadHidden(key: string): Set<string> {
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
      return new Set(Array.isArray(saved) ? saved.map(String) : [])
    } catch {
      return new Set()
    }
  }
  const hidden = ref(loadHidden(storeKey.value))
  watch(storeKey, k => (hidden.value = loadHidden(k)))
  const visibleHeaders = computed(() =>
    props.headers.filter(h => h.hideable === false || !hidden.value.has(h.key))
  )

  function toggleColumn(key: string) {
    const next = new Set(hidden.value)
    if (!next.delete(key)) next.add(key)
    hidden.value = next
    try {
      localStorage.setItem(storeKey.value, JSON.stringify([...next]))
    } catch {
      // storage blocked: the choice lasts until reload
    }
  }

  const selected = (f: FilterDef): string[] => [props.filters[f.key] ?? []].flat()
  const isActive = (f: FilterDef) => selected(f).length > 0
  const activeTitles = (f: FilterDef) =>
    selected(f)
      .map(v => f.options.find(o => o.value === v)?.title ?? v)
      .join(', ')

  function setFilter(f: FilterDef, value: FilterValue | undefined) {
    const next = { ...props.filters }
    if (value?.length) next[f.key] = value
    else delete next[f.key]
    emit('update:filters', next)
  }

  function pick(f: FilterDef, value: string) {
    if (!f.multiple) return setFilter(f, value)
    const cur = selected(f)
    setFilter(f, cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value])
  }

  defineSlots<
    {
      [K in `item.${string}`]?: (p: { item: T; value: unknown }) => unknown
    } & {
      'toolbar-actions'?: () => unknown
      'no-data'?: () => unknown
    }
  >()
  const slots = useSlots()
  // A function, not a computed: `slots` is not reactive, and parents add item slots late.
  const itemSlots = () => Object.keys(slots).filter(n => n.startsWith('item.') || n === 'no-data')
</script>

<style scoped>
  .data-table {
    --row-height: 44px;
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-radius: 6px;
    font-variant-numeric: tabular-nums;
  }

  .data-table--compact {
    --row-height: 34px;
  }

  .data-table__toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-bottom: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
  }

  .data-table__search {
    max-width: 280px;
    min-width: 180px;
  }

  .data-table__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .data-table__error {
    margin: 12px;
  }

  /* Pinned left and no wider than the viewport, so a wide table (catalogue at 390 px) keeps it on screen */
  .data-table__empty {
    position: sticky;
    left: 0;
    max-width: calc(100vw - 32px);
    padding: 32px 16px;
    white-space: normal;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
    text-align: center;
  }

  .data-table__grid {
    max-height: 70vh;
  }

  .data-table__grid :deep(tbody td),
  .data-table__grid :deep(thead th) {
    height: var(--row-height);
    white-space: nowrap;
  }

  /* Sticky header comes from fixed-header; pin the first column for wide tables. */
  .data-table__grid :deep(tr > th:first-child),
  .data-table__grid :deep(tr > td:first-child) {
    position: sticky;
    left: 0;
    z-index: 1;
    background: rgb(var(--v-theme-surface));
  }

  .data-table__grid :deep(thead th:first-child) {
    z-index: 3;
  }
</style>
