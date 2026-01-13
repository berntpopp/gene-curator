<!--
  PendingInvitations Component

  Displays pending scope invitations for the current user.
  Designed for the Dashboard view with accept/decline functionality.

  **Features**:
  - Shows scope name, role offered, inviter
  - Expiration countdown
  - Accept/Decline actions
  - Loading and empty states

  @example
  <PendingInvitations />
-->

<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-email-open</v-icon>
      Pending Invitations
      <v-chip v-if="pendingCount > 0" color="warning" size="small" class="ml-2">
        {{ pendingCount }}
      </v-chip>
      <v-spacer />
      <v-btn
        v-if="invitations.length > 0"
        variant="text"
        size="small"
        icon="mdi-refresh"
        :loading="loading"
        @click="refreshInvitations"
      />
    </v-card-title>

    <v-card-text>
      <!-- Loading state -->
      <div v-if="loading && invitations.length === 0" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" size="32" />
      </div>

      <!-- Invitations list -->
      <v-list v-else-if="invitations.length > 0" density="compact">
        <v-list-item
          v-for="invitation in invitations"
          :key="invitation.id"
          :class="{ 'opacity-50': invitation.is_expired }"
        >
          <template #prepend>
            <v-avatar :color="getRoleColor(invitation.role)" size="36">
              <v-icon :icon="getRoleIcon(invitation.role)" color="white" size="small" />
            </v-avatar>
          </template>

          <v-list-item-title class="font-weight-medium">
            {{ invitation.scope_display_name || invitation.scope_name }}
          </v-list-item-title>

          <v-list-item-subtitle>
            <span>Role: {{ invitation.role }}</span>
            <span v-if="invitation.inviter_name" class="ml-2">
              by {{ invitation.inviter_name }}
            </span>
          </v-list-item-subtitle>

          <!-- Expiration info -->
          <v-list-item-subtitle v-if="invitation.expires_at" class="text-caption">
            <v-icon size="x-small" class="mr-1">mdi-clock-outline</v-icon>
            <span v-if="invitation.is_expired" class="text-error"> Expired </span>
            <span v-else> Expires {{ formatExpiryTime(invitation.expires_at) }} </span>
          </v-list-item-subtitle>

          <template #append>
            <div class="d-flex ga-1">
              <v-btn
                color="success"
                variant="tonal"
                size="small"
                :disabled="invitation.is_expired || actionLoading[invitation.id]"
                :loading="actionLoading[invitation.id] === 'accept'"
                @click="handleAccept(invitation)"
              >
                Accept
              </v-btn>
              <v-btn
                color="error"
                variant="text"
                size="small"
                :disabled="actionLoading[invitation.id]"
                :loading="actionLoading[invitation.id] === 'decline'"
                @click="handleDecline(invitation)"
              >
                Decline
              </v-btn>
            </div>
          </template>
        </v-list-item>
      </v-list>

      <!-- Empty state -->
      <div v-else class="text-center py-4 text-medium-emphasis">
        <v-icon size="48" class="mb-2" color="success">mdi-check-circle</v-icon>
        <div class="text-body-2">No pending invitations</div>
      </div>
    </v-card-text>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
      <template #actions>
        <v-btn color="white" variant="text" @click="showSnackbar = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
  import { ref, computed, onMounted, reactive } from 'vue'
  import { useInvitationsStore } from '@/stores/invitations'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const invitationsStore = useInvitationsStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const actionLoading = reactive({}) // Track loading state per invitation
  const showSnackbar = ref(false)
  const snackbarMessage = ref('')
  const snackbarColor = ref('success')

  // ============================================
  // COMPUTED
  // ============================================

  const invitations = computed(() => invitationsStore.invitations)
  const pendingCount = computed(() => invitationsStore.pendingCount)
  const loading = computed(() => invitationsStore.loading)

  // ============================================
  // METHODS
  // ============================================

  /**
   * Format expiry time relative to now
   */
  const formatExpiryTime = expiresAt => {
    const now = new Date()
    const expiry = new Date(expiresAt)
    const diffMs = expiry - now

    if (diffMs < 0) return 'expired'

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays > 1) return `in ${diffDays} days`
    if (diffDays === 1) return 'in 1 day'
    if (diffHours > 1) return `in ${diffHours} hours`
    if (diffHours === 1) return 'in 1 hour'
    return 'soon'
  }

  /**
   * Show notification
   */
  const showNotification = (message, color = 'success') => {
    snackbarMessage.value = message
    snackbarColor.value = color
    showSnackbar.value = true
  }

  /**
   * Refresh invitations list
   */
  const refreshInvitations = async () => {
    try {
      await invitationsStore.fetchPendingInvitations({ force: true })
    } catch (error) {
      logger.error('Failed to refresh invitations', { error: error.message })
      showNotification('Failed to refresh invitations', 'error')
    }
  }

  /**
   * Handle accept invitation
   */
  const handleAccept = async invitation => {
    actionLoading[invitation.id] = 'accept'

    try {
      await invitationsStore.acceptInvitation(invitation.id, invitation.scope_id)

      showNotification(
        `Joined ${invitation.scope_display_name || invitation.scope_name} as ${invitation.role}`,
        'success'
      )

      logger.info('Accepted scope invitation', {
        invitationId: invitation.id,
        scopeId: invitation.scope_id,
        role: invitation.role
      })
    } catch (error) {
      logger.error('Failed to accept invitation', {
        invitationId: invitation.id,
        error: error.message
      })
      showNotification('Failed to accept invitation', 'error')
    } finally {
      delete actionLoading[invitation.id]
    }
  }

  /**
   * Handle decline invitation
   */
  const handleDecline = async invitation => {
    actionLoading[invitation.id] = 'decline'

    try {
      await invitationsStore.declineInvitation(invitation.id)

      showNotification('Invitation declined', 'info')

      logger.info('Declined scope invitation', {
        invitationId: invitation.id,
        scopeId: invitation.scope_id
      })
    } catch (error) {
      logger.error('Failed to decline invitation', {
        invitationId: invitation.id,
        error: error.message
      })
      showNotification('Failed to decline invitation', 'error')
    } finally {
      delete actionLoading[invitation.id]
    }
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  onMounted(async () => {
    try {
      await invitationsStore.fetchPendingInvitations()
    } catch (error) {
      logger.error('Failed to load pending invitations', { error: error.message })
    }
  })
</script>

<style scoped>
  .v-list-item {
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }

  .v-list-item:last-child {
    border-bottom: none;
  }

  .ga-1 {
    gap: 4px;
  }
</style>
