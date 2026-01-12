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

<script setup>
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

  defineProps({
    loading: {
      type: Boolean,
      required: true
    },
    count: {
      type: Number,
      default: 6,
      validator: value => value > 0 && value <= 24
    },
    cols: {
      type: [String, Number],
      default: 12
    },
    sm: {
      type: [String, Number],
      default: 6
    },
    md: {
      type: [String, Number],
      default: 4
    },
    elevation: {
      type: [String, Number],
      default: 2
    }
  })
</script>
