<template>
  <v-container fluid class="catalogue">
    <header class="catalogue__head">
      <h1 class="text-headline-small">Genes</h1>
      <span class="text-body-medium text-medium-emphasis tabular">{{ store.total }} in view</span>
    </header>

    <DataTable
      v-model:search="search"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="sortBy"
      v-model:density="density"
      v-model:filters="filters"
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
          :scopes="store.availableScopes"
          :model-value="shownIds"
          :mine="mineIds"
          @update:model-value="setScopes"
        />
      </template>

      <template #item.approved_symbol="{ item }">
        <router-link :to="`/genes/${item.gene_id}`" class="gene-link mono">
          {{ item.approved_symbol }}
        </router-link>
        <div class="text-caption text-medium-emphasis mono">{{ item.hgnc_id }}</div>
      </template>

      <template v-for="s in store.scopes" :key="s.id" #[`item.scope:${s.id}`]="{ item }">
        <template v-for="c in [cellOf(item, s.id)]" :key="c?.curation_id ?? s.id">
          <router-link
            v-if="c"
            :to="`/scopes/${s.id}/curations/${c.curation_id}`"
            class="cell-link"
            :aria-label="`Open ${item.approved_symbol} curation in ${s.display_name}`"
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
          </router-link>
          <span v-else class="text-medium-emphasis">not in scope</span>
        </template>
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
  import { curationStatusLabel } from '@/config/status'
  import { useAuthStore } from '@/stores/auth'
  import { useCatalogueMatrixStore } from '@/stores/catalogueMatrix'
  import { useScopesStore } from '@/stores/scopes'
  import type { Schema } from '@/types/api'

  type Row = Schema<'MatrixRow'>

  const AGREEMENT_LABELS: Record<string, string> = {
    agree: 'Agree',
    disagree: 'Disagree',
    single: 'One scope',
    none: '—'
  }
  const filterDefs = [
    {
      key: 'agreement',
      label: 'Agreement',
      options: [
        { value: 'agree', title: 'Agree' },
        { value: 'disagree', title: 'Disagree' }
      ]
    }
  ]

  const store = useCatalogueMatrixStore()
  const scopesStore = useScopesStore()
  const auth = useAuthStore()
  const { search, page, itemsPerPage, sortBy, density, filters } = useTableUrlState({
    filterKeys: ['agreement', 'scopes'],
    multiKeys: ['scopes']
  })

  // The URL wins over the saved default view, so a shared link shows the same columns.
  const shownIds = computed(() => {
    const urlScopes = filters.value.scopes
    return Array.isArray(urlScopes) && urlScopes.length ? urlScopes : store.defaultShownIds
  })
  const mineIds = computed(() => scopesStore.userScopes.filter(s => s.user_role).map(s => s.id))

  const headers = computed(() => [
    { title: 'Gene', key: 'approved_symbol', sortable: true },
    ...store.scopes.map(s => ({ title: s.display_name, key: `scope:${s.id}`, sortable: false })),
    { title: 'Agreement', key: 'agreement', sortable: false }
  ])

  const cellOf = (row: Row, scopeId: string) => row.cells?.find(c => c.scope_id === scopeId)

  function setScopes(ids: string[]) {
    store.saveDefault(ids)
    filters.value = { ...filters.value, scopes: ids }
  }

  const ready = ref(false)
  function load() {
    const agreement = filters.value.agreement
    return store.fetch({
      scopeIds: shownIds.value,
      search: search.value,
      agreement: agreement === 'agree' || agreement === 'disagree' ? agreement : undefined,
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
      sortBy.value[0]?.order,
      ready.value
    ],
    () => ready.value && load()
  )

  onMounted(async () => {
    const mine = auth.isAuthenticated ? scopesStore.fetchUserScopes().catch(() => []) : null
    await Promise.all([store.loadScopes(), mine])
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
