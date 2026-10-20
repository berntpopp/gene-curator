<template>
  <v-badge
    :content="displayCount"
    :model-value="hasNotifications"
    :color="badgeColor"
    :max="max"
    offset-x="-10"
    offset-y="10"
  >
    <slot />
  </v-badge>
</template>

<script setup lang="ts">
  /**
   * NotificationBadge Component
   *
   * Wraps any element with a notification badge.
   * Typically used on avatar or menu items.
   *
   * Features:
   * - Auto-hides when count is 0
   * - Color based on priority (critical = error, warning = warning, info = info)
   * - Max count display (e.g., "99+")
   * - Accessible (ARIA labels)
   *
   * @example
   * ```vue
   * <NotificationBadge :count="5">
   *   <v-avatar>
   *     <v-icon>mdi-account-circle</v-icon>
   *   </v-avatar>
   * </NotificationBadge>
   * ```
   */

  import { computed } from 'vue'

  type NotificationPriority = 'critical' | 'warning' | 'info'

  const props = withDefaults(
    defineProps<{
      /** Notification count */
      count?: number
      /** Priority level (affects color): critical -> error, warning -> warning, info -> info */
      priority?: NotificationPriority
      /** Maximum count to display (shows "max+" above this) */
      max?: number
      /** Force show badge even when count is 0 */
      forceShow?: boolean
    }>(),
    {
      count: 0,
      priority: 'info',
      max: 99,
      forceShow: false
    }
  )

  /**
   * Whether to show the badge
   */
  const hasNotifications = computed(() => {
    if (props.count < 0) return false // Don't show negative counts
    return props.forceShow || props.count > 0
  })

  /**
   * Display count (respects max)
   */
  const displayCount = computed(() => {
    return props.count
  })

  /**
   * Badge color based on priority
   */
  const badgeColor = computed(() => {
    switch (props.priority) {
      case 'critical':
        return 'error'
      case 'warning':
        return 'warning'
      case 'info':
      default:
        return 'info'
    }
  })
</script>
