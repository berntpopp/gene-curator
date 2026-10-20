<template>
  <v-row v-if="loading">
    <v-col v-for="i in count" :key="`skeleton-${i}`" :cols="cols" :sm="sm" :md="md">
      <v-card>
        <v-skeleton-loader type="card" :elevation="elevation" />
      </v-card>
    </v-col>
  </v-row>
  <slot v-else />
</template>

<script setup lang="ts">
  /**
   * Card Skeleton Component
   *
   * Provides skeleton loading state for card grid layouts.
   * Maintains grid structure to prevent layout shift.
   *
   * Design principles:
   * - Zero layout shift: Grid structure maintained
   * - Flexible: Works with various grid configurations
   * - DRY: Reusable across all card views
   *
   * @example
   * <card-skeleton :loading="loading" :count="6" cols="12" sm="6" md="4">
   *   <v-row>
   *     <v-col v-for="item in items" :key="item.id">
   *       <v-card>{{ item.name }}</v-card>
   *     </v-col>
   *   </v-row>
   * </card-skeleton>
   */

  withDefaults(
    defineProps<{
      loading: boolean
      /** Number of skeleton cards (1-24) */
      count?: number
      cols?: string | number
      sm?: string | number
      md?: string | number
      elevation?: string | number
    }>(),
    {
      count: 6,
      cols: 12,
      sm: 6,
      md: 4,
      elevation: 2
    }
  )
</script>
