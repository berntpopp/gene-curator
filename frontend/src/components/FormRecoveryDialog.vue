<template>
  <v-dialog :model-value="modelValue" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center bg-warning">
        <v-icon size="large" class="mr-2"> mdi-restore-alert </v-icon>
        Recover Unsaved Work?
      </v-card-title>

      <v-card-text class="pt-4">
        <v-alert type="info" variant="tonal" class="mb-4">
          <v-alert-title>Recovery Data Found</v-alert-title>
          We found unsaved changes from {{ formatTimestamp(timestamp) }}. Would you like to restore
          them?
        </v-alert>

        <div class="text-body-2 text-grey-darken-1">
          Your browser may have crashed or you navigated away without saving. Click
          <strong>"Restore My Work"</strong> to continue where you left off, or
          <strong>"Discard"</strong> to start fresh.
        </div>

        <v-alert type="warning" variant="text" density="compact" class="mt-4">
          <v-icon start size="small">mdi-information</v-icon>
          This will overwrite any current form data
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-btn variant="text" @click="$emit('discard')"> Discard </v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          variant="elevated"
          prepend-icon="mdi-restore"
          @click="$emit('restore')"
        >
          Restore My Work
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
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

  defineProps({
    modelValue: {
      type: Boolean,
      required: true
    },
    timestamp: {
      type: String,
      default: null
    }
  })

  defineEmits(['restore', 'discard'])

  /**
   * Format timestamp to human-readable relative time
   * @param {string} ts - ISO timestamp string
   * @returns {string} Formatted time string
   */
  function formatTimestamp(ts) {
    if (!ts) return 'recently'

    const date = new Date(ts)
    const now = new Date()
    const diffSeconds = Math.floor((now - date) / 1000)

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
    return date.toLocaleDateString()
  }
</script>

<style scoped>
  /* Ensure proper spacing and readability */
  .v-card-title {
    font-size: 1.25rem;
    font-weight: 500;
  }

  .text-body-2 {
    line-height: 1.5;
  }
</style>
