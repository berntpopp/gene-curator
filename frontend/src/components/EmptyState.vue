<template>
  <div class="empty-state text-center py-12">
    <v-icon :size="iconSize" :color="iconColor" class="mb-4">
      {{ icon }}
    </v-icon>

    <h3 class="text-h5 mb-2">{{ title }}</h3>

    <p v-if="description" class="text-body-1 text-medium-emphasis mb-6">
      {{ description }}
    </p>

    <slot />
  </div>
</template>

<script setup>
  /**
   * EmptyState Component
   *
   * Shows a friendly empty state message with icon and optional action.
   * Used when lists, tables, or views have no data.
   *
   * Features:
   * - Customizable icon and colors
   * - Optional description text
   * - Slot for action buttons
   * - Responsive sizing
   *
   * @example
   * ```vue
   * <EmptyState
   *   icon="mdi-clipboard-alert"
   *   title="No assignments yet"
   *   description="Create your first assignment to get started."
   * >
   *   <v-btn color="primary" @click="createAssignment">
   *     Create Assignment
   *   </v-btn>
   * </EmptyState>
   * ```
   */

  defineProps({
    /**
     * Icon name (Material Design Icons)
     */
    icon: {
      type: String,
      default: 'mdi-inbox'
    },

    /**
     * Icon size (pixels or string)
     */
    iconSize: {
      type: [String, Number],
      default: 80
    },

    /**
     * Icon color (Vuetify color)
     */
    iconColor: {
      type: String,
      default: 'grey'
    },

    /**
     * Title text
     */
    title: {
      type: String,
      required: true
    },

    /**
     * Description text (optional)
     */
    description: {
      type: String,
      default: null
    }
  })
</script>

<style scoped>
  .empty-state {
    max-width: 500px;
    margin: 0 auto;
  }
</style>
