/**
 * useRoleColors Composable
 *
 * Shared composable for scope role colors and icons.
 *
 * **DRY FIX**: Eliminates duplication across 3+ components
 * (ScopeDashboard, MemberManagement).
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
 * <script setup lang="ts">
 * import { useRoleColors } from '@/composables/useRoleColors'
 * const { getRoleColor, getRoleIcon } = useRoleColors()
 * </script>
 * ```
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-11-create-role-colors-composable
 */

export interface UseRoleColorsReturn {
  roleColors: Readonly<Record<string, string>>
  roleIcons: Readonly<Record<string, string>>
  getRoleColor: (role: string) => string
  getRoleIcon: (role: string) => string
}

/**
 * Get role colors and icons for scope roles
 */
export function useRoleColors(): UseRoleColorsReturn {
  /**
   * Role color mapping (Vuetify color names)
   * Frozen for immutability - these are constants
   */
  const roleColors: Readonly<Record<string, string>> = Object.freeze({
    admin: 'red',
    curator: 'blue',
    reviewer: 'green',
    viewer: 'grey'
  })

  /**
   * Role icon mapping (Material Design Icons)
   * Frozen for immutability - these are constants
   */
  const roleIcons: Readonly<Record<string, string>> = Object.freeze({
    admin: 'mdi-shield-crown',
    curator: 'mdi-pencil',
    reviewer: 'mdi-check-circle',
    viewer: 'mdi-eye'
  })

  /**
   * Get color for a specific role
   * @param role - Role name (admin, curator, reviewer, viewer)
   * @returns Vuetify color name
   */
  const getRoleColor = (role: string): string => {
    return roleColors[role] || 'grey'
  }

  /**
   * Get icon for a specific role
   * @param role - Role name (admin, curator, reviewer, viewer)
   * @returns Material Design Icon name
   */
  const getRoleIcon = (role: string): string => {
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
