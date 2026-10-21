<!--
  InviteMemberDialog Component

  Reusable dialog for inviting members to a scope.
  Invites existing users via search.

  **Features**:
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
  <BaseDialog v-model="isOpen" persistent size="md">
    <template #title
      ><v-icon start color="primary">mdi-account-plus</v-icon> Invite member to scope</template
    >
    <v-form ref="formRef" v-model="formValid">
      <UserSearchAutocomplete
        v-model="selectedUser"
        :scope-id="scopeId"
        :exclude-user-ids="existingMemberIds"
        label="Search for user"
        placeholder="Type name, email, or institution..."
      />

      <!-- Selected User Preview -->
      <v-alert v-if="selectedUser" type="info" variant="tonal" class="mt-3" density="compact">
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

      <!-- Role Selection -->
      <v-select
        v-model="selectedRole"
        :items="roleOptions"
        label="Role"
        :rules="roleRules"
        class="mt-4"
        variant="outlined"
      >
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps" :title="undefined">
            <template #prepend>
              <v-icon :icon="item.icon" :color="item.color" />
            </template>
            <v-list-item-title>{{ item.title }}</v-list-item-title>
            <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
          </v-list-item>
        </template>

        <template #selection="{ item }">
          <v-chip :color="item.color" variant="tonal" size="small">
            <v-icon start :icon="item.icon" size="small" />
            {{ item.title }}
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
    <template #actions>
      <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!canSubmit"
        :loading="submitting"
        @click="handleSubmit"
      >
        <v-icon start>mdi-send</v-icon>
        Send invitation
      </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  import { ref, computed, watch } from 'vue'
  import UserSearchAutocomplete from '@/components/common/UserSearchAutocomplete.vue'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'
  import type { Schema } from '@/types/api'
  import BaseDialog from '@/components/BaseDialog.vue'

  /** User picked in the search autocomplete */
  interface InviteCandidate {
    id: string
    name?: string | null
    email: string
    institution?: string | null
    displayName: string
  }

  /** Payload emitted after a successful invitation */
  interface InvitedPayload {
    id?: string
    userName?: string | null
    userEmail?: string | null
  }

  // ============================================
  // PROPS & EMITS
  // ============================================

  const props = withDefaults(
    defineProps<{
      /** v-model for dialog visibility */
      modelValue?: boolean
      /** Scope UUID for the invitation */
      scopeId: string
      /** User IDs already in the scope (to exclude from search) */
      existingMemberIds?: string[]
    }>(),
    {
      modelValue: false,
      existingMemberIds: () => []
    }
  )

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    invited: [result: InvitedPayload]
  }>()

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const scopeStore = useScopesStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const formRef = ref<{ reset: () => void } | null>(null)
  const formValid = ref(false)
  const submitting = ref(false)
  const selectedUser = ref<InviteCandidate | null>(null)
  const selectedRole = ref<Schema<'ScopeRole'>>('viewer')
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

  const canSubmit = computed(() => selectedUser.value && selectedRole.value)

  // ============================================
  // VALIDATION RULES
  // ============================================

  const roleRules = [(v: string) => !!v || 'Role is required']

  const notesRules = [
    (v: string) => !v || v.length <= 200 || 'Notes must be 200 characters or less'
  ]

  // ============================================
  // METHODS
  // ============================================

  /**
   * Get initials from name
   */
  const getInitials = (name: string | null | undefined): string => {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    const first = parts[0] ?? ''
    if (parts.length === 1) return first.charAt(0).toUpperCase()
    const last = parts[parts.length - 1] ?? ''
    return (first.charAt(0) + last.charAt(0)).toUpperCase()
  }

  /**
   * Reset form to initial state
   */
  const resetForm = () => {
    selectedUser.value = null
    selectedRole.value = 'viewer'
    notes.value = ''
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
      const invitationData: Schema<'ScopeMembershipCreate'> = {
        role: selectedRole.value
      }

      if (selectedUser.value) {
        invitationData.user_id = selectedUser.value.id
      }

      if (notes.value) {
        invitationData.notes = notes.value
      }

      logger.debug('Sending invitation', {
        scopeId: props.scopeId,
        role: selectedRole.value
      })

      const result = (await scopeStore.inviteMember(props.scopeId, invitationData)) as
        InvitedPayload | undefined

      logger.info('Invitation sent successfully', {
        scopeId: props.scopeId,
        membershipId: result?.id
      })

      // Emit success event with invitation details
      emit('invited', {
        ...result,
        userName: selectedUser.value?.name,
        userEmail: selectedUser.value?.email
      })

      // Reset and close
      resetForm()
      isOpen.value = false
    } catch (error) {
      const err = error instanceof Error ? error : undefined
      logger.error('Failed to send invitation', {
        scopeId: props.scopeId,
        error: err?.message,
        stack: err?.stack
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
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }
</style>
