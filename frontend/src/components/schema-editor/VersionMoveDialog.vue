<template>
  <v-btn
    aria-label="Move curations to the latest version"
    icon="mdi-redo"
    size="small"
    variant="text"
    :loading="moving && !open"
    @click="openPlan"
  />
  <BaseDialog v-model="open" size="lg">
    <template #title>Move {{ schemaName }} curations to version {{ plan?.to_version }}</template>
    <p v-if="!plan?.items.length" class="text-body-medium">
      Every curation is already on version {{ plan?.to_version }}; nothing to move.
    </p>
    <p v-else class="text-body-medium mb-3">
      Nothing is written until you confirm. Active curations whose class changes go back to review;
      those missing a new required field go back to draft.
    </p>
    <v-table v-if="plan?.items.length" density="compact">
      <thead>
        <tr>
          <th>Gene</th>
          <th>Status</th>
          <th>Version</th>
          <th>Class</th>
          <th>Fields</th>
          <th>Outcome</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in plan.items" :key="item.id">
          <td>
            {{ item.gene ?? '' }} <span class="text-medium-emphasis">{{ item.kind }}</span>
          </td>
          <td>{{ item.status }}</td>
          <td>v{{ item.from_version }} → v{{ item.to_version }}</td>
          <td>
            <template v-if="item.kind === 'curation'">
              {{ item.old_class ?? '-' }} → {{ item.new_class ?? '-' }}
            </template>
          </td>
          <td class="text-body-small">
            <div v-if="item.dropped?.length">Dropped: {{ item.dropped.join(', ') }}</div>
            <div v-if="item.missing_required?.length" class="text-error">
              Now required: {{ item.missing_required.join(', ') }}
            </div>
          </td>
          <td>
            <v-chip
              :color="OUTCOME[outcome(item)].color"
              :title="item.skipped ?? undefined"
              size="small"
              variant="tonal"
            >
              {{ OUTCOME[outcome(item)].label }}
            </v-chip>
          </td>
        </tr>
      </tbody>
    </v-table>
    <template #actions>
      <v-btn variant="text" @click="open = false">Cancel</v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :loading="moving"
        :disabled="!plan?.items.length"
        @click="apply"
      >
        Move
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { storeToRefs } from 'pinia'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { errorMessage } from '@/stores/apiError'
  import { useMethodologyImportStore } from '@/stores/methodologyImport'
  import type { Schema } from '@/types/api'

  type VersionMoveItem = Schema<'VersionMoveItem'>

  const props = defineProps<{ schemaId: string; schemaName: string }>()

  const OUTCOME = {
    review: { label: 'Copy to review', color: 'warning' },
    draft: { label: 'Copy to draft', color: 'error' },
    stays: { label: 'Moves', color: undefined },
    skipped: { label: 'Skipped', color: 'error' }
  }
  /** An inactive scope's row is not moved (read-only); the chip's title says why. */
  const outcome = (item: VersionMoveItem) => (item.skipped ? 'skipped' : (item.back_to ?? 'stays'))

  const logger = useLogger()
  const store = useMethodologyImportStore()
  const { movePlan: plan, moving } = storeToRefs(store)
  const open = ref(false)

  /** Show the dry-run plan; nothing is written yet. */
  const openPlan = async () => {
    try {
      await store.planMove(props.schemaId)
      open.value = true
    } catch (error) {
      logger.error('Move to version dry run failed', {
        schemaId: props.schemaId,
        error: String(error)
      })
      showError(errorMessage(error, 'Failed to plan the move'))
    }
  }

  const apply = async () => {
    try {
      const result = await store.applyMove(props.schemaId)
      const reopened = result.items.filter(i => i.back_to).length
      const skipped = result.items.filter(i => i.skipped).length
      const moved = result.items.length - skipped
      logger.info('Moved to version', {
        schemaId: props.schemaId,
        version: result.to_version,
        moved,
        skipped,
        reopened
      })
      const note = skipped ? `; ${skipped} skipped (inactive scope)` : ''
      showSuccess(
        `${moved} moved to version ${result.to_version}; ${reopened} need review again${note}`
      )
      open.value = false
    } catch (error) {
      // 409: a newer version was published since the plan; plan again
      logger.error('Move to version failed', { schemaId: props.schemaId, error: String(error) })
      showError(errorMessage(error, 'Move failed'))
    }
  }
</script>
