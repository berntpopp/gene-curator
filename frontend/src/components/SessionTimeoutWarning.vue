<template>
  <v-snackbar
    :model-value="modelValue"
    :timeout="-1"
    location="top"
    color="warning"
    multi-line
    vertical
  >
    <div class="d-flex flex-column">
      <div class="d-flex align-center mb-2">
        <v-icon size="large" class="mr-2"> mdi-timer-alert </v-icon>
        <div>
          <div class="text-h6">Session Expiring Soon</div>
          <div class="text-body-2">
            Your session will expire in <strong>{{ formattedTime }}</strong>
          </div>
        </div>
      </div>

      <v-alert
        v-if="timeRemaining < 120"
        type="error"
        variant="text"
        density="compact"
        class="mb-2"
      >
        <v-icon start size="small">mdi-alert</v-icon>
        <strong>Warning:</strong> Unsaved changes will be lost if your session expires!
      </v-alert>

      <div class="text-caption text-grey-lighten-2">
        Click "Extend Session" to continue working, or save your work now.
      </div>
    </div>

    <template #actions>
      <v-btn variant="text" @click="$emit('dismiss')"> Dismiss </v-btn>
      <v-btn color="white" variant="elevated" :loading="extending" @click="handleExtend">
        <v-icon start>mdi-refresh</v-icon>
        Extend Session
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script setup>
  /**
   * Session Timeout Warning Component
   *
   * Non-intrusive warning shown when JWT token is about to expire.
   * Uses Vuetify snackbar for minimal UI disruption.
   *
   * Design principles:
   * - Non-blocking: Snackbar doesn't prevent interaction
   * - Urgent: Clear warning about data loss risk
   * - Actionable: Simple "Extend Session" button
   * - Accessible: Clear messaging, keyboard navigation
   */

  import { ref, computed } from 'vue'

  const props = defineProps({
    modelValue: {
      type: Boolean,
      required: true
    },
    timeRemaining: {
      type: Number,
      required: true,
      validator: value => value >= 0
    }
  })

  const emit = defineEmits(['extend', 'dismiss'])

  const extending = ref(false)

  /**
   * Format time remaining as human-readable string
   * @returns {string} Formatted time (e.g., "5:30", "1:05")
   */
  const formattedTime = computed(() => {
    const minutes = Math.floor(props.timeRemaining / 60)
    const seconds = props.timeRemaining % 60
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  })

  /**
   * Handle extend session action
   * Shows loading state and emits extend event
   */
  async function handleExtend() {
    extending.value = true
    try {
      await emit('extend')
    } finally {
      extending.value = false
    }
  }
</script>

<style scoped>
  /* Ensure text is readable on warning background */
  .v-snackbar :deep(.v-snackbar__content) {
    padding: 16px;
  }

  .text-h6 {
    font-weight: 500;
    margin-bottom: 4px;
  }

  .text-body-2 {
    line-height: 1.5;
  }

  /* Make action buttons more prominent */
  .v-snackbar :deep(.v-snackbar__actions) {
    margin-top: 8px;
  }

  /* Ensure alert text is readable */
  .v-alert {
    font-size: 0.875rem;
  }
</style>
