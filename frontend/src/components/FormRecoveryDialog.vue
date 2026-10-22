<template>
  <BaseDialog
    :model-value="modelValue"
    persistent
    size="md"
    :title="stale ? 'A newer version was saved' : 'Restore unsaved changes?'"
  >
    <template v-if="stale">
      This record was saved again after your local changes{{ when ? ` from ${when}` : '' }}, for
      example in another tab or by another user. Restoring replaces that newer saved version with
      your local copy.
    </template>
    <template v-else>
      Your local changes{{ when ? ` from ${when}` : '' }} were not saved. Restoring replaces what
      the form shows now with them.
    </template>
    <template #actions>
      <v-btn variant="text" @click="$emit('discard')">
        {{ stale ? 'Keep newer version' : 'Discard local changes' }}
      </v-btn>
      <v-btn :color="stale ? 'warning' : 'primary'" variant="flat" @click="$emit('restore')">
        {{ stale ? 'Replace with local copy' : 'Restore local changes' }}
      </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  /**
   * Form Recovery Dialog Component
   *
   * Displays when recoverable form data is found in localStorage.
   * Follows Material Design patterns with clear action buttons.
   *
   * Design principles:
   * - KISS: Simple restore/discard actions
   * - User-centric: Clear messaging about what will happen
   * - Accessible: ARIA labels, keyboard navigation
   */

  import { computed } from 'vue'
  import { formatDate } from '@/utils/format'
  import BaseDialog from '@/components/BaseDialog.vue'

  const props = defineProps<{
    modelValue: boolean
    /** ISO timestamp string */
    timestamp?: string | null
    /** The server copy is newer than the local changes: restoring replaces it */
    stale?: boolean
  }>()

  defineEmits<{
    restore: []
    discard: []
  }>()

  const when = computed(() => formatTimestamp(props.timestamp))

  /**
   * Format timestamp to human-readable relative time
   */
  function formatTimestamp(ts: string | null | undefined): string {
    if (!ts) return ''

    const date = new Date(ts)
    const now = new Date()
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diffSeconds < 60) {
      return 'less than a minute ago'
    }

    const diffMinutes = Math.floor(diffSeconds / 60)
    if (diffMinutes < 60) {
      return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`
    }

    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
    }

    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) {
      return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
    }

    // For older dates, show formatted date
    return formatDate(date)
  }
</script>
