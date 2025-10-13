<template>
  <div class="loading-state">
    <v-skeleton-loader :type="type" :loading="loading">
      <slot />
    </v-skeleton-loader>
  </div>
</template>

<script setup>
  /**
   * LoadingState Component
   *
   * Shows a skeleton loader while content is loading.
   * Wraps Vuetify's v-skeleton-loader with sensible defaults.
   *
   * Features:
   * - Multiple skeleton types
   * - Shows content when loading is false
   * - Smooth transitions
   *
   * @example
   * ```vue
   * <LoadingState
   *   :loading="loading"
   *   type="list-item-avatar-two-line@3"
   * >
   *   <v-list>
   *     <v-list-item v-for="item in items" :key="item.id">
   *       {{ item.title }}
   *     </v-list-item>
   *   </v-list>
   * </LoadingState>
   * ```
   */

  defineProps({
    /**
     * Skeleton type
     * See Vuetify docs for available types
     */
    type: {
      type: String,
      default: 'list-item-avatar-two-line@3'
    },

    /**
     * Loading state
     */
    loading: {
      type: Boolean,
      default: true
    }
  })
</script>

<style scoped>
  .loading-state {
    width: 100%;
  }
</style>
