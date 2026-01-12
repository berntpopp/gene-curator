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
 * <template>
 *   <div>
 *     <v-chip :prepend-icon="getScopeVisibilityIcon(scope.is_public)">
 *       {{ getScopeVisibilityLabel(scope.is_public) }}
 *     </v-chip>
 *     <div>Due: {{ formatDate(scope.due_date) }}</div>
 *     <v-progress-linear :model-value="progress"></v-progress-linear>
 *   </div>
 * </template>
 *
 * <script setup>
 * import { computed } from 'vue'
 * import { useScopeUtils } from '@/composables/useScopeUtils'
 *
 * const { formatDate, calculateProgress, getScopeVisibilityIcon, getScopeVisibilityLabel } = useScopeUtils()
 * const progress = computed(() => calculateProgress(scope.value.completed, scope.value.total))
 * </script>
 * ```
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-12-create-scope-utilities-composable
 */

/**
 * Get utility functions for scope operations
 * @returns {Object} Scope utility functions
 */
export function useScopeUtils() {
  /**
   * Format date for display
   * Converts ISO date string to locale date string
   *
   * @param {string|Date|null} date - Date to format (ISO string or Date object)
   * @returns {string} Formatted date string or 'No due date'
   *
   * @example
   * formatDate('2025-12-31') // "12/31/2025" (US locale)
   * formatDate(null) // "No due date"
   */
  const formatDate = date => {
    if (!date) return 'No due date'

    try {
      const dateObj = typeof date === 'string' ? new Date(date) : date
      return dateObj.toLocaleDateString()
    } catch (error) {
      console.error('Invalid date format:', date, error)
      return 'Invalid date'
    }
  }

  /**
   * Calculate progress percentage
   * Returns rounded percentage (0-100)
   *
   * @param {number} completed - Number of completed items
   * @param {number} total - Total number of items
   * @returns {number} Progress percentage (0-100)
   *
   * @example
   * calculateProgress(7, 10) // 70
   * calculateProgress(0, 10) // 0
   * calculateProgress(5, 0) // 0 (handles division by zero)
   */
  const calculateProgress = (completed, total) => {
    if (!total || total === 0) return 0
    if (!completed || completed < 0) return 0

    const progress = (completed / total) * 100
    return Math.round(Math.min(progress, 100)) // Cap at 100%
  }

  /**
   * Get icon for scope visibility
   *
   * @param {boolean} isPublic - Whether scope is public
   * @returns {string} Material Design Icon name
   *
   * @example
   * getScopeVisibilityIcon(true) // 'mdi-earth' (public)
   * getScopeVisibilityIcon(false) // 'mdi-lock' (private)
   */
  const getScopeVisibilityIcon = isPublic => {
    return isPublic ? 'mdi-earth' : 'mdi-lock'
  }

  /**
   * Get label for scope visibility
   *
   * @param {boolean} isPublic - Whether scope is public
   * @returns {string} Visibility label
   *
   * @example
   * getScopeVisibilityLabel(true) // 'Public'
   * getScopeVisibilityLabel(false) // 'Private'
   */
  const getScopeVisibilityLabel = isPublic => {
    return isPublic ? 'Public' : 'Private'
  }

  /**
   * Format scope name for display
   * Converts machine-readable name to title case
   *
   * @param {string} name - Machine-readable scope name (e.g., 'kidney-genetics')
   * @returns {string} Title case name (e.g., 'Kidney Genetics')
   *
   * @example
   * formatScopeName('kidney-genetics') // 'Kidney Genetics'
   * formatScopeName('neuro-oncology') // 'Neuro Oncology'
   */
  const formatScopeName = name => {
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
   * @param {string} name - Scope name to validate
   * @returns {boolean} True if valid
   *
   * @example
   * isValidScopeName('kidney-genetics') // true
   * isValidScopeName('Kidney Genetics') // false (uppercase)
   * isValidScopeName('kidney_genetics') // false (underscore)
   */
  const isValidScopeName = name => {
    if (!name || typeof name !== 'string') return false

    // Must be lowercase with dashes, 4-64 chars, no consecutive dashes
    const nameRegex = /^[a-z][a-z0-9-]{2,62}[a-z0-9]$/
    return nameRegex.test(name) && !name.includes('--')
  }

  return {
    formatDate,
    calculateProgress,
    getScopeVisibilityIcon,
    getScopeVisibilityLabel,
    formatScopeName,
    isValidScopeName
  }
}

export default useScopeUtils
