/**
 * usePermissions Composable
 *
 * Provides reactive permission checking for role-based access control.
 * Wraps the auth store with computed properties for better performance
 * and provides a single source of truth for all permission checks.
 *
 * Benefits:
 * - DRY: No scattered role checks throughout components
 * - Type-safe: Centralized permission definitions
 * - Reactive: Automatically updates when auth state changes
 * - Testable: Easy to mock for testing
 *
 * @example
 * ```vue
 * <template>
 *   <v-btn v-if="can.createCuration" @click="create">New Curation</v-btn>
 * </template>
 *
 * <script setup>
 * import { usePermissions } from '@/composables/usePermissions'
 * const { can } = usePermissions()
 * </script>
 * ```
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#permissions-management-dry
 */

import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * Permission check composable
 * @returns {Object} Permission checking utilities
 */
export function usePermissions() {
  const authStore = useAuthStore()

  /**
   * Reactive permission checks
   * Each property is a computed that automatically updates with auth state
   */
  const can = {
    // ========================================
    // View Permissions
    // ========================================

    /**
     * Can view dashboard (any authenticated user)
     */
    viewDashboard: computed(() => authStore.isAuthenticated),

    /**
     * Can view curations (curator, reviewer, admin)
     */
    viewCurations: computed(() => authStore.hasAnyRole(['curator', 'reviewer', 'admin'])),

    /**
     * Can view validation dashboard (curator, reviewer, admin)
     */
    viewValidation: computed(() => authStore.hasAnyRole(['curator', 'reviewer', 'admin'])),

    /**
     * Can view admin pages (admin only)
     */
    viewAdminPages: computed(() => authStore.hasRole('admin')),

    // ========================================
    // Action Permissions
    // ========================================

    /**
     * Can create assignments (curator, admin)
     */
    createAssignment: computed(() => authStore.hasAnyRole(['curator', 'admin'])),

    /**
     * Can create precurations (curator, admin)
     */
    createPrecuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),

    /**
     * Can create curations (curator, admin)
     */
    createCuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),

    /**
     * Can review curations (reviewer, admin)
     */
    reviewCuration: computed(() => authStore.hasAnyRole(['reviewer', 'admin'])),

    /**
     * Can edit own curations (curator, admin)
     */
    editOwnCuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),

    /**
     * Can delete own curations (curator, admin)
     */
    deleteOwnCuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),

    /**
     * Can submit for review (curator, admin)
     */
    submitForReview: computed(() => authStore.hasAnyRole(['curator', 'admin'])),

    /**
     * Can approve curations (reviewer, admin)
     */
    approveCuration: computed(() => authStore.hasAnyRole(['reviewer', 'admin'])),

    /**
     * Can reject curations (reviewer, admin)
     */
    rejectCuration: computed(() => authStore.hasAnyRole(['reviewer', 'admin'])),

    // ========================================
    // Admin Permissions
    // ========================================

    /**
     * Can manage users (admin only)
     */
    manageUsers: computed(() => authStore.hasRole('admin')),

    /**
     * Can manage genes (admin only)
     */
    manageGenes: computed(() => authStore.hasRole('admin')),

    /**
     * Can configure curation settings (admin only)
     */
    configureCuration: computed(() => authStore.hasRole('admin')),

    /**
     * Can manage scopes (admin only)
     */
    manageScopes: computed(() => authStore.hasRole('admin')),

    /**
     * Can manage schemas (admin only)
     */
    manageSchemas: computed(() => authStore.hasRole('admin')),

    /**
     * Can manage workflows (admin only)
     */
    manageWorkflows: computed(() => authStore.hasRole('admin')),

    // ========================================
    // Scope Admin Permissions
    // ========================================

    /**
     * Can manage users within scope (scope_admin, admin)
     */
    manageScopeUsers: computed(() => authStore.hasAnyRole(['scope_admin', 'admin'])),

    /**
     * Can assign curators within scope (scope_admin, admin)
     */
    assignCurators: computed(() => authStore.hasAnyRole(['scope_admin', 'admin'])),

    /**
     * Can view scope statistics (scope_admin, admin)
     */
    viewScopeStats: computed(() => authStore.hasAnyRole(['scope_admin', 'admin'])),

    // ========================================
    // Helper Methods
    // ========================================

    /**
     * Check if user has specific role
     * @param {string} role - Role to check
     * @returns {boolean} True if user has role
     */
    hasRole: role => authStore.hasRole(role),

    /**
     * Check if user has any of the specified roles
     * @param {string[]} roles - Array of roles to check
     * @returns {boolean} True if user has any role
     */
    hasAnyRole: roles => authStore.hasAnyRole(roles),

    /**
     * Check if user has all of the specified roles
     * @param {string[]} roles - Array of roles to check
     * @returns {boolean} True if user has all roles
     */
    hasAllRoles: roles => roles.every(role => authStore.hasRole(role))
  }

  /**
   * Get user information
   */
  const user = computed(() => authStore.user)
  const userRole = computed(() => authStore.userRole)
  const isAuthenticated = computed(() => authStore.isAuthenticated)

  return {
    can,
    user,
    userRole,
    isAuthenticated
  }
}

export default usePermissions
