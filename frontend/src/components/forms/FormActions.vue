<template>
  <v-card-actions class="px-4 py-3">
    <v-btn variant="outlined" aria-label="Cancel" @click="$emit('cancel')">
      <v-icon start>mdi-close</v-icon>
      Cancel
    </v-btn>

    <v-spacer />

    <!-- Undo/Redo -->
    <v-btn-group variant="outlined" density="compact" class="mr-2">
      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            :disabled="!canUndo"
            aria-label="Undo (Ctrl+Z)"
            @click="$emit('undo')"
          >
            <v-icon>mdi-undo</v-icon>
          </v-btn>
        </template>
        <span>Undo (Ctrl+Z)</span>
      </v-tooltip>

      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            :disabled="!canRedo"
            aria-label="Redo (Ctrl+Shift+Z)"
            @click="$emit('redo')"
          >
            <v-icon>mdi-redo</v-icon>
          </v-btn>
        </template>
        <span>Redo (Ctrl+Shift+Z)</span>
      </v-tooltip>
    </v-btn-group>

    <v-tooltip location="top">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          variant="outlined"
          :loading="saving"
          aria-label="Save Draft (Ctrl+S)"
          @click="$emit('save-draft')"
        >
          <v-icon start>mdi-content-save</v-icon>
          Save Draft
        </v-btn>
      </template>
      <span>Save Draft (Ctrl+S)</span>
    </v-tooltip>

    <v-tooltip location="top">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          color="primary"
          variant="flat"
          :loading="submitting"
          :disabled="!canSubmit"
          aria-label="Submit for Review (Ctrl+Enter)"
          @click="$emit('submit')"
        >
          <v-icon start>mdi-check-circle</v-icon>
          Submit for Review
        </v-btn>
      </template>
      <span>Submit for Review (Ctrl+Enter)</span>
    </v-tooltip>
  </v-card-actions>
</template>

<script setup>
  /**
   * FormActions Component
   *
   * Reusable action bar for curation and precuration forms.
   * Provides undo/redo, save draft, and submit buttons with keyboard shortcut hints.
   *
   * @example
   * <FormActions
   *   :can-undo="canUndo"
   *   :can-redo="canRedo"
   *   :can-submit="isValid"
   *   :saving="savingDraft"
   *   :submitting="submitting"
   *   @undo="undo"
   *   @redo="redo"
   *   @save-draft="handleSaveDraft"
   *   @submit="handleSubmit"
   *   @cancel="handleCancel"
   * />
   */

  defineProps({
    canUndo: {
      type: Boolean,
      default: false
    },
    canRedo: {
      type: Boolean,
      default: false
    },
    canSubmit: {
      type: Boolean,
      default: true
    },
    saving: {
      type: Boolean,
      default: false
    },
    submitting: {
      type: Boolean,
      default: false
    }
  })

  defineEmits(['undo', 'redo', 'save-draft', 'submit', 'cancel'])
</script>
