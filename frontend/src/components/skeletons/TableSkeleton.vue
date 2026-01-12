<template>
  <v-data-table :items="displayItems" :headers="headers" :loading="false" v-bind="$attrs">
    <template #item="{ item }">
      <tr v-if="item.isSkeleton">
        <td v-for="header in headers" :key="header.key" class="skeleton-cell">
          <v-skeleton-loader type="text" :width="getSkeletonWidth(header)" />
        </td>
      </tr>
      <slot v-else name="item" :item="item" />
    </template>

    <!-- Pass through all other slots -->
    <template v-for="(_, name) in $slots" #[name]="slotData">
      <slot :name="name" v-bind="slotData || {}" />
    </template>
  </v-data-table>
</template>

<script setup>
  /**
   * Table Skeleton Component
   *
   * Provides skeleton loading state for v-data-table.
   * Eliminates Cumulative Layout Shift (CLS) by maintaining table structure during loading.
   *
   * Design principles:
   * - Zero layout shift: Table structure maintained
   * - Progressive enhancement: Works with existing v-data-table
   * - DRY: Reusable across all table views
   * - Accessible: Maintains ARIA labels and roles
   *
   * @example
   * <table-skeleton
   *   :loading="loading"
   *   :items="items"
   *   :headers="headers"
   *   :skeleton-count="5"
   * >
   *   <template #item="{ item }">
   *     <tr>
   *       <td>{{ item.name }}</td>
   *       <td>{{ item.status }}</td>
   *     </tr>
   *   </template>
   * </table-skeleton>
   */

  import { computed } from 'vue'

  const props = defineProps({
    loading: {
      type: Boolean,
      required: true
    },
    items: {
      type: Array,
      required: true
    },
    headers: {
      type: Array,
      required: true
    },
    skeletonCount: {
      type: Number,
      default: 5,
      validator: value => value > 0 && value <= 20
    }
  })

  /**
   * Display skeleton items while loading, otherwise show real items
   * Skeleton items have special isSkeleton flag for conditional rendering
   */
  const displayItems = computed(() => {
    if (props.loading) {
      return Array.from({ length: props.skeletonCount }, (_, i) => ({
        isSkeleton: true,
        id: `skeleton-${i}`
      }))
    }
    return props.items
  })

  /**
   * Get skeleton width based on column type
   * Varies width to look more realistic
   *
   * @param {Object} header - Table header definition
   * @returns {string} Width in pixels or percentage
   */
  function getSkeletonWidth(header) {
    // Customize based on common column types
    const key = header.key?.toLowerCase() || ''

    if (key.includes('id') || key.includes('uuid')) {
      return '120px'
    } else if (key.includes('date') || key.includes('time')) {
      return '100px'
    } else if (key.includes('status') || key.includes('role')) {
      return '80px'
    } else if (key.includes('action')) {
      return '60px'
    } else if (key.includes('description') || key.includes('notes')) {
      return '90%'
    }

    // Default: varied widths for natural look
    const index = props.headers.indexOf(header)
    const widths = ['70%', '85%', '60%', '75%', '80%']
    return widths[index % widths.length]
  }
</script>

<style scoped>
  .skeleton-cell {
    padding: 12px 16px;
  }

  /* Ensure skeleton loaders have consistent height */
  .skeleton-cell :deep(.v-skeleton-loader) {
    height: 20px;
  }

  /* Smooth loading animation */
  .skeleton-cell :deep(.v-skeleton-loader__bone) {
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }
</style>
