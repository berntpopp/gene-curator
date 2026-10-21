<template>
  <BaseDialog :model-value="modelValue" persistent size="md" title="Restore unsaved changes?">
    Restore unsaved changes{{ when ? ` from ${when}` : '' }}? This replaces the current form.
    <template #actions>
      <v-btn variant="text" @click="$emit('discard')">Discard</v-btn>
      <v-btn color="primary" variant="flat" @click="$emit('restore')">Restore</v-btn>
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
