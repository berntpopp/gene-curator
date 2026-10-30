<template>
  <v-container fluid class="catalogue">
    <header class="catalogue__head">
      <h1 class="page-title text-headline-small">Genes</h1>
      <span class="text-body-medium text-medium-emphasis tabular">{{ store.total }} in view</span>
    </header>

    <DataTable
      v-model:search="search"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="sortBy"
      v-model:density="density"
      v-model:filters="filters"
      storage-key="catalogue"
      :headers="headers"
      :items="store.rows"
      :items-length="store.total"
      :loading="store.loading"
      :error="store.error"
      :filter-defs="filterDefs"
      empty-text="No genes match. Adjust the search, filters or shown scopes."
      @retry="load"
    >
      <template #toolbar-actions>
        <ScopePicker
          :scopes="store.allScopes"
          :model-value="shownIds"
          :mine="mineIds"
          @update:model-value="setScopes"
        />
      </template>

      <template #item.approved_symbol="{ item }">
        <router-link :to="`/genes/${item.gene_id}`" class="gene-link mono">
          {{ item.approved_symbol }}
        </router-link>
        <div class="text-body-small text-medium-emphasis mono">{{ item.hgnc_id }}</div>
      </template>

      <template v-for="s in store.scopes" :key="s.id" #[`item.scope:${s.id}`]="{ item }">
        <router-link
          v-for="c in cellsOf(item, s.id)"
          :key="c.curation_id"
          :to="`/scopes/${s.id}/curations/${c.curation_id}`"
          class="cell-link"
          :aria-label="cellLabel(c, item.approved_symbol, s.display_name)"
        >
          <span v-if="c.in_progress" class="text-medium-emphasis">
            {{ curationStatusLabel(c.status) }}
          </span>
          <template v-else>
            <ClassificationMark :classification="c.classification" />
            <span v-if="c.total_score != null" class="score mono">
              {{ c.total_score.toFixed(1) }}
            </span>
          </template>
          <span v-if="c.relationship_type === 'susceptibility'" class="text-medium-emphasis">
            (susceptibility)
          </span>
        </router-link>
        <span v-if="!cellsOf(item, s.id).length" class="text-medium-emphasis">not in scope</span>
      </template>

      <template #item.agreement="{ item }">
        <span :class="['agreement', `agreement--${item.agreement}`]">
          {{ AGREEMENT_LABELS[item.agreement] }}
        </span>
      </template>
    </DataTable>
  </v-container>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue'
  import DataTable from '@/components/common/DataTable.vue'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import ScopePicker from '@/components/catalogue/ScopePicker.vue'
  import { useTableUrlState } from '@/composables/useTableUrlState'
  import {
    compareClassifications,
    getClassification,
    registerClassifications
  } from '@/config/classification'
  import { curationStatusLabel } from '@/config/status'
  import { useAuthStore } from '@/stores/auth'
  import { useCatalogueMatrixStore } from '@/stores/catalogueMatrix'
  import { useScopesStore } from '@/stores/scopes'
  import type { Schema } from '@/types/api'

  type Row = Schema<'MatrixRow'>
  type Cell = Schema<'MatrixCell'>

  const AGREEMENT_LABELS: Record<string, string> = {
    agree: 'Agree',
    disagree: 'Disagree',
    single: 'One scope',
    none: '—'
  }
  const store = useCatalogueMatrixStore()
  // each scope's declared classes label and colour its custom keys (#539)
  watch(
    () => store.scopes,
    list => list.forEach(s => registerClassifications(s.classifications)),
    { immediate: true }
  )
  const filterDefs = computed(() => [
    {
      key: 'agreement',
      label: 'Agreement',
      options: [
        { value: 'agree', title: 'Agree' },
        { value: 'disagree', title: 'Disagree' }
      ]
    },
    {
      key: 'classification',
      label: 'Classification',
      options: [...store.classifications]
        .sort(compareClassifications)
        .map(value => ({ value, title: getClassification(value).label }))
    }
  ])

  const scopesStore = useScopesStore()
  const auth = useAuthStore()
  const { search, page, itemsPerPage, sortBy, density, filters } = useTableUrlState({
    filterKeys: ['agreement', 'classification', 'scopes'],
    multiKeys: ['scopes']
  })

  // The URL wins over the saved default view, so a shared link shows the same columns.
  const shownIds = computed(() => {
    const urlScopes = filters.value.scopes
    // Unknown ids and more than the endpoint accepts would only earn a 422.
    const known = new Set(store.allScopes.map(s => s.id))
    const valid = Array.isArray(urlScopes) ? urlScopes.filter(id => known.has(id)).slice(0, 50) : []
    return valid.length ? valid : store.defaultShownIds
  })
  const mineIds = computed(() => scopesStore.userScopes.filter(s => s.user_role).map(s => s.id))

  const headers = computed(() => [
    { title: 'Gene', key: 'approved_symbol', sortable: true },
    ...store.scopes.map(s => ({ title: s.display_name, key: `scope:${s.id}`, sortable: false })),
    { title: 'Agreement', key: 'agreement', sortable: false }
  ])

  // The accessible name starts with the visible text (WCAG 2.5.3 Label in Name).
  function cellLabel(c: Cell, symbol: string, scope: string) {
    const visible = c.in_progress
      ? curationStatusLabel(c.status)
      : getClassification(c.classification).label
    const score = !c.in_progress && c.total_score != null ? ` ${c.total_score.toFixed(1)}` : ''
    const type = c.relationship_type === 'susceptibility' ? ' (susceptibility)' : ''
    return `${visible}${score}${type}, open ${symbol} curation in ${scope}`
  }

  // one cell per relationship type, so a susceptibility curation never hides the mendelian one
  const cellsOf = (row: Row, scopeId: string) =>
    row.cells?.filter(c => c.scope_id === scopeId) ?? []

  function setScopes(ids: string[]) {
    store.saveDefault(ids)
    filters.value = { ...filters.value, scopes: ids }
  }

  const ready = ref(false)
  function load() {
    const agreement = filters.value.agreement
    const classification = filters.value.classification
    return store.fetch({
      scopeIds: shownIds.value,
      search: search.value,
      agreement: agreement === 'agree' || agreement === 'disagree' ? agreement : undefined,
      classification: typeof classification === 'string' ? classification : undefined,
      page: page.value,
      size: itemsPerPage.value,
      desc: sortBy.value[0]?.order === 'desc'
    })
  }

  watch(
    () => [
      shownIds.value.join(),
      search.value,
      page.value,
      itemsPerPage.value,
      filters.value.agreement,
      filters.value.classification,
      sortBy.value[0]?.order,
      ready.value
    ],
    () => ready.value && load()
  )

  watch(
    () => scopesStore.userScopes,
    list =>
      store.setMemberScopes(
        list.filter(s => s.user_role).map(s => ({ id: s.id, display_name: s.display_name }))
      ),
    { immediate: true }
  )

  // Authentication settles after mount (/me), so follow it instead of reading it once.
  watch(
    () => auth.isAuthenticated,
    signedIn => signedIn && scopesStore.fetchUserScopes().catch(() => []),
    { immediate: true }
  )

  onMounted(async () => {
    void store.loadClassifications()
    await store.loadScopes()
    ready.value = true
  })
</script>

<style scoped>
  .catalogue__head {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 12px;
  }

  .mono {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
  }

  .tabular,
  .score {
    font-variant-numeric: tabular-nums;
  }

  .score {
    margin-left: 8px;
    color: rgb(var(--v-theme-on-surface));
  }

  .gene-link,
  .cell-link {
    color: inherit;
    text-decoration: none;
  }

  .cell-link {
    display: block;
  }

  .gene-link {
    font-weight: 600;
  }

  .gene-link:hover,
  .gene-link:focus-visible,
  .cell-link:hover,
  .cell-link:focus-visible {
    color: rgb(var(--v-theme-secondary));
    text-decoration: underline;
  }

  .agreement--agree {
    color: rgb(var(--v-theme-success));
  }

  .agreement--disagree {
    color: rgb(var(--v-theme-warning));
    font-weight: 600;
  }

  .agreement--single,
  .agreement--none {
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  /* Rows where scopes disagree are tinted so they stand out without a colour per cell. */
  .catalogue :deep(tbody tr:has(.agreement--disagree) > td:not(:first-child)) {
    background: rgba(var(--v-theme-warning), 0.08);
  }
</style>
