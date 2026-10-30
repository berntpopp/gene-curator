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
  <v-card variant="flat" border>
    <div class="d-flex align-center px-4 pt-4">
      <h2 class="text-title-medium">Scope members</h2>
      <v-spacer />
      <v-btn
        v-if="canInviteMembers"
        color="primary"
        variant="flat"
        prepend-icon="mdi-account-plus"
        @click="showInviteDialog = true"
      >
        Invite member
      </v-btn>
    </div>
    <p v-if="!canEditMemberRoles" class="px-4 text-body-medium text-medium-emphasis">
      Only scope admins can manage members.
    </p>

    <v-card-text>
      <v-progress-linear v-if="loading" indeterminate />

      <v-list v-else-if="members.length > 0">
        <v-list-item v-for="member in members" :key="member.user_id">
          <template #prepend>
            <v-avatar color="surface-variant" size="36" class="text-body-small">
              {{ initials(member) }}
            </v-avatar>
          </template>

          <v-list-item-title>{{ displayName(member) }}</v-list-item-title>

          <v-list-item-subtitle>
            {{ member.user_email }}
            <a
              v-if="member.user_orcid"
              class="ml-2 text-primary"
              :href="`https://orcid.org/${member.user_orcid}`"
              target="_blank"
              rel="noopener noreferrer"
            >
              ORCID {{ member.user_orcid }}
            </a>
            <span v-if="member.is_pending" class="ml-2 text-warning">
              Invited {{ formatDate(member.invited_at) }}
            </span>
          </v-list-item-subtitle>

          <template #append>
            <span class="text-body-medium mr-2">{{ roleLabel(member.role) }}</span>

            <v-menu v-if="canEditMemberRoles && member.user_id !== currentUserId">
              <template #activator="{ props: activatorProps }">
                <v-btn
                  aria-label="Member actions"
                  v-bind="activatorProps"
                  icon="mdi-dots-vertical"
                  size="small"
                  variant="text"
                ></v-btn>
              </template>

              <v-list>
                <v-list-subheader>Change role</v-list-subheader>

                <v-list-item
                  v-for="role in availableRoles"
                  :key="role"
                  :active="member.role === role"
                  @click="requestRoleChange(member, role)"
                >
                  <v-list-item-title>{{ roleLabel(role) }}</v-list-item-title>
                </v-list-item>

                <v-divider />

                <v-list-item
                  v-if="canRemoveMembers"
                  base-color="error"
                  @click="confirmRemoveMember(member)"
                >
                  <v-list-item-title>
                    {{ member.is_pending ? 'Revoke invitation' : 'Remove member' }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </template>
        </v-list-item>
      </v-list>

      <p v-else class="text-medium-emphasis">No members found. Invite members to get started.</p>
    </v-card-text>

    <!-- Invite Member Dialog (Reusable Component) -->
    <InviteMemberDialog
      v-model="showInviteDialog"
      :scope-id="scopeId"
      :existing-member-ids="existingMemberIds"
      @invited="handleInvited"
    />

    <BaseDialog
      v-model="showRemoveDialog"
      size="md"
      :title="memberToRemove?.is_pending ? 'Revoke invitation?' : 'Remove member?'"
    >
      <template v-if="memberToRemove?.is_pending">
        <strong>{{ memberToRemove && displayName(memberToRemove) }}</strong> will no longer be able
        to accept the invitation.
      </template>
      <template v-else>
        <strong>{{ memberToRemove && displayName(memberToRemove) }}</strong> loses access to this
        scope. Their gene assignments are not changed; reassign them from the Genes tab.
      </template>
      <template #actions>
        <v-btn variant="text" @click="showRemoveDialog = false">Cancel</v-btn>
        <v-btn color="error" variant="flat" :loading="removing" @click="removeMember">
          {{ memberToRemove?.is_pending ? 'Revoke invitation' : 'Remove member' }}
        </v-btn>
      </template>
    </BaseDialog>
  </v-card>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue'
  import { useScopesStore } from '@/stores/scopes'
  import { useAuthStore } from '@/stores/auth'
  import { useConfirm } from '@/composables/useConfirm'
  import { TERMINOLOGY } from '@/config/terminology'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useLogger } from '@/composables/useLogger'
  import InviteMemberDialog from '@/components/scope/InviteMemberDialog.vue'
  import { scopeService } from '@/services/scopeService'
  import type { Schema } from '@/types/api'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { showSnackbar } from '@/composables/useNotifications'
  import { formatDate } from '@/utils/format'

  type ScopeMember = Schema<'ScopeMembershipResponse'>
  type ScopeRole = Schema<'ScopeRole'>

  /** Payload emitted by InviteMemberDialog after a successful invitation */
  interface InvitedPayload {
    id?: string
    userName?: string | null
    userEmail?: string | null
    direct?: boolean
  }

  // ============================================
  // PROPS
  // ============================================

  const props = defineProps<{
    scopeId: string
  }>()
  // Membership counts changed (invite, removal): the scope header re-reads its statistics
  const emit = defineEmits<{ changed: [] }>()

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const scopeStore = useScopesStore()
  const authStore = useAuthStore()
  const { confirm } = useConfirm()
  const logger = useLogger()

  const userRole = computed(() => scopeStore.currentUserRole)
  const { canInviteMembers, canEditMemberRoles, canRemoveMembers } = useScopePermissions(userRole)

  // ============================================
  // STATE
  // ============================================

  const members = ref<ScopeMember[]>([])
  const loading = ref(false)
  const showInviteDialog = ref(false)
  const showRemoveDialog = ref(false)
  const removing = ref(false)

  const memberToRemove = ref<ScopeMember | null>(null)

  /**
   * Existing member IDs (for excluding from search)
   */
  const existingMemberIds = computed<string[]>(() => {
    // Nobody invites or adds themselves (the API answers 403)
    const ids = new Set(members.value.map(m => m.user_id))
    if (currentUserId.value) ids.add(currentUserId.value)
    return [...ids]
  })

  // ============================================
  // COMPUTED
  // ============================================

  const currentUserId = computed(() => authStore.user?.id)

  const availableRoles: ScopeRole[] = ['admin', 'curator', 'reviewer', 'viewer']

  const roleLabel = (role: string) =>
    (TERMINOLOGY as Record<string, string>)[role.toUpperCase()] ?? role

  const displayName = (m: ScopeMember) => m.user_full_name || m.user_username || m.user_email || ''

  const initials = (m: ScopeMember) =>
    displayName(m)
      .split(/[\s@.]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(w => w[0]!.toUpperCase())
      .join('')

  /** A role change is easy to misclick in a menu, so ask first. */
  const requestRoleChange = async (member: ScopeMember, role: ScopeRole) => {
    if (member.role === role) return
    const ok = await confirm({
      title: `Change ${displayName(member)}'s role to ${role}?`,
      confirmText: 'Change role'
    })
    if (ok) await updateRole(member.user_id, role)
  }

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
      const err = error instanceof Error ? error : undefined
      logger.error('Failed to fetch members', {
        scope_id: props.scopeId,
        error: err?.message,
        stack: err?.stack
      })
      showNotification('Failed to load members', 'error')
    } finally {
      loading.value = false
    }
  }

  /**
   * Handle successful invitation from InviteMemberDialog
   */
  const handleInvited = async (invitationResult: InvitedPayload) => {
    logger.info('Member invited successfully', {
      scope_id: props.scopeId,
      user_name: invitationResult.userName,
      membership_id: invitationResult.id
    })

    const who = invitationResult.userName || invitationResult.userEmail
    showNotification(
      invitationResult.direct ? `${who} added to the scope` : `Invitation sent to ${who}`,
      'success'
    )

    emit('changed')
    // Refresh member list to show new pending invitation
    await fetchMembers()
  }

  /**
   * Update member role
   */
  const updateRole = async (userId: string, newRole: ScopeRole) => {
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
      const err = error instanceof Error ? error : undefined
      logger.error('Failed to update member role', {
        scope_id: props.scopeId,
        user_id: userId,
        error: err?.message,
        stack: err?.stack
      })
      showNotification('Failed to update member role', 'error')
    }
  }

  /**
   * Show remove confirmation dialog
   */
  const confirmRemoveMember = (member: ScopeMember) => {
    memberToRemove.value = member
    showRemoveDialog.value = true
  }

  /**
   * Remove member from scope
   */
  const removeMember = async () => {
    const target = memberToRemove.value
    if (!target) return

    removing.value = true

    try {
      logger.debug('Removing member', {
        scope_id: props.scopeId,
        user_id: target.user_id
      })

      await scopeStore.removeMember(props.scopeId, target.user_id)

      logger.info('Member removed', {
        scope_id: props.scopeId,
        user_id: target.user_id
      })

      showNotification('Member removed successfully', 'success')
      showRemoveDialog.value = false
      memberToRemove.value = null
      emit('changed')
      await fetchMembers()
    } catch (error) {
      const err = error instanceof Error ? error : undefined
      logger.error('Failed to remove member', {
        scope_id: props.scopeId,
        user_id: target.user_id,
        error: err?.message,
        stack: err?.stack
      })
      showNotification('Failed to remove member', 'error')
    } finally {
      removing.value = false
    }
  }

  /**
   * Show notification snackbar
   */
  const showNotification = (message: string, color = 'success') => {
    showSnackbar(message, color)
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
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .v-list-item:last-child {
    border-bottom: none;
  }
</style>
