/**
 * useRoleColors Composable
 *
 * Shared composable for scope role colors and icons.
 *
 * **DRY FIX**: Eliminates duplication across 3+ components
 * (ScopeSelector, ScopeDashboard, MemberManagement).
 *
 * Provides consistent visual representation of scope-level roles:
 * - admin: Red (highest privileges)
 * - curator: Blue (content creation)
 * - reviewer: Green (quality assurance)
 * - viewer: Grey (read-only access)
 *
 * @example
 * ```vue
 * <template>
 *   <v-chip :color="getRoleColor(member.role)" :prepend-icon="getRoleIcon(member.role)">
 *     {{ member.role }}
 *   </v-chip>
 * </template>
 *
 * <script setup>
 * import { useRoleColors } from '@/composables/useRoleColors'
 * const { getRoleColor, getRoleIcon } = useRoleColors()
 * </script>
 * ```
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-11-create-role-colors-composable
 */

/**
 * Get role colors and icons for scope roles
 * @returns {Object} Role colors and utility functions
 */
export function useRoleColors() {
  /**
   * Role color mapping (Vuetify color names)
   * Frozen for immutability - these are constants
   */
  const roleColors = Object.freeze({
    admin: 'red',
    curator: 'blue',
    reviewer: 'green',
    viewer: 'grey'
  })

  /**
   * Role icon mapping (Material Design Icons)
   * Frozen for immutability - these are constants
   */
  const roleIcons = Object.freeze({
    admin: 'mdi-shield-crown',
    curator: 'mdi-pencil',
    reviewer: 'mdi-check-circle',
    viewer: 'mdi-eye'
  })

  /**
   * Get color for a specific role
   * @param {string} role - Role name (admin, curator, reviewer, viewer)
   * @returns {string} Vuetify color name
   */
  const getRoleColor = role => {
    return roleColors[role] || 'grey'
  }

  /**
   * Get icon for a specific role
   * @param {string} role - Role name (admin, curator, reviewer, viewer)
   * @returns {string} Material Design Icon name
   */
  const getRoleIcon = role => {
    return roleIcons[role] || 'mdi-account'
  }

  return {
    roleColors,
    roleIcons,
    getRoleColor,
    getRoleIcon
  }
}

export default useRoleColors
