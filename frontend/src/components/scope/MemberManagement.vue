<!--
  Member Management Component

  **New Component** - Built with DRY/SOLID principles from the start

  **DRY Improvements**:
  - Uses useRoleColors composable (no duplicate role color logic)
  - Uses useScopePermissions composable (permission checking)
  - Uses logService (no console.log/console.error)

  **SOLID-SRP**:
  - Component: UI rendering and user interactions only
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **Features**:
  - List all scope members with roles
  - Invite new members (email or existing user)
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
            {{ member.user_name || member.user_email }}
          </v-list-item-title>

          <v-list-item-subtitle>
            {{ member.user_email }}
          </v-list-item-subtitle>

          <template #append>
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

    <!-- Invite Member Dialog -->
    <v-dialog v-model="showInviteDialog" max-width="600">
      <v-card>
        <v-card-title>Invite Member to Scope</v-card-title>

        <v-card-text>
          <v-form ref="inviteForm" v-model="inviteFormValid">
            <v-radio-group v-model="inviteType" inline>
              <v-radio label="By Email (New User)" value="email"></v-radio>
              <v-radio label="By User ID (Existing User)" value="user_id"></v-radio>
            </v-radio-group>

            <v-text-field
              v-if="inviteType === 'email'"
              v-model="invitationData.email"
              label="Email Address"
              type="email"
              :rules="emailRules"
              prepend-icon="mdi-email"
            ></v-text-field>

            <v-text-field
              v-else
              v-model="invitationData.user_id"
              label="User ID"
              :rules="userIdRules"
              prepend-icon="mdi-account"
            ></v-text-field>

            <v-select
              v-model="invitationData.role"
              :items="availableRoles"
              label="Role"
              :rules="roleRules"
              prepend-icon="mdi-shield-account"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <v-icon
                      :icon="getRoleIcon(item.value)"
                      :color="getRoleColor(item.value)"
                    ></v-icon>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="cancelInvite">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!inviteFormValid || inviting"
            :loading="inviting"
            @click="sendInvitation"
          >
            Send Invitation
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Confirm Remove Member Dialog -->
    <v-dialog v-model="showRemoveDialog" max-width="500">
      <v-card>
        <v-card-title>Remove Member</v-card-title>

        <v-card-text>
          Are you sure you want to remove
          <strong>{{ memberToRemove?.user_name || memberToRemove?.user_email }}</strong> from this
          scope?
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
  const inviting = ref(false)
  const removing = ref(false)

  const inviteType = ref('email')
  const inviteFormValid = ref(false)
  const invitationData = ref({
    email: '',
    user_id: '',
    role: 'viewer'
  })

  const memberToRemove = ref(null)

  // Snackbar
  const showSnackbar = ref(false)
  const snackbarMessage = ref('')
  const snackbarColor = ref('success')

  // ============================================
  // COMPUTED
  // ============================================

  const currentUserId = computed(() => authStore.user?.id)

  const availableRoles = ['admin', 'curator', 'reviewer', 'viewer']

  // ============================================
  // VALIDATION RULES
  // ============================================

  const emailRules = [
    v => !!v || 'Email is required',
    v => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const userIdRules = [
    v => !!v || 'User ID is required',
    v => v.length > 0 || 'User ID must not be empty'
  ]

  const roleRules = [
    v => !!v || 'Role is required',
    v => availableRoles.includes(v) || 'Invalid role'
  ]

  // ============================================
  // METHODS
  // ============================================

  /**
   * Fetch scope members
   */
  const fetchMembers = async () => {
    loading.value = true

    try {
      logger.debug('Fetching scope members', { scope_id: props.scopeId })
      const data = await scopeStore.fetchMembers(props.scopeId)
      members.value = data
      logger.info('Members fetched successfully', { scope_id: props.scopeId, count: data.length })
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
   * Send invitation to new member
   */
  const sendInvitation = async () => {
    if (!inviteFormValid.value) return

    inviting.value = true

    try {
      const payload = {
        role: invitationData.value.role
      }

      if (inviteType.value === 'email') {
        payload.email = invitationData.value.email
      } else {
        payload.user_id = invitationData.value.user_id
      }

      logger.debug('Sending member invitation', {
        scope_id: props.scopeId,
        invite_type: inviteType.value,
        role: payload.role
      })

      await scopeStore.inviteMember(props.scopeId, payload)

      logger.info('Member invited successfully', {
        scope_id: props.scopeId,
        invite_type: inviteType.value
      })

      showNotification('Invitation sent successfully', 'success')
      cancelInvite()
      await fetchMembers()
    } catch (error) {
      logger.error('Failed to send invitation', {
        scope_id: props.scopeId,
        error: error.message,
        stack: error.stack
      })
      showNotification(`Failed to send invitation: ${error.message}`, 'error')
    } finally {
      inviting.value = false
    }
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
   * Cancel invitation and reset form
   */
  const cancelInvite = () => {
    showInviteDialog.value = false
    invitationData.value = {
      email: '',
      user_id: '',
      role: 'viewer'
    }
    inviteType.value = 'email'
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
