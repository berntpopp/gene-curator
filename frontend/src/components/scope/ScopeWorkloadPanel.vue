<template>
  <aside class="workload" aria-labelledby="workload-title">
    <h2 id="workload-title" class="text-title-medium mb-2">Curator workload</h2>
    <table v-if="rows.length" class="workload__table">
      <thead>
        <tr>
          <th scope="col">Curator</th>
          <th scope="col" class="num">Open</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.name">
          <td>{{ r.name }}</td>
          <td class="num">{{ r.open }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="text-body-small text-medium-emphasis">No genes are assigned to curators.</p>
    <p class="text-body-small text-medium-emphasis mt-2">
      Open = assigned genes not yet active. Counted from this scope's gene list.
    </p>
  </aside>
</template>

<script setup lang="ts">
  /** Open genes per curator, computed from the scope's assignment rows (no workload endpoint is used). */
  import { computed } from 'vue'

  const props = defineProps<{
    genes: { curator_id?: string | null; curator_name: string; stage: string }[]
  }>()

  const rows = computed(() => {
    const open = new Map<string, number>()
    for (const g of props.genes) {
      if (!g.curator_id || g.stage === 'active') continue
      open.set(g.curator_name, (open.get(g.curator_name) ?? 0) + 1)
    }
    return [...open].map(([name, n]) => ({ name, open: n })).sort((a, b) => b.open - a.open)
  })
</script>

<style scoped>
  .workload {
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-radius: 6px;
    padding: 16px;
  }

  .workload__table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  .workload__table th {
    text-align: left;
    font-weight: 500;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
    padding: 4px 0;
  }

  .workload__table td {
    padding: 6px 0;
    border-top: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
  }

  .num {
    text-align: right !important;
    font-family: 'IBM Plex Mono', monospace;
  }
</style>
