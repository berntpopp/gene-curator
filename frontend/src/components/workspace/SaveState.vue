<template>
  <span :class="['save-state', `save-state--${state}`]" role="status" aria-live="polite">
    <v-icon v-if="state === 'saved'" size="14" aria-hidden="true">mdi-check</v-icon>
    <v-icon v-else-if="state === 'failed'" size="14" aria-hidden="true">mdi-alert-circle</v-icon>
    <template v-if="state === 'saved'">Saved{{ time ? ` ${time}` : '' }}</template>
    <template v-else-if="state === 'saving'">Saving…</template>
    <template v-else-if="state === 'unsaved'">Unsaved changes</template>
    <template v-else>
      Save failed
      <v-btn variant="text" size="x-small" class="ml-1" @click="emit('retry')">Retry</v-btn>
    </template>
  </span>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import type { SaveState } from './useWorkspaceFrame'

  const props = defineProps<{ state: SaveState; savedAt: number | null }>()
  const emit = defineEmits<{ retry: [] }>()

  const time = computed(() =>
    props.savedAt
      ? new Date(props.savedAt).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        })
      : ''
  )
</script>

<style scoped>
  .save-state {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .save-state--saved {
    color: rgb(var(--v-theme-success));
  }

  .save-state--unsaved {
    color: rgb(var(--v-theme-warning));
  }

  .save-state--failed {
    color: rgb(var(--v-theme-error));
    font-weight: 600;
  }
</style>
