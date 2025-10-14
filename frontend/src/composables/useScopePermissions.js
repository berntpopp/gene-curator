/**
 * useScopePermissions Composable
 *
 * Scope-level permission checking utilities.
 *
 * **Scope vs Application Permissions**:
 * - Application permissions (usePermissions): Based on global user role (admin, curator, reviewer, viewer)
 * - Scope permissions (this composable): Based on role within a specific scope
 *
 * **Scope Roles**:
 * - admin: Full control (manage scope, invite members, curate, review)
 * - curator: Can curate genes within scope
 * - reviewer: Can review curations within scope
 * - viewer: Read-only access to scope
 *
 * **Benefits**:
 * - DRY: Centralized scope permission logic
 * - Reactive: Automatically updates when user role changes
 * - Type-safe: Clear permission definitions
 * - Testable: Pure computed properties
 *
 * @example
 * ```vue
 * <template>
 *   <v-btn v-if="canManageScope" @click="editScope">Edit Scope</v-btn>
 *   <v-btn v-if="canInviteMembers" @click="inviteMember">Invite Member</v-btn>
 *   <v-btn v-if="canCurate" @click="createCuration">New Curation</v-btn>
 * </template>
 *
 * <script setup>
 * import { computed } from 'vue'
 * import { useScopeStore } from '@/stores/scopes'
 * import { useScopePermissions } from '@/composables/useScopePermissions'
 *
 * const scopeStore = useScopeStore()
 * const userRole = computed(() => scopeStore.currentUserRole)
 * const { canManageScope, canInviteMembers, canCurate } = useScopePermissions(userRole)
 * </script>
 * ```
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-13-create-permission-checker-composable
 */

import { computed, isRef, unref } from 'vue'

/**
 * Get permission checks for a scope role
 *
 * @param {Ref<string>|string} userRole - User's role within the scope (reactive or static)
 * @returns {Object} Permission checking computed properties
 */
export function useScopePermissions(userRole) {
  /**
   * Get the actual role value (handles both Ref and plain strings)
   * @returns {string|null} Role value
   */
  const getRole = () => {
    const role = isRef(userRole) ? unref(userRole) : userRole
    return role || null
  }

  /**
   * Can manage scope (settings, members, permissions)
   * Only scope admins
   */
  const canManageScope = computed(() => {
    return getRole() === 'admin'
  })

  /**
   * Can invite members to scope
   * Only scope admins
   */
  const canInviteMembers = computed(() => {
    return getRole() === 'admin'
  })

  /**
   * Can curate genes within scope
   * Admins and curators
   */
  const canCurate = computed(() => {
    const role = getRole()
    return role === 'admin' || role === 'curator'
  })

  /**
   * Can review curations within scope
   * Admins and reviewers
   */
  const canReview = computed(() => {
    const role = getRole()
    return role === 'admin' || role === 'reviewer'
  })

  /**
   * Can view members list
   * All roles except viewers
   */
  const canViewMembers = computed(() => {
    const role = getRole()
    return role === 'admin' || role === 'curator' || role === 'reviewer'
  })

  /**
   * Can edit member roles
   * Only scope admins
   */
  const canEditMemberRoles = computed(() => {
    return getRole() === 'admin'
  })

  /**
   * Can remove members from scope
   * Only scope admins
   */
  const canRemoveMembers = computed(() => {
    return getRole() === 'admin'
  })

  /**
   * Can view scope statistics
   * All roles except viewers
   */
  const canViewStatistics = computed(() => {
    const role = getRole()
    return role === 'admin' || role === 'curator' || role === 'reviewer'
  })

  /**
   * Can create assignments within scope
   * Admins and curators
   */
  const canCreateAssignments = computed(() => {
    const role = getRole()
    return role === 'admin' || role === 'curator'
  })

  /**
   * Can manage workflows within scope
   * Only scope admins
   */
  const canManageWorkflows = computed(() => {
    return getRole() === 'admin'
  })

  /**
   * Is viewer role (read-only)
   * Helper to show/hide read-only UI elements
   */
  const isViewer = computed(() => {
    return getRole() === 'viewer'
  })

  /**
   * Is admin role
   * Helper for conditional rendering
   */
  const isAdmin = computed(() => {
    return getRole() === 'admin'
  })

  /**
   * Is curator role
   * Helper for conditional rendering
   */
  const isCurator = computed(() => {
    return getRole() === 'curator'
  })

  /**
   * Is reviewer role
   * Helper for conditional rendering
   */
  const isReviewer = computed(() => {
    return getRole() === 'reviewer'
  })

  /**
   * Has any role in scope
   * Useful for checking if user is a scope member
   */
  const hasAnyRole = computed(() => {
    return getRole() !== null
  })

  return {
    // Permission checks
    canManageScope,
    canInviteMembers,
    canCurate,
    canReview,
    canViewMembers,
    canEditMemberRoles,
    canRemoveMembers,
    canViewStatistics,
    canCreateAssignments,
    canManageWorkflows,

    // Role checks
    isViewer,
    isAdmin,
    isCurator,
    isReviewer,
    hasAnyRole
  }
}

export default useScopePermissions
