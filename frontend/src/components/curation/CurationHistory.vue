<template>
  <section v-if="entries.length" aria-labelledby="curation-history-title" class="curation-history">
    <h3 id="curation-history-title" class="text-body-medium font-weight-medium mb-2">History</h3>
    <ol class="curation-history__list">
      <li v-for="entry in entries" :key="`${entry.id}-${entry.executed_at}`">
        <span class="mono tabular">{{ formatDateTime(entry.executed_at) }}</span>
        {{ action(entry) }} by {{ entry.executed_by_name || 'unknown' }}
        <template v-if="agentOf(entry)">
          via {{ agentOf(entry)!.agent || 'an AI agent' }} ({{ agentOf(entry)!.model }})
          <span v-if="agentOf(entry)!.tools_used?.length" class="text-medium-emphasis">
            using {{ agentOf(entry)!.tools_used!.join(', ') }}
          </span>
        </template>
        <div v-if="entry.notes" class="curation-history__notes">{{ entry.notes }}</div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
  /** Submissions and review decisions of a curation, with the AI agent of an MCP submit (#593). */
  import { computed, onMounted } from 'vue'
  import { useWorkflowStore } from '@/stores/workflow'
  import { formatDateTime } from '@/utils/format'
  import type { Schema } from '@/types/api'

  type Entry = Schema<'WorkflowAuditEntry'>
  interface Agent {
    model?: string
    agent?: string
    tools_used?: string[]
  }

  const props = defineProps<{ curationId: string }>()
  const store = useWorkflowStore()
  const entries = computed(() => store.getStageHistory(props.curationId))

  const action = (e: Entry) =>
    e.to_stage === 'review'
      ? 'Submitted'
      : e.to_stage === 'active'
        ? 'Approved'
        : 'Changes requested'
  const agentOf = (e: Entry) => (e.metadata as { agent?: Agent } | null)?.agent ?? null

  // The history is extra context: a failed load leaves it out
  onMounted(() => store.fetchStageHistory(props.curationId).catch(() => undefined))
</script>

<style scoped>
  .curation-history__list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 6px;
    font-size: 0.875rem;
  }

  .curation-history__notes {
    white-space: pre-wrap;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }
</style>
