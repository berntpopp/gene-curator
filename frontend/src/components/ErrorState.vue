<template>
  <v-alert
    :type="type"
    :variant="variant"
    :color="color"
    :closable="closable"
    class="error-state mb-4"
  >
    <template #title>
      <slot name="title">{{ title }}</slot>
    </template>

    <template #text>
      <slot name="description">{{ description }}</slot>
    </template>

    <template v-if="showRetry" #append>
      <v-btn :variant="retryVariant" :size="retrySize" @click="$emit('retry')">
        {{ retryText }}
      </v-btn>
    </template>
  </v-alert>
</template>

<script setup>
  /**
   * ErrorState Component
   *
   * Shows an error message with optional retry button.
   * Used for API errors, validation errors, or general failures.
   *
   * Features:
   * - Customizable type (error, warning, info)
   * - Optional retry button
   * - Closable
   * - Slot support for custom content
   *
   * @example
   * ```vue
   * <ErrorState
   *   title="Failed to load data"
   *   description="Please try again or contact support."
   *   @retry="fetchData"
   * />
   * ```
   */

  defineProps({
    /**
     * Alert type
     */
    type: {
      type: String,
      default: 'error',
      validator: value => ['error', 'warning', 'info', 'success'].includes(value)
    },

    /**
     * Alert variant
     */
    variant: {
      type: String,
      default: 'tonal',
      validator: value => ['tonal', 'flat', 'elevated', 'outlined', 'plain', 'text'].includes(value)
    },

    /**
     * Alert color (overrides type color)
     */
    color: {
      type: String,
      default: null
    },

    /**
     * Title text
     */
    title: {
      type: String,
      default: 'Something went wrong'
    },

    /**
     * Description text
     */
    description: {
      type: String,
      default: 'Please try again or contact support if the problem persists.'
    },

    /**
     * Show retry button
     */
    showRetry: {
      type: Boolean,
      default: true
    },

    /**
     * Retry button text
     */
    retryText: {
      type: String,
      default: 'Retry'
    },

    /**
     * Retry button variant
     */
    retryVariant: {
      type: String,
      default: 'outlined'
    },

    /**
     * Retry button size
     */
    retrySize: {
      type: String,
      default: 'small'
    },

    /**
     * Closable
     */
    closable: {
      type: Boolean,
      default: false
    }
  })

  defineEmits(['retry'])
</script>

<style scoped>
  .error-state {
    width: 100%;
  }
</style>
