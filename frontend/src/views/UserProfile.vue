<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">
        <!-- Profile Header Card -->
        <v-card class="mb-6" :loading="loading">
          <v-card-text>
            <div class="text-center mb-6">
              <v-avatar size="100" class="mb-4">
                <v-icon size="60">mdi-account-circle</v-icon>
              </v-avatar>
              <h1 class="text-h4 mb-2">{{ userProfile?.name || currentUser?.email }}</h1>
              <div class="text-subtitle-1 text-medium-emphasis">
                {{ userProfile?.email }}
              </div>
              <div class="text-body-2 text-medium-emphasis">
                Member since {{ formatDate(userProfile?.created_at) }}
              </div>
            </div>

            <h2 class="text-h6 mb-3">Scopes &amp; roles</h2>
            <v-table v-if="scopes.length" density="comfortable">
              <thead>
                <tr>
                  <th scope="col">Scope</th>
                  <th scope="col">Role</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="scope in scopes" :key="scope.id">
                  <td>
                    <router-link :to="{ name: 'scope-dashboard', params: { scopeId: scope.id } }">
                      {{ scope.display_name || scope.name }}
                    </router-link>
                  </td>
                  <td>{{ roleName(scope.user_role) }}</td>
                </tr>
              </tbody>
            </v-table>
            <p v-else class="text-body-2 text-medium-emphasis">
              You are not a member of any scope yet.
            </p>
          </v-card-text>
        </v-card>

        <!-- Password Change Card -->
        <v-card>
          <v-card-title class="text-h6">
            <v-icon start>mdi-lock</v-icon>
            Change password
          </v-card-title>
          <v-card-text>
            <v-form ref="passwordForm" v-model="passwordFormValid" @submit.prevent="changePassword">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="passwordData.current_password"
                    label="Current Password"
                    type="password"
                    variant="outlined"
                    :rules="[required]"
                    autocomplete="current-password"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="passwordData.new_password"
                    label="New Password"
                    type="password"
                    variant="outlined"
                    :rules="passwordRules"
                    :hint="`Minimum ${PASSWORD_MIN_LENGTH} characters`"
                    autocomplete="new-password"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="confirmPassword"
                    label="Confirm New Password"
                    type="password"
                    variant="outlined"
                    :rules="confirmRules"
                    autocomplete="new-password"
                  />
                </v-col>
              </v-row>
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              :loading="passwordLoading"
              :disabled="!passwordFormValid"
              color="primary"
              @click="changePassword"
            >
              Change password
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { formatDate } from '@/utils/format'
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, onMounted, watch } from 'vue'
  import { useAuthStore } from '@/stores/auth'
  import { useUsersStore } from '@/stores/users'
  import { useScopesStore } from '@/stores/scopes'
  import { showSuccess, showError } from '@/composables/useNotifications'
  import { passwordRules, PASSWORD_MIN_LENGTH } from '@/config/password'
  import { authApi } from '@/api/auth'
  import type { Schema } from '@/types/api'

  const authStore = useAuthStore()
  const usersStore = useUsersStore()
  const scopesStore = useScopesStore()
  // Only scopes where the caller has an accepted membership carry a role (admins also list the rest)
  const scopes = computed(() => scopesStore.userScopes.filter(s => s.user_role))
  // The auth store types user as null (untyped JS state); narrow it to the generated user shape
  const currentUser = computed(() => authStore.user as Schema<'UserResponse'> | null)

  // Reactive state
  const userProfile = ref<Schema<'UserResponse'> | null>(null)
  const loading = ref(false)
  const passwordLoading = ref(false)
  const passwordFormValid = ref(false)
  const passwordForm = ref<{
    validate: () => Promise<{ valid: boolean }>
    reset: () => void
  } | null>(null)

  // Password change form
  const passwordData = ref({
    current_password: '',
    new_password: ''
  })

  const confirmPassword = ref('')
  const required = (value: unknown) => !!value || 'This field is required'
  const confirmRules = [
    (v: string) => !!v || 'Please confirm your password',
    (v: string) => v === passwordData.value.new_password || 'Passwords do not match'
  ]

  // Methods
  const roleName = (role: string | null | undefined) =>
    role ? role.charAt(0).toUpperCase() + role.slice(1) : ''

  async function loadUserProfile() {
    if (!currentUser.value?.id) {
      // If we don't have user ID from auth store, use the auth store data
      userProfile.value = currentUser.value
      return
    }

    loading.value = true

    try {
      // Fetch complete user profile from database
      const profile = await usersStore.fetchUser(currentUser.value.id)
      userProfile.value = profile
    } catch (error) {
      const err = error as Error
      logger.error('Failed to load user profile:', { error: err.message, stack: err.stack })
      // Fallback to auth store data
      userProfile.value = currentUser.value
      showError('Failed to load complete profile information')
    } finally {
      loading.value = false
    }
  }

  async function changePassword() {
    if (!passwordForm.value) return

    const { valid } = await passwordForm.value.validate()
    if (!valid) return

    passwordLoading.value = true

    try {
      await authApi.changePassword(passwordData.value)

      // Clear form
      passwordData.value = {
        current_password: '',
        new_password: ''
      }
      passwordForm.value.reset()

      confirmPassword.value = ''
      showSuccess('Password changed successfully')
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } }
      const message = err.response?.data?.detail || 'Failed to change password'
      showError(message)
    } finally {
      passwordLoading.value = false
    }
  }

  // Watch for auth changes
  watch(
    () => authStore.user,
    newUser => {
      if (newUser) {
        loadUserProfile()
      }
    },
    { immediate: true }
  )

  // Initialize
  onMounted(() => {
    scopesStore.fetchUserScopes().catch(() => showError('Failed to load your scopes'))
  })
</script>
