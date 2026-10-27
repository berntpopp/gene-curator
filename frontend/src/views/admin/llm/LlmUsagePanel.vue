<template>
  <h2 class="text-title-large mb-2">Usage this month</h2>
  <DataTable
    v-model:search="usageTable.search.value"
    v-model:page="usageTable.page.value"
    v-model:items-per-page="usageTable.itemsPerPage.value"
    v-model:sort-by="usageTable.sortBy.value"
    v-model:density="usageTable.density.value"
    storage-key="llm-usage"
    :headers="USAGE_HEADERS"
    :items="usageTable.shown.value"
    :items-length="usageTable.total.value"
    :loading="store.loading"
    empty-text="No LLM runs this month."
    class="mb-8"
  >
    <template #item.cost_cents="{ item }">{{ dollars(item.cost_cents) }}</template>
  </DataTable>

  <h2 class="text-title-large mb-2">Runs</h2>
  <DataTable
    v-model:search="runsTable.search.value"
    v-model:page="runsTable.page.value"
    v-model:items-per-page="runsTable.itemsPerPage.value"
    v-model:sort-by="runsTable.sortBy.value"
    v-model:density="runsTable.density.value"
    storage-key="llm-runs"
    :headers="RUN_HEADERS"
    :items="runsTable.shown.value"
    :items-length="runsTable.total.value"
    :loading="store.loading"
    empty-text="No runs yet."
  >
    <template #item.created_at="{ item }">{{ formatDateTime(item.created_at) }}</template>
    <template #item.cost_cents="{ item }">{{ dollars(item.cost_cents) }}</template>
    <template #item.duration_ms="{ item }">
      {{ item.duration_ms == null ? EMPTY : `${item.duration_ms} ms` }}
    </template>
  </DataTable>
</template>

<script setup lang="ts">
  import { computed, onMounted } from 'vue'
  import DataTable from '@/components/common/DataTable.vue'
  import { useLlmStore } from '@/stores/llm'
  import { useScopesStore } from '@/stores/scopes'
  import { EMPTY, formatDateTime } from '@/utils/format'
  import { useLlmTable } from './useLlmTable'

  const USAGE_HEADERS = [
    { title: 'Scope', key: 'scope', hideable: false },
    { title: 'Runs', key: 'runs' },
    { title: 'Input tokens', key: 'input_tokens' },
    { title: 'Output tokens', key: 'output_tokens' },
    { title: 'Cost', key: 'cost_cents' }
  ]
  const RUN_HEADERS = [
    { title: 'Started', key: 'created_at', hideable: false },
    { title: 'Scope', key: 'scope' },
    { title: 'Strategy', key: 'strategy' },
    { title: 'Model', key: 'model_id' },
    { title: 'Status', key: 'status' },
    { title: 'Input tokens', key: 'input_tokens' },
    { title: 'Output tokens', key: 'output_tokens' },
    { title: 'Cost', key: 'cost_cents' },
    { title: 'Duration', key: 'duration_ms' },
    { title: 'Error', key: 'error_code' }
  ]

  const store = useLlmStore()
  const scopes = useScopesStore()
  const scopeName = (id: string) => scopes.scopes.find(s => s.id === id)?.name ?? id
  const dollars = (cents: string) => `$${(Number(cents) / 100).toFixed(2)}`

  // `scope` is a display column so search and sort work on the name, not the id
  const usageRows = computed(() => store.usage.map(r => ({ ...r, scope: scopeName(r.scope_id) })))
  const runRows = computed(() => store.runs.map(r => ({ ...r, scope: scopeName(r.scope_id) })))
  const usageTable = useLlmTable('usage', usageRows)
  const runsTable = useLlmTable('runs', runRows)

  onMounted(() => {
    void store.fetchActivity()
    scopes.fetchUserScopes().catch(() => undefined) // names are a nicety; ids still show
  })
</script>
