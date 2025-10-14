<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="pa-6" elevation="8">
          <v-card-title class="text-center mb-4">
            <v-img
              src="/img/logo.png"
              alt="Gene Curator Logo"
              max-width="64"
              class="mx-auto mb-4"
            />
            <h2 class="text-h4">Login</h2>
          </v-card-title>

          <v-card-text>
            <v-form ref="loginForm" v-model="formValid" @submit.prevent="handleLogin">
              <v-text-field
                v-model="credentials.email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email"
                variant="outlined"
                :rules="emailRules"
                :error-messages="fieldErrors.email"
                required
                class="mb-3"
              />

              <v-text-field
                v-model="credentials.password"
                label="Password"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                variant="outlined"
                :rules="passwordRules"
                :error-messages="fieldErrors.password"
                required
                class="mb-4"
                @click:append-inner="showPassword = !showPassword"
              />

              <v-alert
                v-if="authStore.error"
                type="error"
                variant="tonal"
                class="mb-4"
                closable
                @click:close="authStore.clearError"
              >
                {{ authStore.error }}
              </v-alert>

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="authStore.loading"
                :disabled="!formValid"
                class="mb-4"
              >
                Login
              </v-btn>

              <div class="text-center">
                <p class="text-body-2 mb-2">Don't have an account?</p>
                <v-btn :to="{ name: 'Register' }" variant="text" color="primary">
                  Create Account
                </v-btn>
              </div>
            </v-form>
          </v-card-text>
        </v-card>

        <!-- Development Login Helper -->
        <v-card v-if="isDevelopment" class="mt-4 pa-4" variant="tonal" color="info">
          <v-card-title class="text-subtitle-1">
            <v-icon start>mdi-dev-to</v-icon>
            Development Quick Login
          </v-card-title>
          <v-card-text>
            <div class="d-flex flex-column gap-2">
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('admin')"
              >
                Login as Admin
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('curator')"
              >
                Login as Alice Smith
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('reviewer')"
              >
                Login as Bob Jones
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('viewer')"
              >
                Login as Carol Williams
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, reactive, computed } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { useAuthStore } from '@/stores/auth.js'
  import { showSuccess, showError } from '@/composables/useNotifications.js'

  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()

  // Form state
  const loginForm = ref(null)
  const formValid = ref(false)
  const showPassword = ref(false)

  const credentials = reactive({
    email: '',
    password: ''
  })

  const fieldErrors = reactive({
    email: [],
    password: []
  })

  // Development mode check
  const isDevelopment = computed(() => {
    return (
      import.meta.env.DEV ||
      import.meta.env.MODE === 'development' ||
      import.meta.env.VITE_ENABLE_DEV_LOGIN === 'true'
    )
  })

  // Validation rules
  const emailRules = [
    v => !!v || 'Email is required',
    v => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const passwordRules = [
    v => !!v || 'Password is required',
    v => v.length >= 6 || 'Password must be at least 6 characters'
  ]

  // Development quick login credentials
  // Note: admin is application-level, others are standard users with scope-specific roles
  const devCredentials = {
    admin: { email: 'admin@genecurator.org', password: 'admin123' },              // Application admin
    curator: { email: 'alice.smith@genecurator.org', password: 'admin123' },      // User (curator role in kidney-genetics scope)
    reviewer: { email: 'bob.jones@genecurator.org', password: 'admin123' },       // User (reviewer role in cardio-genetics scope)
    viewer: { email: 'carol.williams@genecurator.org', password: 'admin123' }     // User (viewer role in neuro-genetics scope)
  }

  const handleLogin = async () => {
    if (!formValid.value) return

    try {
      // Clear previous errors
      fieldErrors.email = []
      fieldErrors.password = []
      authStore.clearError()

      await authStore.login(credentials)

      showSuccess('Login successful!')

      // Redirect to intended page or home
      const redirectTo = route.query.redirect || { name: 'Home' }
      router.push(redirectTo)
    } catch (error) {
      logger.error('Login error:', { error: error.message, stack: error.stack })

      // Handle specific field errors
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (detail.includes('email')) {
          fieldErrors.email = [detail]
        } else if (detail.includes('password')) {
          fieldErrors.password = [detail]
        }
      }

      showError('Login failed. Please check your credentials.')
    }
  }

  const quickLogin = async role => {
    const creds = devCredentials[role]
    if (!creds) return

    // Fill credentials
    credentials.email = creds.email
    credentials.password = creds.password

    // Force form validation to run (Vuetify needs this for programmatic input)
    await loginForm.value.validate()

    // Now submit the form
    await handleLogin()
  }
</script>

<style scoped>
  .fill-height {
    min-height: 100vh;
    background: linear-gradient(
      135deg,
      rgb(var(--v-theme-surface)) 0%,
      rgb(var(--v-theme-background)) 100%
    );
  }

  .gap-2 {
    gap: 0.5rem;
  }

  .v-card {
    backdrop-filter: blur(10px);
    background: rgba(var(--v-theme-surface), 0.9);
  }
</style>
