/**
 * useScopeUtils Composable
 *
 * Utility functions for scope operations.
 *
 * Provides reusable formatting and calculation functions for:
 * - Date formatting (ISO to locale)
 * - Progress calculation (completed/total → percentage)
 * - Scope visibility (public/private icons and labels)
 *
 * **Benefits**:
 * - DRY: Centralized formatting logic
 * - Consistency: Same date/progress format everywhere
 * - Testability: Pure functions, easy to test
 *
 * @example
 * ```vue
 * <script setup lang="ts">
 * import { computed } from 'vue'
 * import { useScopeUtils } from '@/composables/useScopeUtils'
 *
 * const { calculateProgress, getScopeVisibilityIcon, getScopeVisibilityLabel } = useScopeUtils()
 * const progress = computed(() => calculateProgress(scope.value.completed, scope.value.total))
 * </script>
 * ```
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-12-create-scope-utilities-composable
 */

export interface UseScopeUtilsReturn {
  calculateProgress: (
    completed: number | null | undefined,
    total: number | null | undefined
  ) => number
  getScopeVisibilityIcon: (isPublic: boolean) => string
  getScopeVisibilityLabel: (isPublic: boolean) => string
  formatScopeName: (name: string | null | undefined) => string
  isValidScopeName: (name: string | null | undefined) => boolean
}

/**
 * Get utility functions for scope operations
 */
export function useScopeUtils(): UseScopeUtilsReturn {
  /**
   * Calculate progress percentage
   * Returns rounded percentage (0-100)
   *
   * @example
   * calculateProgress(7, 10) // 70
   * calculateProgress(0, 10) // 0
   * calculateProgress(5, 0) // 0 (handles division by zero)
   */
  const calculateProgress = (
    completed: number | null | undefined,
    total: number | null | undefined
  ): number => {
    if (!total || total === 0) return 0
    if (!completed || completed < 0) return 0

    const progress = (completed / total) * 100
    return Math.round(Math.min(progress, 100)) // Cap at 100%
  }

  /**
   * Get icon for scope visibility
   *
   * @example
   * getScopeVisibilityIcon(true) // 'mdi-earth' (public)
   * getScopeVisibilityIcon(false) // 'mdi-lock' (private)
   */
  const getScopeVisibilityIcon = (isPublic: boolean): string => {
    return isPublic ? 'mdi-earth' : 'mdi-lock'
  }

  /**
   * Get label for scope visibility
   *
   * @example
   * getScopeVisibilityLabel(true) // 'Public'
   * getScopeVisibilityLabel(false) // 'Private'
   */
  const getScopeVisibilityLabel = (isPublic: boolean): string => {
    return isPublic ? 'Public' : 'Private'
  }

  /**
   * Format scope name for display
   * Converts machine-readable name to title case
   *
   * @example
   * formatScopeName('kidney-genetics') // 'Kidney Genetics'
   * formatScopeName('neuro-oncology') // 'Neuro Oncology'
   */
  const formatScopeName = (name: string | null | undefined): string => {
    if (!name) return ''

    return name
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  /**
   * Validate scope name format
   * Checks if name follows naming convention (lowercase-with-dashes)
   *
   * @example
   * isValidScopeName('kidney-genetics') // true
   * isValidScopeName('Kidney Genetics') // false (uppercase)
   * isValidScopeName('kidney_genetics') // false (underscore)
   */
  const isValidScopeName = (name: string | null | undefined): boolean => {
    if (!name || typeof name !== 'string') return false

    // Must be lowercase with dashes, 4-64 chars, no consecutive dashes
    const nameRegex = /^[a-z][a-z0-9-]{2,62}[a-z0-9]$/
    return nameRegex.test(name) && !name.includes('--')
  }

  return {
    calculateProgress,
    getScopeVisibilityIcon,
    getScopeVisibilityLabel,
    formatScopeName,
    isValidScopeName
  }
}

export default useScopeUtils
