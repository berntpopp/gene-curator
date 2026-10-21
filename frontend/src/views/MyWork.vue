<template>
  <v-container fluid>
    <div class="mb-4">
      <h1 class="text-headline-medium font-weight-bold">My work</h1>
      <p class="text-body-medium text-medium-emphasis">
        Across your scopes. Sorted by what blocks others first.
      </p>
    </div>

    <PendingInvitations v-if="invitations.hasPendingInvitations" class="mb-4" />

    <div class="d-flex flex-wrap align-center ga-2 mb-3">
      <v-tabs v-model="tab" density="compact" color="primary" class="work-tabs">
        <v-tab v-for="t in TABS" :key="t.value" :value="t.value" role="tab">
          {{ t.label }}
          <span class="ml-2 text-medium-emphasis font-mono">{{ store.counts[t.value] ?? 0 }}</span>
        </v-tab>
      </v-tabs>
      <v-text-field
        v-model="filter"
        placeholder="Filter by gene or scope"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        class="work-filter"
        aria-label="Filter by gene or scope"
      />
    </div>

    <v-alert v-if="store.error" type="error" variant="tonal">
      {{ store.error }}
      <template #append>
        <v-btn class="retry" variant="text" @click="store.fetchMyWork()">Retry</v-btn>
      </template>
    </v-alert>
    <div v-else-if="store.loading && !store.items.length" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" />
    </div>
    <div v-else-if="!visible.length" class="work-empty text-medium-emphasis">
      {{ EMPTY_TEXT[tab] }}
    </div>
    <v-card v-else variant="flat" border>
      <template v-for="g in groups" :key="g.verb">
        <div data-test="work-group" class="work-group text-label-large px-4 py-2">
          {{ g.verb }} <span class="font-mono text-medium-emphasis">{{ g.rows.length }}</span>
        </div>
        <div
          v-for="row in g.rows"
          :key="row.item_id + row.kind"
          data-test="work-row"
          class="work-row d-flex flex-wrap align-center ga-3 px-4"
          :class="{ 'work-row--active': row === active }"
          :aria-current="row === active ? 'true' : undefined"
        >
          <span class="font-mono work-gene">{{ row.gene_symbol }}</span>
          <span class="text-medium-emphasis">{{ row.scope_name }}</span>
          <v-spacer />
          <span class="font-mono text-medium-emphasis text-body-small">
            {{ formatDate(row.updated_at) }}
          </span>
          <v-btn :to="row.link" size="small" variant="outlined" color="primary">{{
            row.verb
          }}</v-btn>
        </div>
      </template>
    </v-card>
    <p class="text-body-small text-medium-emphasis mt-3">
      Press <kbd>J</kbd> <kbd>K</kbd> to move, <kbd>Enter</kbd> to open.
    </p>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useMyWorkStore, type WorkTab } from '@/stores/myWork'
  import { useInvitationsStore } from '@/stores/invitations'
  import PendingInvitations from '@/components/dashboard/PendingInvitations.vue'
  import { formatDate } from '@/utils/format'

  const TABS: { value: WorkTab; label: string }[] = [
    { value: 'needs_you', label: 'Needs you' },
    { value: 'waiting', label: 'Waiting on others' },
    { value: 'done', label: 'Done this week' }
  ]
  const EMPTY_TEXT: Record<WorkTab, string> = {
    needs_you: 'Nothing needs you right now.',
    waiting: 'Nothing is waiting on others.',
    done: 'Nothing finished this week yet.'
  }

  const router = useRouter()
  const store = useMyWorkStore()
  const invitations = useInvitationsStore()
  const tab = ref<WorkTab>('needs_you')
  const filter = ref('')
  const cursor = ref(0)

  const groups = computed(() => {
    const q = (filter.value ?? '').trim().toLowerCase()
    const byVerb = new Map<string, typeof store.items>()
    for (const i of store.byTab(tab.value)) {
      if (q && !`${i.gene_symbol} ${i.scope_name}`.toLowerCase().includes(q)) continue
      byVerb.set(i.verb, [...(byVerb.get(i.verb) ?? []), i])
    }
    return [...byVerb].map(([verb, rows]) => ({ verb, rows }))
  })
  // Flat in display order so J/K follow what the eye sees
  const visible = computed(() => groups.value.flatMap(g => g.rows))
  const active = computed(() => visible.value[cursor.value])
  watch([tab, filter], () => (cursor.value = 0))

  function onKey(e: KeyboardEvent) {
    // Typing or activating a focused control keeps its own behaviour
    const typing =
      e.target instanceof Element &&
      e.target.closest('input, textarea, select, a, button, [contenteditable]')
    if (typing || e.metaKey || e.ctrlKey) return
    const last = visible.value.length - 1
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
  .work-filter {
    max-width: 280px;
    min-width: 200px;
  }
  .work-group {
    background: rgb(var(--v-theme-background));
    border-bottom: 1px solid rgb(var(--v-theme-outline-variant, var(--v-theme-on-surface)));
  }
  .work-row {
    min-height: 44px;
    border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  }
  .work-row--active {
    box-shadow: inset 3px 0 0 rgb(var(--v-theme-secondary));
  }
  .work-gene {
    min-width: 72px;
    font-weight: 600;
  }
  .work-empty {
    padding: 32px 0;
  }
  kbd {
    font-family: monospace;
    border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
    border-radius: 3px;
    padding: 0 4px;
  }
</style>
