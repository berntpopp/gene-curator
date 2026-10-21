<template>
  <div v-if="selected.length" class="bulk-bar" role="toolbar" aria-label="Bulk actions">
    <strong>{{ selected.length }} selected</strong>
    <v-btn size="small" variant="outlined" data-testid="bulk-assign" @click="emit('assign')">
      Assign curator
    </v-btn>
    <v-menu>
      <template #activator="{ props: menu }">
        <v-btn v-bind="menu" size="small" variant="outlined" data-testid="bulk-priority">
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
    <v-menu :close-on-content-click="false">
      <template #activator="{ props: menu }">
        <v-btn v-bind="menu" size="small" variant="outlined" data-testid="bulk-due">
          Set due date
        </v-btn>
      </template>
      <v-card class="pa-3">
        <v-text-field
          v-model="dueDate"
          type="date"
          label="Due date"
          density="compact"
          variant="outlined"
          hide-details
        />
        <v-btn
          class="mt-2"
          size="small"
          color="primary"
          variant="flat"
          :disabled="!dueDate"
          data-testid="bulk-due-apply"
          @click="apply({ due_date: new Date(dueDate).toISOString() }, 'Due date set')"
        >
          Apply
        </v-btn>
      </v-card>
    </v-menu>
    <v-spacer />
    <v-btn size="small" variant="text" data-testid="bulk-clear" @click="emit('clear')">Clear</v-btn>
  </div>
</template>

<script setup lang="ts">
  /**
   * Actions for the selected genes. Assigning a curator opens the assign dialog (one
   * POST /gene-assignments/bulk); priority and due date have no bulk endpoint, so each selected
   * assignment is updated in turn.
   */
  import { ref } from 'vue'
  import { useAssignmentsStore } from '@/stores/assignments'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import { pluralize } from '@/utils/pluralize'
  import { priorityOptions } from '@/components/dynamic/assignmentDisplay'
  import type { Schema } from '@/types/api'
  import type { GeneRow } from './types'

  const props = defineProps<{ selected: GeneRow[] }>()
  const emit = defineEmits<{ assign: []; clear: []; changed: [] }>()

  const assignments = useAssignmentsStore()
  const notifications = useNotificationsStore()
  const logger = useLogger()
  const dueDate = ref('')

  async function apply(update: Schema<'GeneScopeAssignmentUpdate'>, message: string) {
    const results = await Promise.allSettled(
      props.selected.map(g => assignments.updateAssignment(g.assignment_id, update))
    )
    const failed = results.filter(r => r.status === 'rejected').length
    if (failed) logger.error('Bulk update failed', { failed, total: results.length })
    notifications.addToast(
      failed
        ? `${message} for ${results.length - failed} of ${pluralize(results.length, 'gene')}; ${failed} failed`
        : `${message} for ${pluralize(results.length, 'gene')}`,
      failed ? 'error' : 'success'
    )
    dueDate.value = ''
    emit('changed')
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
