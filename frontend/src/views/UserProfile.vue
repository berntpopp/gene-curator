<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">
        <!-- Profile Header Card -->
        <v-card class="mb-6">
          <v-card-title class="text-h5">
            <v-icon start>mdi-account</v-icon>
            User Profile
          </v-card-title>
          <v-card-text>
            <div class="text-center mb-6">
              <v-avatar size="100" class="mb-4">
                <v-icon size="60">mdi-account-circle</v-icon>
              </v-avatar>
              <h2 class="text-h4 mb-2">{{ userProfile?.name || authStore.user?.email }}</h2>
              <div class="mb-3">
                <v-chip :color="getRoleColor(userProfile?.role)" variant="tonal" size="large">
                  <v-icon start>{{ getRoleIcon(userProfile?.role) }}</v-icon>
                  {{ userProfile?.role }}
                </v-chip>
              </div>
              <div class="text-subtitle-1 text-medium-emphasis">
                {{ userProfile?.email }}
              </div>
            </div>

            <v-divider class="my-6" />

            <!-- Account Information -->
            <v-row>
              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-3">Account Information</h3>
                <v-list>
                  <v-list-item>
                    <template #prepend>
                      <v-icon>mdi-email</v-icon>
                    </template>
                    <v-list-item-title>{{ userProfile?.email }}</v-list-item-title>
                    <v-list-item-subtitle>Email Address</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon>mdi-account</v-icon>
                    </template>
                    <v-list-item-title>{{
                      userProfile?.name || 'Not specified'
                    }}</v-list-item-title>
                    <v-list-item-subtitle>Full Name</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon>mdi-shield-account</v-icon>
                    </template>
                    <v-list-item-title>
                      <v-chip :color="getRoleColor(userProfile?.role)" size="small">
                        {{ userProfile?.role }}
                      </v-chip>
                    </v-list-item-title>
                    <v-list-item-subtitle>Role</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon>mdi-calendar</v-icon>
                    </template>
                    <v-list-item-title>{{ formatDate(userProfile?.created_at) }}</v-list-item-title>
                    <v-list-item-subtitle>Member Since</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon>mdi-login</v-icon>
                    </template>
                    <v-list-item-title>{{
                      formatDate(userProfile?.last_login) || 'Never'
                    }}</v-list-item-title>
                    <v-list-item-subtitle>Last Login</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon :color="userProfile?.is_active ? 'success' : 'error'">
                        {{ userProfile?.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
                      </v-icon>
                    </template>
                    <v-list-item-title>
                      <v-chip
                        :color="userProfile?.is_active ? 'success' : 'error'"
                        size="small"
                        variant="flat"
                      >
                        {{ userProfile?.is_active ? 'Active' : 'Inactive' }}
                      </v-chip>
                    </v-list-item-title>
                    <v-list-item-subtitle>Account Status</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>

              <!-- Activity Summary -->
              <v-col v-if="userActivity" cols="12" md="6">
                <h3 class="text-h6 mb-3">Activity Summary</h3>
                <v-list>
                  <v-list-item>
                    <template #prepend>
                      <v-icon color="primary">mdi-dna</v-icon>
                    </template>
                    <v-list-item-title>{{ userActivity.genes_created || 0 }}</v-list-item-title>
                    <v-list-item-subtitle>Genes Created</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon color="info">mdi-database-edit</v-icon>
                    </template>
                    <v-list-item-title>{{ userActivity.genes_updated || 0 }}</v-list-item-title>
                    <v-list-item-subtitle>Genes Updated</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon color="warning">mdi-file-document</v-icon>
                    </template>
                    <v-list-item-title>{{ userActivity.curations_created || 0 }}</v-list-item-title>
                    <v-list-item-subtitle>Curations Created</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon color="success">mdi-check-circle</v-icon>
                    </template>
                    <v-list-item-title>{{
                      userActivity.curations_approved || 0
                    }}</v-list-item-title>
                    <v-list-item-subtitle>Curations Approved</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item class="pt-3">
                    <template #prepend>
                      <v-icon color="primary">mdi-star</v-icon>
                    </template>
                    <v-list-item-title class="text-h6 font-weight-bold">
                      {{ userActivity.total_contributions || 0 }}
                    </v-list-item-title>
                    <v-list-item-subtitle>Total Contributions</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Password Change Card -->
        <v-card>
          <v-card-title class="text-h6">
            <v-icon start>mdi-lock</v-icon>
            Change Password
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
                    :rules="[rules.required]"
                    autocomplete="current-password"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="passwordData.new_password"
                    label="New Password"
                    type="password"
                    variant="outlined"
                    :rules="[rules.required, rules.minLength]"
                    hint="Minimum 8 characters"
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
              Change Password
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Loading overlay -->
    <v-overlay v-model="loading" class="align-center justify-center">
      <v-progress-circular color="primary" indeterminate size="64" />
    </v-overlay>

    <!-- Snackbar for messages -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
  import { ref, onMounted, watch } from 'vue'
  import { useAuthStore } from '@/stores/auth.js'
  import { useUsersStore } from '@/stores/users.js'
  import { authApi } from '@/api/auth.js'

  const authStore = useAuthStore()
  const usersStore = useUsersStore()

  // Reactive state
  const userProfile = ref(null)
  const userActivity = ref(null)
  const loading = ref(false)
  const passwordLoading = ref(false)
  const passwordFormValid = ref(false)
  const passwordForm = ref(null)

  // Password change form
  const passwordData = ref({
    current_password: '',
    new_password: ''
  })

  // Snackbar
  const snackbar = ref({
    show: false,
    message: '',
    color: 'success'
  })

  // Form validation rules
  const rules = {
    required: value => !!value || 'This field is required',
    minLength: value => (value && value.length >= 8) || 'Minimum 8 characters required'
  }

  // Methods
  const getRoleColor = role => {
    const colors = { admin: 'error', curator: 'warning', viewer: 'info' }
    return colors[role] || 'grey'
  }

  const getRoleIcon = role => {
    const icons = { admin: 'mdi-shield-crown', curator: 'mdi-pencil', viewer: 'mdi-eye' }
    return icons[role] || 'mdi-account'
  }

  const formatDate = dateString => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  async function loadUserProfile() {
    if (!authStore.user?.id) {
      // If we don't have user ID from auth store, use the auth store data
      userProfile.value = authStore.user
      return
    }

    loading.value = true

    try {
      // Fetch complete user profile from database
      const profile = await usersStore.fetchUser(authStore.user.id)
      userProfile.value = profile

      // Fetch user activity
      const activity = await usersStore.fetchUserActivity(authStore.user.id)
      userActivity.value = activity
    } catch (error) {
      logger.error('Failed to load user profile:', { error: error.message, stack: error.stack })
      // Fallback to auth store data
      userProfile.value = authStore.user
      showSnackbar('Failed to load complete profile information', 'warning')
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

      showSnackbar('Password changed successfully', 'success')
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to change password'
      showSnackbar(message, 'error')
    } finally {
      passwordLoading.value = false
    }
  }

  function showSnackbar(message, color = 'success') {
    snackbar.value = {
      show: true,
      message,
      color
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
    if (authStore.user) {
      loadUserProfile()
    }
  })
</script>
