<template>
  <div v-if="selected.length" class="bulk-bar" role="toolbar" aria-label="Bulk actions">
    <strong>{{ selected.length }} selected</strong>
    <v-btn
      size="small"
      variant="outlined"
      data-testid="bulk-assign"
      :disabled="busy || !assignable"
      @click="emit('assign')"
    >
      Assign curator
    </v-btn>
    <span v-if="skipped" class="text-body-small" data-testid="bulk-skipped">
      {{ skipped }} already {{ skipped === 1 ? 'has' : 'have' }} a curator
    </span>
    <v-menu>
      <template #activator="{ props: menu }">
        <v-btn
          v-bind="menu"
          size="small"
          variant="outlined"
          data-testid="bulk-priority"
          :disabled="busy"
        >
          Set priority
        </v-btn>
      </template>
      <v-list density="compact">
        <v-list-item
          v-for="p in priorityOptions"
          :key="p.value"
          :title="p.title"
          :data-testid="`bulk-priority-${p.value}`"
          @click="apply({ priority_level: p.value }, `Priority set to ${p.title.toLowerCase()}`)"
        />
      </v-list>
    </v-menu>
    <v-spacer />
    <v-btn
      size="small"
      variant="text"
      data-testid="bulk-clear"
      :disabled="busy"
      @click="emit('clear')"
      >Clear</v-btn
    >
  </div>
</template>

<script setup lang="ts">
  /**
   * Actions for the selected genes. Assigning a curator opens the assign dialog (one
   * POST /gene-assignments/bulk); priority has no bulk endpoint, so selected assignments are
   * updated in batches of five. Due date is not offered: the list carries no due date to show.
   */
  import { computed, ref } from 'vue'
  import { useAssignmentsStore } from '@/stores/assignments'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import { pluralize } from '@/utils/pluralize'
  import { priorityOptions } from '@/components/dynamic/assignmentDisplay'
  import type { Schema } from '@/types/api'
  import type { GeneRow } from './types'

  const props = defineProps<{ selected: GeneRow[] }>()
  const emit = defineEmits<{ assign: []; clear: []; changed: [failedGeneIds: string[]] }>()

  const assignments = useAssignmentsStore()
  const notifications = useNotificationsStore()
  const logger = useLogger()
  const busy = ref(false)
  const BATCH = 5

  const assignable = computed(() => props.selected.filter(g => !g.curator_id).length)
  const skipped = computed(() => props.selected.length - assignable.value)

  async function apply(update: Schema<'GeneScopeAssignmentUpdate'>, message: string) {
    if (busy.value) return
    busy.value = true
    const failed: GeneRow[] = []
    try {
      const genes = [...props.selected]
      for (let i = 0; i < genes.length; i += BATCH) {
        const batch = genes.slice(i, i + BATCH)
        const results = await Promise.allSettled(
          batch.map(g => assignments.updateAssignment(g.assignment_id, update))
        )
        results.forEach((r, j) => r.status === 'rejected' && failed.push(batch[j]!))
      }
      if (failed.length) logger.error('Bulk update failed', { failed: failed.length })
      const total = genes.length
      notifications.addToast(
        failed.length
          ? `${message} for ${total - failed.length} of ${pluralize(total, 'gene')}. Failed: ${failed.map(g => g.gene_symbol).join(', ')}`
          : `${message} for ${pluralize(total, 'gene')}`,
        failed.length ? 'error' : 'success'
      )
    } finally {
      busy.value = false
    }
    emit(
      'changed',
      failed.map(g => g.gene_id)
    )
  }
</script>

<style scoped>
  .bulk-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-on-primary));
    border-radius: 6px;
  }
</style>
