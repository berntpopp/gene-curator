<template>
  <v-container fluid>
    <div class="mb-4">
      <h1 class="page-title text-headline-medium font-weight-bold">My work</h1>
      <p class="text-body-medium text-medium-emphasis">
        Across your scopes. Sorted by what blocks others first.
      </p>
    </div>

    <PendingInvitations v-if="invitations.hasPendingInvitations" class="mb-4" />

    <v-tabs v-model="tab" density="compact" color="primary" class="work-tabs mb-3">
      <v-tab v-for="t in TABS" :key="t.value" :value="t.value" role="tab">
        {{ t.label }}
        <span class="ml-2 text-medium-emphasis font-mono">{{ store.counts[t.value] ?? 0 }}</span>
      </v-tab>
    </v-tabs>

    <DataTable
      v-model:search="search"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="sortBy"
      v-model:density="density"
      :headers="HEADERS"
      :items="shown"
      :items-length="visible.length"
      :loading="store.loading"
      :error="store.error"
      :empty-text="search ? 'No work matches the search.' : EMPTY_TEXT[tab]"
      :row-props="rowProps"
      storage-key="my-work"
      @retry="store.fetchMyWork()"
    >
      <template #item.gene_symbol="{ item }">
        <span class="font-mono work-gene">{{ item.gene_symbol }}</span>
      </template>
      <template #item.disease_name="{ item }">
        {{ item.disease_name ?? EMPTY }}
        <span v-if="item.mode_of_inheritance" class="text-medium-emphasis">
          · {{ formatInheritance(item.mode_of_inheritance) }}
        </span>
        <span v-if="relationshipLabel(item.relationship_type)" class="text-medium-emphasis">
          · {{ relationshipLabel(item.relationship_type) }}
        </span>
      </template>
      <template #item.stage="{ item }">
        <!-- An assignment has no workflow stage yet; say what it is, not a dash -->
        {{ item.stage ? humanize(item.stage) : item.kind === 'assignment' ? 'Assigned' : EMPTY }}
      </template>
      <template #item.classification="{ item }">
        <ClassificationMark v-if="item.classification" :classification="item.classification" />
        <span v-else class="text-medium-emphasis">{{ EMPTY }}</span>
      </template>
      <template #item.updated_at="{ item }">
        <span class="font-mono text-medium-emphasis">{{ relativeTime(item.updated_at) }}</span>
      </template>
      <template #item.verb="{ item }">
        <v-btn :to="item.link" size="small" variant="outlined" color="primary">
          {{ item.verb }}
        </v-btn>
      </template>
    </DataTable>
    <p class="d-none d-md-block text-body-small text-medium-emphasis mt-3">
      Press <kbd>J</kbd> <kbd>K</kbd> to move, <kbd>Enter</kbd> to open.
    </p>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
  import { useRouter } from 'vue-router'
  import DataTable from '@/components/common/DataTable.vue'
  import { clientPage, relativeTime } from '@/components/common/tableRows'
  import { useTableUrlState } from '@/composables/useTableUrlState'
  import { useMyWorkStore, type WorkItem, type WorkTab } from '@/stores/myWork'
  import { useInvitationsStore } from '@/stores/invitations'
  import PendingInvitations from '@/components/dashboard/PendingInvitations.vue'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { humanize } from '@/components/dynamic/fieldLabels'
  import { formatInheritance, relationshipLabel } from '@/utils/inheritance'
  import { EMPTY } from '@/utils/format'

  const TABS: { value: WorkTab; label: string }[] = [
    { value: 'needs_you', label: 'Needs you' },
    { value: 'waiting', label: 'Waiting' },
    { value: 'done', label: 'Done' }
  ]
  const HEADERS = [
    { title: 'Gene', key: 'gene_symbol' },
    { title: 'Disease', key: 'disease_name' },
    { title: 'Stage', key: 'stage' },
    { title: 'Classification', key: 'classification' },
    { title: 'Scope', key: 'scope_name' },
    { title: 'Age', key: 'updated_at' },
    { title: 'Next action', key: 'verb' }
  ]
  const EMPTY_TEXT: Record<WorkTab, string> = {
    needs_you: 'Nothing needs you right now.',
    waiting: 'Nothing is waiting on others.',
    done: 'Nothing finished this week yet.'
  }

  const router = useRouter()
  const store = useMyWorkStore()
  const invitations = useInvitationsStore()
  const { search, page, itemsPerPage, sortBy, density, filters } = useTableUrlState({
    filterKeys: ['tab']
  })
  const tab = computed<WorkTab>({
    get: () => TABS.find(t => t.value === filters.value.tab)?.value ?? 'needs_you',
    set: v => (filters.value = { tab: v === 'needs_you' ? '' : v })
  })
  const cursor = ref(0)

  // Rows of one next action stay together, in the API's "blocks others first" order
  const visible = computed(() => {
    const q = (search.value ?? '').trim().toLowerCase()
    const byVerb = new Map<string, WorkItem[]>()
    for (const i of store.byTab(tab.value)) {
      if (
        q &&
        !`${i.gene_symbol} ${i.scope_name} ${i.disease_name ?? ''}`.toLowerCase().includes(q)
      )
        continue
      byVerb.set(i.verb, [...(byVerb.get(i.verb) ?? []), i])
    }
    return [...byVerb.values()].flat()
  })
  const shown = computed(() =>
    clientPage(visible.value, {
      sortBy: sortBy.value,
      page: page.value,
      itemsPerPage: itemsPerPage.value
    })
  )
  // J/K follow the rows on screen
  const active = computed(() => shown.value[cursor.value])
  watch([tab, search, page, itemsPerPage, sortBy], () => (cursor.value = 0))
  const rowProps = ({ item }: { item: WorkItem }) => ({
    'data-test': 'work-row',
    class: item === active.value ? 'work-row--active' : undefined,
    'aria-current': item === active.value ? 'true' : undefined
  })

  function onKey(e: KeyboardEvent) {
    // Typing or activating a focused control keeps its own behaviour
    const typing =
      e.target instanceof Element &&
      e.target.closest('input, textarea, select, a, button, [contenteditable]')
    if (typing || e.metaKey || e.ctrlKey || e.altKey || e.defaultPrevented) return
    const last = shown.value.length - 1
    if (e.key === 'j') cursor.value = Math.min(cursor.value + 1, last)
    else if (e.key === 'k') cursor.value = Math.max(cursor.value - 1, 0)
    else if (e.key === 'Enter' && active.value) void router.push(active.value.link)
  }

  onMounted(() => {
    window.addEventListener('keydown', onKey)
    void store.fetchMyWork()
    void invitations.fetchPendingInvitations().catch(() => undefined) // banner only; the list works without it
  })
  onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
  .work-gene {
    font-weight: 600;
  }
  :deep(.work-row--active) > td:first-child {
    box-shadow: inset 3px 0 0 rgb(var(--v-theme-secondary));
  }
  kbd {
    font-family: monospace;
    border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
    border-radius: 3px;
    padding: 0 4px;
  }
</style>
