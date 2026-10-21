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
        <v-menu v-for="f in filterDefs" :key="f.key">
          <template #activator="{ props: menu }">
            <v-chip
              v-bind="menu"
              :data-testid="`filter-${f.key}`"
              :color="filters[f.key] ? 'secondary' : undefined"
              :variant="filters[f.key] ? 'tonal' : 'outlined'"
              :closable="false"
              size="small"
            >
              {{ f.label
              }}<template v-if="filters[f.key]">: {{ optionTitle(f, filters[f.key]) }}</template>
              <v-icon
                v-if="filters[f.key]"
                :data-testid="`filter-${f.key}-clear`"
                size="small"
                end
                aria-label="Clear filter"
                @click.stop="setFilter(f.key, undefined)"
                >mdi-close</v-icon
              >
            </v-chip>
          </template>
          <v-list density="compact">
            <v-list-item
              v-for="o in f.options"
              :key="o.value"
              :title="o.title"
              :active="filters[f.key] === o.value"
              @click="setFilter(f.key, o.value)"
            />
          </v-list>
        </v-menu>
      </div>
      <v-spacer />
      <v-btn
        data-testid="density-toggle"
        variant="text"
        size="small"
        :aria-label="`Switch to ${density === 'compact' ? 'comfortable' : 'compact'} rows`"
        :prepend-icon="density === 'compact' ? 'mdi-view-list' : 'mdi-view-grid'"
        @click="emit('update:density', density === 'compact' ? 'comfortable' : 'compact')"
      >
        {{ density === 'compact' ? 'Compact' : 'Comfortable' }}
      </v-btn>
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
          <v-list-item v-for="h in headers" :key="h.key" :data-testid="`column-${h.key}`">
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
      :items-per-page-options="[10, 25, 50, 100]"
      :sort-by="sortBy"
      fixed-header
      hover
      class="data-table__grid"
      @update:page="emit('update:page', $event)"
      @update:items-per-page="emit('update:itemsPerPage', $event)"
      @update:sort-by="emit('update:sortBy', $event)"
    >
      <template v-for="(_, name) in $slots" #[name]="slotProps" :key="name">
        <slot :name="name" v-bind="slotProps ?? {}" />
      </template>
      <template v-if="!$slots['no-data']" #no-data>
        <div data-testid="table-empty" class="data-table__empty">
          {{ emptyText }}
        </div>
      </template>
    </v-data-table-server>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import type { Density, SortItem } from '@/composables/useTableUrlState'

  interface Header {
    title: string
    key: string
    [k: string]: unknown
  }
  interface FilterDef {
    key: string
    label: string
    options: { value: string; title: string }[]
  }

  const props = withDefaults(
    defineProps<{
      headers: Header[]
      items: Record<string, unknown>[]
      /** Server total, not the length of the current page. */
      itemsLength: number
      loading?: boolean
      error?: string | null
      search?: string
      filterDefs?: FilterDef[]
      filters?: Record<string, string>
      page?: number
      itemsPerPage?: number
      sortBy?: SortItem[]
      density?: Density
      emptyText?: string
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
      emptyText: 'No results. Adjust the search or filters.'
    }
  )

  const emit = defineEmits<{
    'update:search': [string]
    'update:filters': [Record<string, string>]
    'update:page': [number]
    'update:itemsPerPage': [number]
    'update:sortBy': [SortItem[]]
    'update:density': [Density]
    retry: []
  }>()

  const hidden = ref(new Set<string>())
  const visibleHeaders = computed(() => props.headers.filter(h => !hidden.value.has(h.key)))

  function toggleColumn(key: string) {
    const next = new Set(hidden.value)
    if (!next.delete(key)) next.add(key)
    hidden.value = next
  }

  function setFilter(key: string, value: string | undefined) {
    const next = { ...props.filters }
    if (value) next[key] = value
    else delete next[key]
    emit('update:filters', next)
  }

  const optionTitle = (f: FilterDef, v: string | undefined) =>
    f.options.find(o => o.value === v)?.title ?? v
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

  .data-table__empty {
    padding: 32px 16px;
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
