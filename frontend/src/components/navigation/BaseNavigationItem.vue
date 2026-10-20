<template>
  <v-list-item
    :to="to ?? undefined"
    :href="href ?? undefined"
    :target="href ? '_blank' : undefined"
    :rel="href ? 'noopener noreferrer' : undefined"
    :disabled="disabled"
    :class="itemClasses"
    :aria-label="ariaLabel || label"
    :aria-current="isCurrent ? 'page' : undefined"
    @click="handleClick"
  >
    <template v-if="icon" #prepend>
      <v-icon :color="iconColor ?? undefined">{{ icon }}</v-icon>
    </template>

    <v-list-item-title>
      {{ label }}
    </v-list-item-title>

    <template v-if="badge || $slots.append" #append>
      <slot name="append">
        <v-badge v-if="badge" :content="badge" :color="badgeColor" inline />
      </slot>
    </template>
  </v-list-item>
</template>

<script setup lang="ts">
  /**
   * BaseNavigationItem Component
   *
   * Reusable navigation item component for all menus (main nav, user menu, mobile nav).
   * Provides consistent styling, accessibility, and behavior.
   *
   * Features:
   * - Router link or external link support
   * - Badge support (notifications, counts)
   * - Icon support with custom colors
   * - Active state styling
   * - Accessibility (ARIA labels, current page indicator)
   * - Click event handling for non-link items
   *
   * @example
   * ```vue
   * <BaseNavigationItem
   *   :to="{ name: 'Dashboard' }"
   *   icon="mdi-view-dashboard"
   *   label="Dashboard"
   *   :badge="5"
   * />
   * ```
   */

  import { computed } from 'vue'
  import { useRoute, type RouteLocationRaw } from 'vue-router'

  const props = withDefaults(
    defineProps<{
      /** Router link destination (internal navigation) */
      to?: RouteLocationRaw | null
      /** External link href (external links) */
      href?: string | null
      /** Icon name (Material Design Icons) */
      icon?: string | null
      /** Icon color (Vuetify color) */
      iconColor?: string | null
      /** Item label text */
      label: string
      /** Badge content, shown on the right side */
      badge?: string | number | null
      /** Badge color (Vuetify color) */
      badgeColor?: string
      /** Disabled state */
      disabled?: boolean
      /** ARIA label override, defaults to label */
      ariaLabel?: string | null
    }>(),
    {
      to: null,
      href: null,
      icon: null,
      iconColor: null,
      badge: null,
      badgeColor: 'error',
      disabled: false,
      ariaLabel: null
    }
  )

  const emit = defineEmits<{ click: [event: Event] }>()

  const route = useRoute()

  /**
   * Check if this item is the current page
   */
  const isCurrent = computed(() => {
    const target = props.to
    if (!target || typeof target === 'string') return false

    // Match by route name
    if ('name' in target && target.name) {
      return route.name === target.name
    }

    // Match by route path
    if ('path' in target && target.path) {
      return route.path === target.path
    }

    return false
  })

  /**
   * Dynamic classes for the item
   */
  const itemClasses = computed(() => ({
    'base-navigation-item': true,
    'base-navigation-item--active': isCurrent.value,
    'base-navigation-item--disabled': props.disabled
  }))

  /**
   * Handle click event
   * Only emits for non-link items (no to or href)
   */
  const handleClick = (event: Event) => {
    if (!props.to && !props.href) {
      event.preventDefault()
      emit('click', event)
    }
  }
</script>

<style scoped>
  .base-navigation-item {
    transition: background-color 0.2s ease;
  }

  .base-navigation-item--active {
    background-color: rgba(var(--v-theme-primary), 0.1);
    color: rgb(var(--v-theme-primary));
  }

  .base-navigation-item--disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  .base-navigation-item:hover:not(.base-navigation-item--disabled) {
    background-color: rgba(var(--v-theme-surface-variant), 0.1);
  }
</style>
