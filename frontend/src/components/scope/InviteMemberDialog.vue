<!--
  InviteMemberDialog Component

  Reusable dialog for inviting members to a scope.
  Supports both existing user search and email invitation (deferred).

  **Features**:
  - Two tabs: "Existing User" (default) and "By Email" (deferred)
  - User autocomplete search
  - Role selection with icons
  - Form validation
  - Emits invited event on success

  **Props**:
  - modelValue: v-model for dialog visibility
  - scopeId: Required scope UUID
  - existingMemberIds: User IDs already in the scope (to exclude)

  **Events**:
  - update:modelValue: Dialog visibility change
  - invited: Emitted when invitation is successful

  @example
  <InviteMemberDialog
    v-model="showDialog"
    :scope-id="scopeId"
    :existing-member-ids="memberIds"
    @invited="handleInvited"
  />
-->

<template>
  <v-dialog v-model="isOpen" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start color="primary">mdi-account-plus</v-icon>
        Invite Member to Scope
      </v-card-title>

      <v-card-text>
        <!-- Invitation Method Tabs -->
        <v-tabs v-model="inviteTab" class="mb-4">
          <v-tab value="existing">
            <v-icon start>mdi-account-search</v-icon>
            Existing User
          </v-tab>
          <v-tab value="email" disabled>
            <v-icon start>mdi-email</v-icon>
            By Email
            <v-chip size="x-small" class="ml-2" color="warning">Coming Soon</v-chip>
          </v-tab>
        </v-tabs>

        <v-form ref="formRef" v-model="formValid">
          <v-window v-model="inviteTab">
            <!-- Existing User Tab -->
            <v-window-item value="existing">
              <UserSearchAutocomplete
                v-model="selectedUser"
                :scope-id="scopeId"
                :exclude-user-ids="existingMemberIds"
                label="Search for user"
                placeholder="Type name, email, or institution..."
              />

              <!-- Selected User Preview -->
              <v-alert
                v-if="selectedUser"
                type="info"
                variant="tonal"
                class="mt-3"
                density="compact"
              >
                <div class="d-flex align-center">
                  <v-avatar size="32" color="primary" class="mr-3">
                    <span class="text-caption font-weight-bold">
                      {{ getInitials(selectedUser.name) }}
                    </span>
                  </v-avatar>
                  <div>
                    <div class="font-weight-medium">
                      {{ selectedUser.name || selectedUser.email }}
                    </div>
                    <div class="text-caption text-medium-emphasis">{{ selectedUser.email }}</div>
                  </div>
                </div>
              </v-alert>
            </v-window-item>

            <!-- Email Tab (deferred) -->
            <v-window-item value="email">
              <v-text-field
                v-model="emailInvite"
                label="Email Address"
                type="email"
                :rules="emailRules"
                prepend-icon="mdi-email"
                placeholder="user@example.com"
                disabled
              />
              <v-alert type="info" variant="tonal" density="compact" class="mt-2">
                Email invitations are coming soon. For now, please invite existing users.
              </v-alert>
            </v-window-item>
          </v-window>

          <!-- Role Selection -->
          <v-select
            v-model="selectedRole"
            :items="roleOptions"
            label="Role"
            :rules="roleRules"
            class="mt-4"
            variant="outlined"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props" :title="undefined">
                <template #prepend>
                  <v-icon :icon="item.raw.icon" :color="item.raw.color" />
                </template>
                <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
              </v-list-item>
            </template>

            <template #selection="{ item }">
              <v-chip :color="item.raw.color" variant="tonal" size="small">
                <v-icon start :icon="item.raw.icon" size="small" />
                {{ item.raw.title }}
              </v-chip>
            </template>
          </v-select>

          <!-- Optional Notes -->
          <v-textarea
            v-model="notes"
            label="Notes (optional)"
            rows="2"
            variant="outlined"
            placeholder="Welcome message or additional context..."
            counter="200"
            :rules="notesRules"
          />
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!canSubmit"
          :loading="submitting"
          @click="handleSubmit"
        >
          <v-icon start>mdi-send</v-icon>
          Send Invitation
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  import { ref, computed, watch } from 'vue'
  import UserSearchAutocomplete from '@/components/common/UserSearchAutocomplete.vue'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'

  // ============================================
  // PROPS & EMITS
  // ============================================

  const props = defineProps({
    /**
     * v-model for dialog visibility
     */
    modelValue: {
      type: Boolean,
      default: false
    },
    /**
     * Scope UUID for the invitation
     */
    scopeId: {
      type: String,
      required: true
    },
    /**
     * User IDs already in the scope (to exclude from search)
     */
    existingMemberIds: {
      type: Array,
      default: () => []
    }
  })

  const emit = defineEmits(['update:modelValue', 'invited'])

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const scopeStore = useScopesStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const formRef = ref(null)
  const formValid = ref(false)
  const submitting = ref(false)
  const inviteTab = ref('existing')
  const selectedUser = ref(null)
  const emailInvite = ref('')
  const selectedRole = ref('viewer')
  const notes = ref('')

  // ============================================
  // COMPUTED
  // ============================================

  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const roleOptions = computed(() => [
    {
      value: 'admin',
      title: 'Admin',
      description: 'Full scope management and member control',
      icon: getRoleIcon('admin'),
      color: getRoleColor('admin')
    },
    {
      value: 'curator',
      title: 'Curator',
      description: 'Create and edit curations',
      icon: getRoleIcon('curator'),
      color: getRoleColor('curator')
    },
    {
      value: 'reviewer',
      title: 'Reviewer',
      description: 'Review and approve curations',
      icon: getRoleIcon('reviewer'),
      color: getRoleColor('reviewer')
    },
    {
      value: 'viewer',
      title: 'Viewer',
      description: 'Read-only access to scope',
      icon: getRoleIcon('viewer'),
      color: getRoleColor('viewer')
    }
  ])

  const canSubmit = computed(() => {
    if (inviteTab.value === 'existing') {
      return selectedUser.value && selectedRole.value
    }
    return false // Email tab is disabled
  })

  // ============================================
  // VALIDATION RULES
  // ============================================

  const emailRules = [
    v => !!v || 'Email is required',
    v => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const roleRules = [v => !!v || 'Role is required']

  const notesRules = [v => !v || v.length <= 200 || 'Notes must be 200 characters or less']

  // ============================================
  // METHODS
  // ============================================

  /**
   * Get initials from name
   */
  const getInitials = name => {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
  }

  /**
   * Reset form to initial state
   */
  const resetForm = () => {
    selectedUser.value = null
    emailInvite.value = ''
    selectedRole.value = 'viewer'
    notes.value = ''
    inviteTab.value = 'existing'
    if (formRef.value) {
      formRef.value.reset()
    }
  }

  /**
   * Handle cancel button
   */
  const handleCancel = () => {
    resetForm()
    isOpen.value = false
  }

  /**
   * Handle form submission
   */
  const handleSubmit = async () => {
    if (!canSubmit.value) return

    submitting.value = true

    try {
      const invitationData = {
        role: selectedRole.value
      }

      if (inviteTab.value === 'existing' && selectedUser.value) {
        invitationData.user_id = selectedUser.value.id
      } else if (inviteTab.value === 'email') {
        invitationData.email = emailInvite.value
      }

      if (notes.value) {
        invitationData.notes = notes.value
      }

      logger.debug('Sending invitation', {
        scopeId: props.scopeId,
        type: inviteTab.value,
        role: selectedRole.value
      })

      const result = await scopeStore.inviteMember(props.scopeId, invitationData)

      logger.info('Invitation sent successfully', {
        scopeId: props.scopeId,
        membershipId: result?.id
      })

      // Emit success event with invitation details
      emit('invited', {
        ...result,
        userName: selectedUser.value?.name,
        userEmail: selectedUser.value?.email || emailInvite.value
      })

      // Reset and close
      resetForm()
      isOpen.value = false
    } catch (error) {
      logger.error('Failed to send invitation', {
        scopeId: props.scopeId,
        error: error.message,
        stack: error.stack
      })
      // Error handling is done by the store/component using this dialog
      throw error
    } finally {
      submitting.value = false
    }
  }

  // ============================================
  // WATCHERS
  // ============================================

  // Reset form when dialog opens
  watch(isOpen, newValue => {
    if (newValue) {
      // Reset on open
      resetForm()
    }
  })
</script>

<style scoped>
  .v-tabs {
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  }
</style>
