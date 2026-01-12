<template>
  <v-dialog :model-value="modelValue" max-width="1000" persistent scrollable>
    <v-card>
      <v-card-title class="d-flex align-center bg-error text-white">
        <v-icon size="large" class="mr-2" color="white"> mdi-alert-octagon </v-icon>
        Save Conflict Detected
      </v-card-title>

      <v-card-text class="pt-4">
        <v-alert type="error" variant="tonal" class="mb-4">
          <v-alert-title>Someone else modified this record</v-alert-title>
          Another user saved changes while you were editing. Choose how to resolve this conflict:
        </v-alert>

        <!-- Conflict comparison -->
        <v-row>
          <v-col cols="12" md="6">
            <v-card variant="outlined" color="primary">
              <v-card-title class="bg-primary text-white">
                <v-icon start>mdi-account</v-icon>
                Your Changes
              </v-card-title>
              <v-card-text>
                <div class="conflict-diff">
                  <pre>{{ formatJSON(yourChanges) }}</pre>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="6">
            <v-card variant="outlined" color="warning">
              <v-card-title class="bg-warning text-white">
                <v-icon start>mdi-account-multiple</v-icon>
                Their Changes
              </v-card-title>
              <v-card-text>
                <div class="conflict-diff">
                  <pre>{{ formatJSON(theirChanges) }}</pre>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Conflicted fields list -->
        <v-alert
          v-if="conflictedFields && conflictedFields.length > 0"
          type="warning"
          variant="text"
          density="compact"
          class="mt-4"
        >
          <v-icon start size="small">mdi-information</v-icon>
          <strong>Conflicted fields:</strong>
          {{ conflictedFields.join(', ') }}
        </v-alert>

        <!-- Resolution options explanation -->
        <v-card variant="tonal" color="info" class="mt-4">
          <v-card-text>
            <div class="text-subtitle-2 mb-2">
              <v-icon start size="small">mdi-lightbulb</v-icon>
              Resolution Options:
            </div>
            <ul class="text-body-2">
              <li><strong>Discard My Changes:</strong> Keep the other user's version (safest)</li>
              <li>
                <strong>Overwrite Their Changes:</strong> Force save your version (use with caution)
              </li>
              <li>
                <strong>Merge Manually:</strong> Close this dialog and manually combine changes
              </li>
            </ul>
          </v-card-text>
        </v-card>

        <!-- Warning -->
        <v-alert type="warning" density="compact" class="mt-4">
          <v-icon start size="small">mdi-alert</v-icon>
          If possible, contact the other user before overwriting their changes.
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-btn variant="text" @click="$emit('cancel')"> Cancel </v-btn>
        <v-spacer />
        <v-btn
          color="warning"
          variant="outlined"
          prepend-icon="mdi-delete-sweep"
          @click="$emit('resolve', 'discard-mine')"
        >
          Discard My Changes
        </v-btn>
        <v-btn
          color="error"
          variant="outlined"
          prepend-icon="mdi-alert"
          @click="$emit('resolve', 'overwrite-theirs')"
        >
          Overwrite Their Changes
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          prepend-icon="mdi-merge"
          @click="$emit('resolve', 'merge')"
        >
          Merge Manually
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  /**
   * Conflict Resolution Dialog Component
   *
   * Displays when optimistic locking conflict is detected (409 response).
   * Shows side-by-side comparison of conflicting changes.
   *
   * Design principles:
   * - Clear visual distinction between "your" and "their" changes
   * - Explicit resolution options with clear consequences
   * - Follows Material Design error handling patterns
   * - Accessible with keyboard navigation and ARIA labels
   */

  defineProps({
    modelValue: {
      type: Boolean,
      required: true
    },
    yourChanges: {
      type: Object,
      default: () => ({})
    },
    theirChanges: {
      type: Object,
      default: () => ({})
    },
    conflictedFields: {
      type: Array,
      default: () => []
    }
  })

  defineEmits(['resolve', 'cancel'])

  /**
   * Format object as pretty-printed JSON
   * Removes sensitive fields and formats for display
   *
   * @param {Object} obj - Object to format
   * @returns {string} Formatted JSON string
   */
  function formatJSON(obj) {
    if (!obj) return 'No data'

    // Remove sensitive or unnecessary fields
    const filtered = { ...obj }
    delete filtered.lock_version
    delete filtered.updated_at
    delete filtered.updated_by

    try {
      return JSON.stringify(filtered, null, 2)
    } catch (error) {
      return 'Error formatting data'
    }
  }
</script>

<style scoped>
  .conflict-diff {
    max-height: 400px;
    overflow-y: auto;
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
    padding: 12px;
  }

  .conflict-diff pre {
    margin: 0;
    font-size: 0.875rem;
    font-family: 'Roboto Mono', monospace;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  /* Dark mode support */
  .v-theme--dark .conflict-diff {
    background-color: rgba(255, 255, 255, 0.05);
  }

  /* Ensure card titles are readable on colored backgrounds */
  .v-card-title.bg-primary,
  .v-card-title.bg-warning {
    font-size: 1rem;
    font-weight: 500;
    padding: 12px 16px;
  }

  /* List styling */
  ul {
    padding-left: 20px;
    margin: 0;
  }

  ul li {
    margin-bottom: 4px;
  }
</style>
