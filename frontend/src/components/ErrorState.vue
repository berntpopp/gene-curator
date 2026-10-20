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

<script setup lang="ts">
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

  withDefaults(
    defineProps<{
      /** Alert type */
      type?: 'error' | 'warning' | 'info' | 'success'
      /** Alert variant */
      variant?: 'tonal' | 'flat' | 'elevated' | 'outlined' | 'plain' | 'text'
      /** Alert color (overrides type color) */
      color?: string
      /** Title text */
      title?: string
      /** Description text */
      description?: string
      /** Show retry button */
      showRetry?: boolean
      /** Retry button text */
      retryText?: string
      /** Retry button variant */
      retryVariant?: 'elevated' | 'flat' | 'tonal' | 'outlined' | 'text' | 'plain'
      /** Retry button size */
      retrySize?: 'x-small' | 'small' | 'default' | 'large' | 'x-large'
      /** Closable */
      closable?: boolean
    }>(),
    {
      type: 'error',
      variant: 'tonal',
      color: undefined,
      title: 'Something went wrong',
      description: 'Please try again or contact support if the problem persists.',
      showRetry: true,
      retryText: 'Retry',
      retryVariant: 'outlined',
      retrySize: 'small',
      closable: false
    }
  )

  defineEmits<{ retry: [] }>()
</script>

<style scoped>
  .error-state {
    width: 100%;
  }
</style>
