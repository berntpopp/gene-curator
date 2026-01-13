<!--
  Member Management Component

  **Updated** - Now uses GitHub-style invitation workflow

  **DRY Improvements**:
  - Uses useRoleColors composable (no duplicate role color logic)
  - Uses useScopePermissions composable (permission checking)
  - Uses logService (no console.log/console.error)
  - Uses InviteMemberDialog (reusable invite component)

  **SOLID-SRP**:
  - Component: UI rendering and user interactions only
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **Features**:
  - List all scope members with roles
  - Show pending invitations with "Invited" status
  - Invite new members (user search with autocomplete)
  - Update member roles (admin only)
  - Remove members (admin only)
  - Role-based UI (different views for admin/curator/viewer)

  @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-32-member-management-component
-->

<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-account-group</v-icon>
      Scope Members
      <v-spacer />
      <v-btn
        v-if="canInviteMembers"
        color="primary"
        prepend-icon="mdi-account-plus"
        @click="showInviteDialog = true"
      >
        Invite Member
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Loading state -->
      <v-progress-linear v-if="loading" indeterminate />

      <!-- Members list -->
      <v-list v-else-if="members.length > 0">
        <v-list-item v-for="member in members" :key="member.user_id">
          <template #prepend>
            <v-avatar :color="getRoleColor(member.role)">
              <v-icon :icon="getRoleIcon(member.role)" color="white"></v-icon>
            </v-avatar>
          </template>

          <v-list-item-title>
            {{ member.user_full_name || member.user_username || member.user_email }}
          </v-list-item-title>

          <v-list-item-subtitle>
            {{ member.user_email }}
            <span v-if="member.user_orcid" class="text-caption ml-2">
              (ORCID: {{ member.user_orcid }})
            </span>
          </v-list-item-subtitle>

          <template #append>
            <!-- Pending/Invited chip -->
            <v-chip
              v-if="member.is_pending"
              color="warning"
              variant="outlined"
              size="small"
              class="mr-2"
              prepend-icon="mdi-clock-outline"
            >
              Invited
            </v-chip>

            <!-- Role chip -->
            <v-chip
              :color="getRoleColor(member.role)"
              :prepend-icon="getRoleIcon(member.role)"
              size="small"
              class="mr-2"
            >
              {{ member.role }}
            </v-chip>

            <!-- Actions (admin only) -->
            <v-menu v-if="canEditMemberRoles && member.user_id !== currentUserId">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-dots-vertical" size="small" variant="text"></v-btn>
              </template>

              <v-list>
                <v-list-subheader>Change Role</v-list-subheader>

                <v-list-item
                  v-for="role in availableRoles"
                  :key="role"
                  :active="member.role === role"
                  @click="updateRole(member.user_id, role)"
                >
                  <template #prepend>
                    <v-icon :icon="getRoleIcon(role)" :color="getRoleColor(role)"></v-icon>
                  </template>
                  <v-list-item-title>{{ role }}</v-list-item-title>
                </v-list-item>

                <v-divider />

                <v-list-item
                  v-if="canRemoveMembers"
                  prepend-icon="mdi-delete"
                  base-color="error"
                  @click="confirmRemoveMember(member)"
                >
                  <v-list-item-title>Remove Member</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </template>
        </v-list-item>
      </v-list>

      <!-- Empty state -->
      <v-alert v-else type="info" variant="tonal" icon="mdi-information">
        No members found. Invite members to get started.
      </v-alert>
    </v-card-text>

    <!-- Invite Member Dialog (Reusable Component) -->
    <InviteMemberDialog
      v-model="showInviteDialog"
      :scope-id="scopeId"
      :existing-member-ids="existingMemberIds"
      @invited="handleInvited"
    />

    <!-- Confirm Remove Member Dialog -->
    <v-dialog v-model="showRemoveDialog" max-width="500">
      <v-card>
        <v-card-title>Remove Member</v-card-title>

        <v-card-text>
          Are you sure you want to remove
          <strong>{{
            memberToRemove?.user_full_name ||
            memberToRemove?.user_username ||
            memberToRemove?.user_email
          }}</strong>
          from this scope?
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showRemoveDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="removing" @click="removeMember"> Remove </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
      <template #actions>
        <v-btn color="white" variant="text" @click="showSnackbar = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useScopesStore } from '@/stores/scopes'
  import { useAuthStore } from '@/stores/auth'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useLogger } from '@/composables/useLogger'
  import InviteMemberDialog from '@/components/scope/InviteMemberDialog.vue'
  import { scopeService } from '@/services/scopeService'

  // ============================================
  // PROPS
  // ============================================

  const props = defineProps({
    scopeId: {
      type: String,
      required: true
    }
  })

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const scopeStore = useScopesStore()
  const authStore = useAuthStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const logger = useLogger()

  const userRole = computed(() => scopeStore.currentUserRole)
  const { canInviteMembers, canEditMemberRoles, canRemoveMembers } = useScopePermissions(userRole)

  // ============================================
  // STATE
  // ============================================

  const members = ref([])
  const loading = ref(false)
  const showInviteDialog = ref(false)
  const showRemoveDialog = ref(false)
  const removing = ref(false)

  const memberToRemove = ref(null)

  // Snackbar
  const showSnackbar = ref(false)
  const snackbarMessage = ref('')
  const snackbarColor = ref('success')

  /**
   * Existing member IDs (for excluding from search)
   */
  const existingMemberIds = computed(() => {
    return members.value.map(m => m.user_id)
  })

  // ============================================
  // COMPUTED
  // ============================================

  const currentUserId = computed(() => authStore.user?.id)

  const availableRoles = ['admin', 'curator', 'reviewer', 'viewer']

  // ============================================
  // METHODS
  // ============================================

  /**
   * Fetch scope members (including pending invitations)
   */
  const fetchMembers = async () => {
    loading.value = true

    try {
      logger.debug('Fetching scope members', { scope_id: props.scopeId })
      // Include pending invitations to show "Invited" status
      const data = await scopeService.fetchMembers(props.scopeId, { includePending: true })
      members.value = data
      logger.info('Members fetched successfully', {
        scope_id: props.scopeId,
        count: data.length,
        pending: data.filter(m => m.is_pending).length
      })
    } catch (error) {
      logger.error('Failed to fetch members', {
        scope_id: props.scopeId,
        error: error.message,
        stack: error.stack
      })
      showNotification('Failed to load members', 'error')
    } finally {
      loading.value = false
    }
  }

  /**
   * Handle successful invitation from InviteMemberDialog
   */
  const handleInvited = async invitationResult => {
    logger.info('Member invited successfully', {
      scope_id: props.scopeId,
      user_name: invitationResult.userName,
      membership_id: invitationResult.id
    })

    showNotification(
      `Invitation sent to ${invitationResult.userName || invitationResult.userEmail}`,
      'success'
    )

    // Refresh member list to show new pending invitation
    await fetchMembers()
  }

  /**
   * Update member role
   */
  const updateRole = async (userId, newRole) => {
    try {
      logger.debug('Updating member role', {
        scope_id: props.scopeId,
        user_id: userId,
        new_role: newRole
      })

      await scopeStore.updateMemberRole(props.scopeId, userId, newRole)

      logger.info('Member role updated', {
        scope_id: props.scopeId,
        user_id: userId,
        new_role: newRole
      })

      showNotification('Member role updated successfully', 'success')
      await fetchMembers()
    } catch (error) {
      logger.error('Failed to update member role', {
        scope_id: props.scopeId,
        user_id: userId,
        error: error.message,
        stack: error.stack
      })
      showNotification('Failed to update member role', 'error')
    }
  }

  /**
   * Show remove confirmation dialog
   */
  const confirmRemoveMember = member => {
    memberToRemove.value = member
    showRemoveDialog.value = true
  }

  /**
   * Remove member from scope
   */
  const removeMember = async () => {
    if (!memberToRemove.value) return

    removing.value = true

    try {
      logger.debug('Removing member', {
        scope_id: props.scopeId,
        user_id: memberToRemove.value.user_id
      })

      await scopeStore.removeMember(props.scopeId, memberToRemove.value.user_id)

      logger.info('Member removed', {
        scope_id: props.scopeId,
        user_id: memberToRemove.value.user_id
      })

      showNotification('Member removed successfully', 'success')
      showRemoveDialog.value = false
      memberToRemove.value = null
      await fetchMembers()
    } catch (error) {
      logger.error('Failed to remove member', {
        scope_id: props.scopeId,
        user_id: memberToRemove.value.user_id,
        error: error.message,
        stack: error.stack
      })
      showNotification('Failed to remove member', 'error')
    } finally {
      removing.value = false
    }
  }

  /**
   * Show notification snackbar
   */
  const showNotification = (message, color = 'success') => {
    snackbarMessage.value = message
    snackbarColor.value = color
    showSnackbar.value = true
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  onMounted(async () => {
    await fetchMembers()
  })
</script>

<style scoped>
  .v-list-item {
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }

  .v-list-item:last-child {
    border-bottom: none;
  }
</style>
