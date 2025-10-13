<template>
  <v-list-item
    :to="to"
    :href="href"
    :target="href ? '_blank' : undefined"
    :rel="href ? 'noopener noreferrer' : undefined"
    :disabled="disabled"
    :class="itemClasses"
    :aria-label="ariaLabel || label"
    :aria-current="isCurrent ? 'page' : undefined"
    @click="handleClick"
  >
    <template v-if="icon" #prepend>
      <v-icon :color="iconColor">{{ icon }}</v-icon>
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

<script setup>
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
  import { useRoute } from 'vue-router'

  const props = defineProps({
    /**
     * Router link destination
     * Use this for internal navigation
     */
    to: {
      type: Object,
      default: null
    },

    /**
     * External link href
     * Use this for external links
     */
    href: {
      type: String,
      default: null
    },

    /**
     * Icon name (Material Design Icons)
     */
    icon: {
      type: String,
      default: null
    },

    /**
     * Icon color (Vuetify color)
     */
    iconColor: {
      type: String,
      default: null
    },

    /**
     * Item label text
     */
    label: {
      type: String,
      required: true
    },

    /**
     * Badge content (number or string)
     * Shows a badge on the right side
     */
    badge: {
      type: [String, Number],
      default: null
    },

    /**
     * Badge color (Vuetify color)
     */
    badgeColor: {
      type: String,
      default: 'error'
    },

    /**
     * Disabled state
     */
    disabled: {
      type: Boolean,
      default: false
    },

    /**
     * ARIA label override
     * Defaults to label if not provided
     */
    ariaLabel: {
      type: String,
      default: null
    }
  })

  const emit = defineEmits(['click'])

  const route = useRoute()

  /**
   * Check if this item is the current page
   */
  const isCurrent = computed(() => {
    if (!props.to) return false

    // Match by route name
    if (props.to.name) {
      return route.name === props.to.name
    }

    // Match by route path
    if (props.to.path) {
      return route.path === props.to.path
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
  const handleClick = event => {
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
